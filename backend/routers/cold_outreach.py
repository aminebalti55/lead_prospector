"""Cold outreach router — extracted from backend/app.py."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from src.core.storage import list_files, read_leads, update_lead
from src.core.config import COLD_OUTPUT_DIR, OUTPUT_DIR
from backend.models import (
    RunCreateRequest,
    RunCreateResponse,
    RunStatusResponse,
)
from backend.run_manager import RunManager

router = APIRouter(prefix="/api/cold", tags=["cold-outreach"])

run_manager = RunManager()


# ── File endpoints ────────────────────────────────────────────────────

@router.get("/files")
async def list_cold_files():
    cold_files = list_files("cold")
    legacy_files = list_files("legacy")
    return {"files": cold_files + legacy_files}


@router.get("/files/{filename}/leads")
async def get_cold_leads(filename: str):
    # Try cold dir first, then legacy
    try:
        headers, rows = read_leads(filename, "cold")
    except FileNotFoundError:
        try:
            headers, rows = read_leads(filename, "legacy")
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="File not found")
    return {"file": filename, "columns": headers, "rows": rows}


@router.get("/files/{filename}/download")
async def download_cold_file(filename: str):
    safe_name = Path(filename).name
    # Check cold dir first, then legacy (OUTPUT_DIR)
    for directory in [COLD_OUTPUT_DIR, OUTPUT_DIR]:
        path = directory / safe_name
        if path.exists():
            return FileResponse(path, filename=safe_name)
    raise HTTPException(status_code=404, detail="File not found")


@router.patch("/leads/{lead_id}")
async def update_cold_lead(lead_id: str, body: dict):
    for section in ["cold", "legacy"]:
        for f in list_files(section):
            try:
                update_lead(f["name"], lead_id, body, section)
                return {"ok": True}
            except (KeyError, FileNotFoundError):
                continue
    raise HTTPException(status_code=404, detail="Lead not found")


# ── Run endpoints ─────────────────────────────────────────────────────

@router.post("/runs", response_model=RunCreateResponse)
async def create_run(body: RunCreateRequest) -> RunCreateResponse:
    import traceback

    try:
        state = await run_manager.create_run(body)
        return RunCreateResponse(
            run_id=state.run_id, status=state.status, created_at=state.created_at
        )
    except Exception as e:
        print(f"[COLD_ROUTER] create_run error: {e}", flush=True)
        print(f"[COLD_ROUTER] Traceback:\n{traceback.format_exc()}", flush=True)
        raise


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run(run_id: str) -> RunStatusResponse:
    try:
        state = await run_manager.get_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunStatusResponse(
        run_id=state.run_id,
        status=state.status,
        created_at=state.created_at,
        started_at=state.started_at,
        finished_at=state.finished_at,
        params=state.params,
        output_files=state.output_files,
        error=state.error,
        progress=state.progress,
    )


@router.get("/runs")
async def list_runs():
    runs = await run_manager.list_runs()
    return {
        "runs": [
            {
                "run_id": r.run_id,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in runs
        ]
    }
