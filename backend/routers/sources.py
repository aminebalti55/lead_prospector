"""Sources index + per-source actions: list, run-now, toggle.

Supabase-backed — pulls every opportunity + recent scan once per request.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.services import scans_store, source_state
from backend.services.hub_aggregator import _KNOWN_COLD_SOURCES, _KNOWN_DIRECT_SOURCES
from backend.services.source_metrics import compute_source_summary
from backend.services.supabase_client import get_client


router = APIRouter(prefix="/api/sources", tags=["sources"])

ALL_KNOWN_SOURCES: list[str] = list(_KNOWN_DIRECT_SOURCES) + list(_KNOWN_COLD_SOURCES)


def _all_opportunities() -> list[dict]:
    resp = (
        get_client()
        .table("opportunities")
        .select(
            "id, type, source, posted_date, contact_email, contact_phone, "
            "stage, score, priority, estimated_value_usd"
        )
        .limit(5000)
        .execute()
    )
    rows = resp.data or []
    # Project to the shape compute_source_summary expects.
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "source": r["source"],
            "posted_date": r.get("posted_date"),
            "contact_email": r.get("contact_email") or "",
            "contact_phone": r.get("contact_phone") or "",
            "stage": r.get("stage") or "new",
            "score": int(r.get("score") or 0),
            "priority": r.get("priority") or "cold",
            "estimated_value_usd": int(r.get("estimated_value_usd") or 0),
        }
        for r in rows
    ]


def _last_keywords_for_source(source: str, scans: list[dict]) -> list[str] | None:
    matching = [s for s in scans if source in (s.get("sources") or []) and s.get("keywords")]
    matching.sort(
        key=lambda s: s.get("finished_at") or s.get("started_at") or s.get("created_at") or "",
        reverse=True,
    )
    if not matching:
        return None
    return list(matching[0].get("keywords") or [])


@router.get("")
async def list_sources() -> dict[str, Any]:
    scans = scans_store.list_all(limit=200)
    opps = _all_opportunities()
    sources = [
        compute_source_summary(
            source=name,
            scans=scans,
            opportunities=opps,
            enabled=source_state.is_enabled(name),
        )
        for name in ALL_KNOWN_SOURCES
    ]
    return {"sources": sources}


@router.post("/{name}/toggle")
async def toggle_source(name: str) -> dict[str, Any]:
    if name not in ALL_KNOWN_SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown source: {name}")
    new_value = source_state.toggle(name)
    return {"source": name, "enabled": new_value}


@router.post("/{name}/run")
async def run_source(name: str) -> dict[str, Any]:
    if name not in ALL_KNOWN_SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown source: {name}")

    scans = scans_store.list_all(limit=200)
    keywords = _last_keywords_for_source(name, scans)
    if not keywords:
        raise HTTPException(
            status_code=400,
            detail=(
                "No prior scan history for this source — please run a saved "
                "search with keywords first, or use the New Scan form."
            ),
        )

    is_cold = name in _KNOWN_COLD_SOURCES
    scan = scans_store.create({
        "type": "cold" if is_cold else "direct",
        "status": "queued",
        "sources": [name],
        "keywords": keywords,
        "max_results": 50,
    })

    if is_cold:
        # Cold sources need a location — fall back to last scan's location.
        last_cold = next(
            (s for s in scans if s.get("type") == "cold" and (s.get("locations") or [])),
            None,
        )
        locations = (last_cold or {}).get("locations") or ["Austin, TX"]
        niches = (last_cold or {}).get("niches") or ["plumbing"]
        from backend.routers.cold_outreach import _execute_scan as _exec_cold
        asyncio.create_task(_exec_cold(scan["id"], {
            "locations": locations,
            "niches": niches,
            "skip_scrapers": [s for s in _KNOWN_COLD_SOURCES if s != name],
            "skip_audit": False,
            "fetch_emails": True,
            "fetch_details": True,
            "max_results": 50,
        }))
    else:
        from backend.routers.direct_leads import _execute_scan as _exec_direct
        asyncio.create_task(_exec_direct(scan["id"], {
            "sources": [name],
            "keywords": keywords,
            "max_results": 50,
        }))

    return {
        "source": name, "scan_id": scan["id"],
        "keywords": keywords, "status": "queued",
    }
