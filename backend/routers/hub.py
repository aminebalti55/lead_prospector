"""Hub + Pulse status endpoints — Supabase-backed read-aggregators."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from backend.services import scans_store
from backend.services.hub_aggregator import (
    compute_activity,
    compute_pulse_status,
    compute_stats,
)
from backend.services.supabase_client import get_client


router = APIRouter(tags=["hub"])


_OPP_FIELDS = (
    "id, type, source, title, description, url, posted_date, "
    "company_name, location, contact_email, contact_phone, "
    "score, priority, stage, estimated_value_usd, "
    "matched_skills, budget_signal, urgency_signal, pain_tags, notes"
)


def _all_opportunities() -> list[dict]:
    """Return every opportunity as a flat dict — what the aggregator wants."""
    resp = (
        get_client()
        .table("opportunities")
        .select(_OPP_FIELDS)
        .limit(5000)
        .execute()
    )
    rows = resp.data or []
    # The aggregator reads `posted_date` as ISO string already — no conversion needed.
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "source": r["source"],
            "title": r.get("title") or "",
            "description": r.get("description") or "",
            "url": r.get("url") or "",
            "posted_date": r.get("posted_date"),
            "company_name": r.get("company_name") or "",
            "location": r.get("location") or "",
            "contact_email": r.get("contact_email") or "",
            "contact_phone": r.get("contact_phone") or "",
            "score": int(r.get("score") or 0),
            "priority": r.get("priority") or "cold",
            "stage": r.get("stage") or "new",
            "estimated_value_usd": int(r.get("estimated_value_usd") or 0),
            "matched_skills": r.get("matched_skills") or [],
            "budget_signal": r.get("budget_signal") or "",
            "urgency_signal": r.get("urgency_signal") or "",
            "pain_tags": r.get("pain_tags") or [],
            "notes": r.get("notes") or "",
        }
        for r in rows
    ]


@router.get("/api/hub/stats")
async def get_hub_stats() -> dict[str, Any]:
    return compute_stats(_all_opportunities())


@router.get("/api/hub/activity")
async def get_hub_activity(limit: int = Query(30, ge=1, le=200)) -> dict[str, Any]:
    return {"events": compute_activity(scans_store.list_all(limit=200), _all_opportunities(), limit=limit)}


@router.get("/api/pulse/status")
async def get_pulse_status() -> dict[str, Any]:
    return {"sources": compute_pulse_status(scans_store.list_all(limit=200), _all_opportunities())}
