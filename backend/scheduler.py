"""Background scheduler — Supabase-backed.

Two responsibilities:
1. Fire saved searches whose `next_run_at` (computed from frequency) has
   elapsed.
2. Auto-fail scans that have been 'running' for over an hour (process died).

Plan-10 hooks into this loop too — see backend/services/sequence_worker.py.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services import saved_searches_store, scans_store
from backend.services.supabase_client import get_client

logger = logging.getLogger(__name__)


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
                await self._fire_due_saved_searches()
                await self._reconcile_stuck_scans()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(60)

    # -----------------------------------------------------------------

    async def _fire_due_saved_searches(self) -> None:
        searches = saved_searches_store.get_all()
        for search in searches:
            if search.get("is_paused"):
                continue
            if not self._is_due(search):
                continue
            logger.info(f"Scheduler triggering saved search {search['id']}")
            try:
                await self._dispatch(search)
                saved_searches_store.mark_run_started(search["id"])
            except Exception as e:
                logger.error(f"Scheduled scan failed for {search['id']}: {e}")

    def _is_due(self, search: dict[str, Any]) -> bool:
        last = search.get("last_run_at")
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return True
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        gap = self._parse_frequency_hours(search.get("frequency"))
        return datetime.now(timezone.utc) - last_dt >= timedelta(hours=gap)

    async def _dispatch(self, search: dict[str, Any]) -> None:
        kind = search.get("type") or "direct"
        keywords = search.get("keywords") or []
        sources = search.get("sources") or []
        max_results = int(search.get("max_results") or 50)

        if kind == "cold":
            scan = scans_store.create({
                "type": "cold",
                "status": "queued",
                "sources": sources,
                "locations": search.get("locations") or [],
                "niches": search.get("niches") or [],
                "max_results": max_results,
            })
            from backend.routers.cold_outreach import _execute_scan as _exec_cold
            asyncio.create_task(_exec_cold(scan["id"], {
                "locations": search.get("locations") or [],
                "niches": search.get("niches") or [],
                "skip_scrapers": [],
                "skip_audit": False,
                "fetch_emails": True,
                "fetch_details": True,
                "max_results": max_results,
            }))
        else:
            scan = scans_store.create({
                "type": "direct",
                "status": "queued",
                "sources": sources,
                "keywords": keywords,
                "max_results": max_results,
            })
            from backend.routers.direct_leads import _execute_scan as _exec_direct
            asyncio.create_task(_exec_direct(scan["id"], {
                "sources": sources,
                "keywords": keywords,
                "max_results": max_results,
            }))

    # -----------------------------------------------------------------

    async def _reconcile_stuck_scans(self) -> None:
        """Mark scans 'running' for over an hour as failed (process likely died)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        client = get_client()
        resp = (
            client.table("scans")
            .select("id, started_at")
            .eq("status", "running")
            .execute()
        )
        for row in resp.data or []:
            ts = row.get("started_at")
            if not ts:
                continue
            try:
                t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except ValueError:
                continue
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if t < cutoff:
                scans_store.mark_failed(row["id"], "killed before completing (auto-reconciled)")

    # -----------------------------------------------------------------

    @staticmethod
    def _parse_frequency_hours(raw: str | None) -> int:
        s = (raw or "daily").lower().strip()
        return {
            "hourly": 1,
            "daily": 24,
            "weekly": 168,
            "biweekly": 336,
            "monthly": 720,
        }.get(s, 24)
