"""Direct-leads router — Supabase-backed.

- POST /scans         create + dispatch a scan job
- GET  /scans         list recent scan records
- GET  /scans/{id}    one scan
- GET  /leads         all direct opportunities
- GET  /leads/{id}    one
- PATCH /leads/{id}   partial update (notes, stage, owner, …)
- saved-searches CRUD + on-demand run
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.services import saved_searches_store, scans_store
from backend.services.supabase_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/direct", tags=["direct-leads"])


_DEFAULT_SOURCES = [
    "reddit", "linkedin", "linkedin_posts", "indeed", "twitter",
    "clutch", "goodfirms", "tanit", "remoteok",
]


# ── Scan endpoints ────────────────────────────────────────────────────


@router.post("/scans")
async def create_scan(body: dict):
    sources = body.get("sources") or _DEFAULT_SOURCES
    keywords = body.get("keywords") or []
    scan = scans_store.create({
        "type": "direct",
        "status": "queued",
        "sources": sources,
        "keywords": keywords,
        "source_configs": body.get("source_configs") or {},
        "max_results": int(body.get("max_results") or 50),
    })
    asyncio.create_task(_execute_scan(scan["id"], {
        "sources": sources,
        "keywords": keywords,
        "source_configs": body.get("source_configs") or {},
        "max_results": int(body.get("max_results") or 50),
    }))
    return {"scan_id": scan["id"], "status": "queued", "message": "Scan started"}


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str):
    s = scans_store.get(scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    return s


@router.get("/scans")
async def list_scans():
    return {"scans": scans_store.list_all(limit=50)}


# ── Scan execution (background task) ────────────────────────────────


async def _execute_scan(scan_id: str, params: dict) -> None:
    sources = params.get("sources") or _DEFAULT_SOURCES
    keywords = params.get("keywords") or []
    source_configs = params.get("source_configs") or {}
    max_results = int(params.get("max_results") or 50)

    scans_store.mark_running(scan_id)
    scans_store.append_log(
        scan_id,
        f"Scraping {len(sources)} sources for {len(keywords)} keywords...",
    )

    try:
        from src.direct_leads.pipeline import DirectLeadsPipeline

        pipeline = DirectLeadsPipeline()

        def on_progress(msg: str):
            scans_store.append_log(scan_id, msg)
            logger.info(f"[SCAN {scan_id}] {msg}")

        ids = await pipeline.run(
            keywords=keywords,
            sources=sources,
            max_results=max_results,
            progress_callback=on_progress,
            source_configs=source_configs,
            scan_id=scan_id,
        )

        scans_store.mark_completed(scan_id, leads_found=len(ids))
        scans_store.append_log(scan_id, f"Done — {len(ids)} leads persisted.")
        logger.info(f"[SCAN {scan_id}] Completed: {len(ids)} leads")

    except Exception as e:
        logger.error(f"[SCAN {scan_id}] Failed: {e}", exc_info=True)
        scans_store.mark_failed(scan_id, str(e))
        scans_store.append_log(scan_id, f"Error: {e}")


# ── Lead endpoints ────────────────────────────────────────────────────


@router.get("/leads")
async def list_direct_leads():
    resp = (
        get_client()
        .table("opportunities")
        .select("id, source, title, description, url, contact_email, contact_phone, "
                "stage, score, priority, posted_date, company_name, location, "
                "matched_skills, budget_signal, urgency_signal", count="exact")
        .eq("type", "direct")
        .order("score", desc=True)
        .limit(500)
        .execute()
    )
    return {"leads": resp.data or [], "total": resp.count or 0}


@router.get("/leads/{lead_id}")
async def get_direct_lead(lead_id: str):
    resp = (
        get_client()
        .table("opportunities")
        .select("*")
        .eq("id", lead_id)
        .eq("type", "direct")
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Lead not found")
    return rows[0]


@router.patch("/leads/{lead_id}")
async def update_direct_lead(lead_id: str, body: dict):
    # Allow only writeable columns through. Names match Supabase columns.
    allowed = {
        "stage", "notes", "owner", "last_contacted", "follow_up_date",
        "contact_name", "contact_email", "contact_phone",
    }
    payload = {k: v for k, v in body.items() if k in allowed}
    if not payload:
        return {"ok": True}
    resp = (
        get_client()
        .table("opportunities")
        .update(payload)
        .eq("id", lead_id)
        .eq("type", "direct")
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"ok": True}


# ── Saved searches CRUD ──────────────────────────────────────────────


@router.get("/saved-searches")
async def list_saved_searches():
    return {"searches": saved_searches_store.get_all()}


@router.post("/saved-searches")
async def create_saved_search(body: dict):
    return saved_searches_store.create({**body, "type": "direct"})


@router.put("/saved-searches/{search_id}")
async def update_saved_search(search_id: str, body: dict):
    s = saved_searches_store.update(search_id, body)
    if not s:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return s


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(search_id: str):
    if not saved_searches_store.delete(search_id):
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"ok": True}


@router.post("/saved-searches/{search_id}/run")
async def run_saved_search_now(search_id: str):
    search = saved_searches_store.get_by_id(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    keywords = search.get("keywords") or []
    if not keywords:
        raise HTTPException(status_code=400, detail="Saved search has no keywords")

    sources = search.get("sources") or _DEFAULT_SOURCES
    max_results = int(search.get("max_results") or 50)

    scan = scans_store.create({
        "type": "direct",
        "status": "queued",
        "sources": sources,
        "keywords": keywords,
        "max_results": max_results,
    })
    saved_searches_store.mark_run_started(search_id)

    asyncio.create_task(_execute_scan(scan["id"], {
        "sources": sources,
        "keywords": keywords,
        "max_results": max_results,
    }))
    return {"scan_id": scan["id"], "status": "queued"}
