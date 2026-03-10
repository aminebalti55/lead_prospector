"""Direct leads router — new v2 endpoints."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.core.storage import list_files, read_leads, update_lead
from src.core.config import DIRECT_OUTPUT_DIR

router = APIRouter(prefix="/api/direct", tags=["direct-leads"])

SAVED_SEARCHES_FILE = DIRECT_OUTPUT_DIR / "saved_searches.json"


# ── Scan endpoints ────────────────────────────────────────────────────

@router.post("/scans")
async def create_scan(body: dict):
    """Start a new direct lead scan (placeholder — pipeline not yet wired)."""
    scan_id = uuid.uuid4().hex[:8]
    return {"scan_id": scan_id, "status": "queued", "message": "Direct leads pipeline not yet implemented"}


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str):
    return {"scan_id": scan_id, "status": "unknown", "message": "Scan tracking not yet implemented"}


@router.get("/scans")
async def list_scans():
    return {"scans": []}


# ── Lead endpoints ────────────────────────────────────────────────────

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


# ── Saved searches CRUD ──────────────────────────────────────────────

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
