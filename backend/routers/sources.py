"""Sources index + per-source actions: list, run-now, toggle."""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from src.core.config import DIRECT_OUTPUT_DIR
from src.core.storage import list_files, read_leads
from src.core.models import DirectLead
from backend.services import source_state
from backend.services.opportunity_aggregator import (
    cold_row_to_opportunity,
    direct_lead_to_opportunity,
)
from backend.services.source_metrics import compute_source_summary
from backend.services.hub_aggregator import _KNOWN_DIRECT_SOURCES, _KNOWN_COLD_SOURCES

router = APIRouter(prefix="/api/sources", tags=["sources"])

SCANS_FILE = DIRECT_OUTPUT_DIR / "scans.json"

ALL_KNOWN_SOURCES: list[str] = list(_KNOWN_DIRECT_SOURCES) + list(_KNOWN_COLD_SOURCES)


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


def _parse_iso_to_dt(value):
    """Lenient ISO parser for re-hydrating DirectLead.posted_date from Excel rows."""
    from datetime import datetime as _dt
    if not value:
        return None
    if isinstance(value, _dt):
        return value
    try:
        return _dt.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _load_all_opportunity_dicts() -> list[dict]:
    """Same shape as opportunities/hub routers — read everything as Opportunity dicts."""
    from dataclasses import asdict
    out: list[dict] = []
    for section in ("cold", "legacy"):
        for f in list_files(section):
            try:
                _, rows = read_leads(f["name"], section)
            except Exception:
                continue
            for row in rows:
                opp = cold_row_to_opportunity(row, source_file=f["name"])
                if opp.id:
                    out.append(asdict(opp))
    for f in list_files("direct"):
        try:
            _, rows = read_leads(f["name"], "direct")
        except Exception:
            continue
        for row in rows:
            lead = DirectLead(
                source=row.get("Source") or "",
                title=row.get("Title") or "",
                description=row.get("Description") or "",
                url=row.get("URL") or "",
                company_name=row.get("Company") or "",
                company_website=row.get("Company_Website") or "",
                location=row.get("Location") or "",
                contact_name=row.get("Contact_Name") or "",
                contact_email=row.get("Contact_Email") or "",
                contact_phone=row.get("Contact_Phone") or "",
                relevance_score=int(row.get("Relevance_Score") or 0),
                budget_signal=row.get("Budget_Signal") or "",
                urgency_signal=row.get("Urgency_Signal") or "",
                matched_skills=[s.strip() for s in (row.get("Matched_Skills") or "").split(",") if s.strip()],
                outreach_status=row.get("Outreach_Status") or "new",
                notes=row.get("Notes") or "",
                posted_date=_parse_iso_to_dt(row.get("Posted_Date")),
            )
            if row.get("Lead_ID"):
                lead.lead_id = str(row["Lead_ID"])
            opp = direct_lead_to_opportunity(lead, source_file=f["name"])
            if opp.id:
                out.append(asdict(opp))
    return out


def _last_keywords_for_source(source: str, scans: list[dict]) -> list[str] | None:
    """Find the most recent scan that includes this source and return its keywords."""
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
    scans = _load_scans()
    opps = _load_all_opportunity_dicts()
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
    scans = _load_scans()
    keywords = _last_keywords_for_source(name, scans)
    if not keywords:
        raise HTTPException(
            status_code=400,
            detail="No prior scan history for this source — please run a saved search with keywords first, or use the New Scan form.",
        )
    # Reuse the existing direct-leads scan creation flow.
    from backend.routers.direct_leads import _execute_scan, _save_scans as _save_scans_dl
    scan_id = uuid.uuid4().hex[:8]
    scan = {
        "id": scan_id,
        "status": "queued",
        "sources": [name],
        "source_configs": {},
        "keywords": keywords,
        "max_results": 50,
        "progress": 0,
        "leads_found": 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "started_at": None,
        "finished_at": None,
        "error": None,
        "logs": [],
    }
    scans.insert(0, scan)
    _save_scans_dl(scans)
    asyncio.create_task(_execute_scan(scan_id, {"sources": [name], "keywords": keywords, "max_results": 50}))
    return {"source": name, "scan_id": scan_id, "keywords": keywords, "status": "queued"}
