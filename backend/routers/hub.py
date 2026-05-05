"""Hub + Pulse status endpoints. Read-aggregators over the existing storage."""
from __future__ import annotations

import json
from datetime import datetime as _dt, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Query

from src.core.config import DIRECT_OUTPUT_DIR, settings
from src.core.storage import list_files, read_leads
from src.core.models import DirectLead
from backend.services.opportunity_aggregator import (
    cold_row_to_opportunity,
    direct_lead_to_opportunity,
)
from backend.services.hub_aggregator import (
    compute_stats,
    compute_pulse_status,
    compute_activity,
)


def _parse_iso(value: object) -> Optional[_dt]:
    if not value:
        return None
    if isinstance(value, _dt):
        return value
    try:
        return _dt.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

router = APIRouter(tags=["hub"])

SCANS_FILE = DIRECT_OUTPUT_DIR / "scans.json"


def _load_scans() -> list[dict]:
    if not SCANS_FILE.exists():
        return []
    try:
        return json.loads(SCANS_FILE.read_text())
    except Exception:
        return []


def _load_all_opportunity_dicts() -> list[dict]:
    """Same logic as opportunities router — read everything as Opportunity dicts."""
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
                lead_subtype=row.get("Lead_Subtype") or "hiring",
                title=row.get("Title") or "",
                description=row.get("Description") or "",
                url=row.get("URL") or "",
                posted_date=_parse_iso(row.get("Posted_Date")),
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
            )
            if row.get("Lead_ID"):
                lead.lead_id = str(row["Lead_ID"])

            # Drop stale hiring posts on read (agencies bypass — no posted_date).
            if lead.lead_subtype != "agency" and lead.posted_date is not None:
                max_age = int(getattr(settings.direct_leads, "max_age_days", 30) or 30)
                cutoff = _dt.now() - timedelta(days=max_age)
                posted = lead.posted_date
                posted_naive = posted.replace(tzinfo=None) if posted.tzinfo else posted
                if posted_naive < cutoff:
                    continue

            opp = direct_lead_to_opportunity(lead, source_file=f["name"])
            if opp.id:
                out.append(asdict(opp))
    return out


@router.get("/api/hub/stats")
async def get_hub_stats() -> dict[str, Any]:
    opps = _load_all_opportunity_dicts()
    return compute_stats(opps)


@router.get("/api/hub/activity")
async def get_hub_activity(limit: int = Query(30, ge=1, le=200)) -> dict[str, Any]:
    opps = _load_all_opportunity_dicts()
    scans = _load_scans()
    return {"events": compute_activity(scans, opps, limit=limit)}


@router.get("/api/pulse/status")
async def get_pulse_status() -> dict[str, Any]:
    opps = _load_all_opportunity_dicts()
    scans = _load_scans()
    return {"sources": compute_pulse_status(scans, opps)}
