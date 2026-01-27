from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from backend.models import RunCreateRequest, RunProgress, ProgressStep


RunStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class RunState:
    run_id: str
    status: RunStatus
    created_at: datetime
    params: RunCreateRequest
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    output_files: list[str] = None
    error: Optional[str] = None
    progress: RunProgress = None

    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []
        if self.progress is None:
            self.progress = RunProgress()


class ProgressTracker:
    """Tracks progress for a single run with detailed step information."""
    
    def __init__(self, state: RunState):
        self.state = state
        self.progress = state.progress
        self._lock = asyncio.Lock()
    
    async def set_phase(self, phase: str, step: str = ""):
        async with self._lock:
            self.progress.current_phase = phase
            self.progress.current_step = step
            self._add_log(f"[{phase}] {step}" if step else phase)
    
    async def update_step(self, step: str, message: str = ""):
        async with self._lock:
            self.progress.current_step = step
            if message:
                self._add_log(f"  {step}: {message}")
    
    async def set_progress(self, percent: int):
        async with self._lock:
            self.progress.progress_percent = min(100, max(0, percent))
    
    async def increment_leads(self, count: int = 1):
        async with self._lock:
            self.progress.leads_found += count
    
    async def increment_emails(self, count: int = 1):
        async with self._lock:
            self.progress.emails_extracted += count
    
    async def increment_audits(self, count: int = 1):
        async with self._lock:
            self.progress.websites_audited += count
    
    async def add_step(self, step_name: str, status: str = "pending", message: str = ""):
        async with self._lock:
            step = ProgressStep(
                step=step_name,
                status=status,
                message=message,
                started_at=datetime.utcnow() if status == "running" else None
            )
            self.progress.steps.append(step)
    
    async def complete_step(self, step_name: str, message: str = "", count: int = 0):
        async with self._lock:
            for step in self.progress.steps:
                if step.step == step_name:
                    step.status = "completed"
                    step.message = message
                    step.count = count
                    step.completed_at = datetime.utcnow()
                    break
    
    async def fail_step(self, step_name: str, message: str = ""):
        async with self._lock:
            for step in self.progress.steps:
                if step.step == step_name:
                    step.status = "failed"
                    step.message = message
                    step.completed_at = datetime.utcnow()
                    break
    
    def _add_log(self, message: str):
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        self.progress.logs.append(f"[{timestamp}] {message}")
        # Keep only last 100 logs
        if len(self.progress.logs) > 100:
            self.progress.logs = self.progress.logs[-100:]


class RunManager:
    def __init__(self):
        self._runs: Dict[str, RunState] = {}
        self._trackers: Dict[str, ProgressTracker] = {}
        self._lock = asyncio.Lock()
        # Avoid running multiple Playwright scrapes concurrently (resource heavy)
        self._run_semaphore = asyncio.Semaphore(1)

    async def create_run(self, params: RunCreateRequest) -> RunState:
        run_id = uuid4().hex
        state = RunState(
            run_id=run_id, 
            status="queued", 
            created_at=datetime.utcnow(), 
            params=params,
            progress=RunProgress(
                current_phase="Queued",
                current_step="Waiting to start...",
                progress_percent=0
            )
        )

        async with self._lock:
            self._runs[run_id] = state
            self._trackers[run_id] = ProgressTracker(state)

        asyncio.create_task(self._execute_run(state))
        return state

    async def get_run(self, run_id: str) -> RunState:
        async with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            return self._runs[run_id]

    async def list_runs(self) -> list[RunState]:
        async with self._lock:
            return list(self._runs.values())

    async def _execute_run(self, state: RunState) -> None:
        tracker = self._trackers.get(state.run_id)
        
        async with self._run_semaphore:
            # Import here to keep import-time side effects minimal
            from main import LeadProspector

            state.status = "running"
            state.started_at = datetime.utcnow()

            try:
                if tracker:
                    await tracker.set_phase("Initializing", "Setting up scrapers...")
                    await tracker.set_progress(5)
                
                prospector = LeadProspector()
                
                # Inject progress tracker into prospector
                prospector._progress_tracker = tracker
                
                if tracker:
                    await tracker.set_phase("Scraping", "Starting data collection...")
                    await tracker.set_progress(10)
                    
                    # Add steps for each scraper
                    scrapers = ["google_maps", "yelp", "yellowpages", "bbb", "manta"]
                    skip_scrapers = state.params.skip_scrapers or []
                    active_scrapers = [s for s in scrapers if s not in skip_scrapers]
                    
                    for scraper in active_scrapers:
                        await tracker.add_step(f"Scrape {scraper}", "pending")
                
                await prospector.run(
                    locations=state.params.locations,
                    niches=list(state.params.niches),
                    skip_audit=state.params.skip_audit,
                    skip_reviews=True,
                    output_format=state.params.output_format,
                    use_scrapers=True,
                    skip_scrapers=state.params.skip_scrapers,
                    fetch_details=state.params.fetch_details,
                    fetch_emails=state.params.fetch_emails,
                    max_results=state.params.max_results,
                )

                # Get output files from prospector
                output_files = getattr(prospector, "last_output_files", [])
                state.output_files = [p.name for p in output_files if p and hasattr(p, 'name')]
                
                # Log for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Run {state.run_id} completed with {len(state.output_files)} output files: {state.output_files}")
                
                state.status = "completed"
                state.finished_at = datetime.utcnow()
                
                if tracker:
                    leads_count = tracker.progress.leads_found if tracker.progress else 0
                    await tracker.set_phase("Completed", f"Found {leads_count} leads!")
                    await tracker.set_progress(100)
                    
            except Exception as e:
                state.status = "failed"
                state.finished_at = datetime.utcnow()
                state.error = str(e)
                
                if tracker:
                    await tracker.set_phase("Failed", str(e))
