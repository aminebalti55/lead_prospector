"""Scheduler for automated saved-search execution."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from src.core.config import DIRECT_OUTPUT_DIR

logger = logging.getLogger(__name__)
SAVED_SEARCHES_FILE = DIRECT_OUTPUT_DIR / "saved_searches.json"


class Scheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Scheduler started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._check_saved_searches()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(60)

    async def _check_saved_searches(self) -> None:
        if not SAVED_SEARCHES_FILE.exists():
            return

        searches = json.loads(SAVED_SEARCHES_FILE.read_text())
        updated = False

        for search in searches:
            if not search.get("enabled", True):
                continue

            frequency_hours = self._parse_frequency(search.get("frequency", "daily"))
            last_run = search.get("last_run")

            if last_run:
                last_dt = datetime.fromisoformat(last_run)
                if datetime.now() - last_dt < timedelta(hours=frequency_hours):
                    continue

            logger.info(f"Scheduler triggering search: {search.get('id')}")
            try:
                # Pipeline import deferred to avoid import-time side effects
                from src.direct_leads.pipeline import DirectLeadsPipeline

                pipeline = DirectLeadsPipeline()
                await pipeline.run(
                    keywords=search.get("keywords", []),
                    sources=search.get("sources"),
                    max_results=search.get("max_results", 20),
                )
                search["last_run"] = datetime.now().isoformat()
                updated = True
            except ImportError:
                logger.warning("DirectLeadsPipeline not yet available; skipping scheduled scan")
            except Exception as e:
                logger.error(f"Scheduled scan failed: {e}")

        if updated:
            SAVED_SEARCHES_FILE.write_text(json.dumps(searches, indent=2))

    @staticmethod
    def _parse_frequency(freq: str) -> float:
        freq = freq.lower()
        if "hour" in freq:
            match = re.search(r"(\d+)", freq)
            return float(match.group(1)) if match else 6
        if freq == "daily":
            return 24
        if freq == "weekly":
            return 168
        return 24  # default daily
