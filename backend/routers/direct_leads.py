"""Direct leads router — scan management + lead CRUD."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from src.core.storage import list_files, read_leads, update_lead
from src.core.config import DIRECT_OUTPUT_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/direct", tags=["direct-leads"])

SAVED_SEARCHES_FILE = DIRECT_OUTPUT_DIR / "saved_searches.json"
SCANS_FILE = DIRECT_OUTPUT_DIR / "scans.json"


# ── Scan state management ────────────────────────────────────────────

def _load_scans() -> list[dict]:
    if not SCANS_FILE.exists():
        return []
    try:
        return json.loads(SCANS_FILE.read_text())
    except Exception:
        return []


def _save_scans(scans: list[dict]) -> None:
    SCANS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCANS_FILE.write_text(json.dumps(scans, indent=2, default=str))


def _update_scan(scan_id: str, updates: dict) -> None:
    scans = _load_scans()
    for s in scans:
        if s["id"] == scan_id:
            s.update(updates)
            break
    _save_scans(scans)


# ── Scan endpoints ───────────────────────────────────────────────────

@router.post("/scans")
async def create_scan(body: dict):
    """Start a new direct lead scan."""
    scan_id = uuid.uuid4().hex[:8]

    scan = {
        "id": scan_id,
        "status": "queued",
        "sources": body.get("sources", []),
        "source_configs": body.get("source_configs", {}),
        "keywords": body.get("keywords", []),
        "max_results": body.get("max_results", 50),
        "progress": 0,
        "leads_found": 0,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "finished_at": None,
        "error": None,
        "logs": [],
    }

    scans = _load_scans()
    scans.insert(0, scan)
    _save_scans(scans)

    # Launch background scan task
    asyncio.create_task(_execute_scan(scan_id, body))

    return {
        "scan_id": scan_id,
        "status": "queued",
        "message": "Scan started",
    }


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str):
    for s in _load_scans():
        if s["id"] == scan_id:
            return s
    raise HTTPException(status_code=404, detail="Scan not found")


@router.get("/scans")
async def list_scans():
    return {"scans": _load_scans()}


# ── Scan execution (background task) ────────────────────────────────

async def _execute_scan(scan_id: str, params: dict) -> None:
    """Run the direct leads scan using the real pipeline."""
    sources = params.get("sources", [])
    source_configs = params.get("source_configs", {})
    keywords = params.get("keywords", [])
    max_results = params.get("max_results", 50)

    _update_scan(scan_id, {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "progress": 10,
        "logs": ["Initializing pipeline..."],
    })

    try:
        from src.direct_leads.pipeline import DirectLeadsPipeline

        pipeline = DirectLeadsPipeline()

        def on_progress(msg: str):
            _update_scan(scan_id, {"logs": [msg]})
            logger.info(f"[SCAN {scan_id}] {msg}")

        _update_scan(scan_id, {
            "progress": 20,
            "logs": [f"Scraping {len(sources)} sources for {len(keywords)} keywords..."],
        })

        output_files = await pipeline.run(
            keywords=keywords,
            sources=sources if sources else None,
            max_results=max_results,
            progress_callback=on_progress,
            source_configs=source_configs,
        )

        # Count leads from the output files
        total_leads = 0
        if output_files:
            import pandas as pd
            for fpath in output_files:
                try:
                    df = pd.read_excel(fpath)
                    total_leads += len(df)
                except Exception:
                    pass

        _update_scan(scan_id, {
            "status": "completed",
            "progress": 100,
            "leads_found": total_leads,
            "output_files": [Path(f).name for f in output_files],
            "finished_at": datetime.utcnow().isoformat(),
            "logs": [f"Done — {total_leads} leads found across {len(output_files)} file(s)."],
        })
        logger.info(f"[SCAN {scan_id}] Completed: {total_leads} leads")

    except Exception as e:
        logger.error(f"[SCAN {scan_id}] Failed: {e}", exc_info=True)
        _update_scan(scan_id, {
            "status": "failed",
            "error": str(e),
            "finished_at": datetime.utcnow().isoformat(),
            "logs": [f"Error: {e}"],
        })


# ── Lead endpoints ───────────────────────────────────────────────────

@router.get("/leads")
async def list_direct_leads():
    """List all direct leads across all files."""
    all_leads: list[dict] = []
    for f in list_files("direct"):
        try:
            _, rows = read_leads(f["name"], "direct")
            all_leads.extend(rows)
        except Exception:
            continue
    return {"leads": all_leads, "total": len(all_leads)}


@router.get("/leads/{lead_id}")
async def get_direct_lead(lead_id: str):
    for f in list_files("direct"):
        try:
            _, rows = read_leads(f["name"], "direct")
            for row in rows:
                if row.get("Lead_ID") == lead_id:
                    return row
        except Exception:
            continue
    raise HTTPException(status_code=404, detail="Lead not found")


@router.patch("/leads/{lead_id}")
async def update_direct_lead(lead_id: str, body: dict):
    for f in list_files("direct"):
        try:
            update_lead(f["name"], lead_id, body, "direct")
            return {"ok": True}
        except (KeyError, FileNotFoundError):
            continue
    raise HTTPException(status_code=404, detail="Lead not found")


# ── Saved searches CRUD ─────────────────────────────────────────────

def _load_searches() -> list[dict]:
    if not SAVED_SEARCHES_FILE.exists():
        return []
    return json.loads(SAVED_SEARCHES_FILE.read_text())


def _save_searches(searches: list[dict]) -> None:
    SAVED_SEARCHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SAVED_SEARCHES_FILE.write_text(json.dumps(searches, indent=2))


@router.get("/saved-searches")
async def list_saved_searches():
    return {"searches": _load_searches()}


@router.post("/saved-searches")
async def create_saved_search(body: dict):
    searches = _load_searches()
    search = {
        "id": str(uuid.uuid4())[:8],
        **body,
        "last_run": None,
        "enabled": True,
    }
    searches.append(search)
    _save_searches(searches)
    return search


@router.put("/saved-searches/{search_id}")
async def update_saved_search(search_id: str, body: dict):
    searches = _load_searches()
    for s in searches:
        if s["id"] == search_id:
            s.update(body)
            _save_searches(searches)
            return s
    raise HTTPException(status_code=404, detail="Saved search not found")


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(search_id: str):
    searches = _load_searches()
    before = len(searches)
    searches = [s for s in searches if s["id"] != search_id]
    if len(searches) == before:
        raise HTTPException(status_code=404, detail="Saved search not found")
    _save_searches(searches)
    return {"ok": True}
