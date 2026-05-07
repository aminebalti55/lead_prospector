"""Scan job records — Supabase-backed (`scans` table).

Used by direct_leads + cold_outreach routers to track scrape jobs.
Replaces the legacy scans.json file.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from backend.services.supabase_client import get_client


_FIELDS = (
    "id, type, status, sources, keywords, locations, niches, source_configs, "
    "max_results, progress, leads_found, emails_extracted, logs, error, "
    "output_files, created_at, started_at, finished_at, "
    "phase, current_source, current_keyword"
)


def list_all(limit: int = 50) -> list[dict[str, Any]]:
    resp = (
        get_client()
        .table("scans")
        .select(_FIELDS)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def get(scan_id: str) -> Optional[dict[str, Any]]:
    resp = (
        get_client()
        .table("scans")
        .select(_FIELDS)
        .eq("id", scan_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def create(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a queued scan record. Returns the row including the generated id."""
    row = {
        "type": payload.get("type") or "direct",
        "status": payload.get("status") or "queued",
        "sources": payload.get("sources") or [],
        "keywords": payload.get("keywords") or [],
        "locations": payload.get("locations") or [],
        "niches": payload.get("niches") or [],
        "source_configs": payload.get("source_configs") or {},
        "max_results": int(payload.get("max_results") or 50),
        "progress": 0,
        "leads_found": 0,
        "emails_extracted": 0,
        "logs": [],
        "output_files": [],
    }
    resp = get_client().table("scans").insert(row).execute()
    return (resp.data or [None])[0]


def update(scan_id: str, patch: dict[str, Any]) -> None:
    """Patch fields on a scan. `logs` is APPENDED if present (not replaced)."""
    if "logs" in patch:
        existing = get(scan_id) or {}
        existing_logs = existing.get("logs") or []
        if isinstance(patch["logs"], list):
            patch["logs"] = list(existing_logs) + patch["logs"]
        else:
            patch["logs"] = list(existing_logs) + [str(patch["logs"])]
    get_client().table("scans").update(patch).eq("id", scan_id).execute()


def append_log(scan_id: str, message: str) -> None:
    update(scan_id, {"logs": [message]})


def set_phase(
    scan_id: str,
    phase: str,
    *,
    progress: int | None = None,
    source: str | None = None,
    keyword: str | None = None,
) -> None:
    """Update the human-readable phase string + an optional progress %.
    Frontend polls /api/direct/scans/{id} every 2s and reads these fields."""
    payload: dict = {"phase": phase}
    if progress is not None:
        payload["progress"] = max(0, min(100, int(progress)))
    if source is not None:
        payload["current_source"] = source
    if keyword is not None:
        payload["current_keyword"] = keyword
    update(scan_id, payload)


def mark_running(scan_id: str) -> None:
    update(scan_id, {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "progress": 10,
    })


def mark_completed(scan_id: str, leads_found: int, emails_extracted: int = 0) -> None:
    update(scan_id, {
        "status": "completed",
        "progress": 100,
        "leads_found": leads_found,
        "emails_extracted": emails_extracted,
        "finished_at": datetime.utcnow().isoformat(),
    })


def mark_failed(scan_id: str, error: str) -> None:
    update(scan_id, {
        "status": "failed",
        "error": str(error),
        "finished_at": datetime.utcnow().isoformat(),
    })
