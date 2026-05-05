"""Unified opportunities router — read-aggregator across cold + direct stores."""
from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.core.storage import list_files, read_leads, update_lead
from src.core.models import DirectLead, Stage
from backend.services.opportunity_aggregator import (
    cold_row_to_opportunity,
    direct_lead_to_opportunity,
)

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


class StagePatch(BaseModel):
    stage: Stage


def _load_all_opportunities() -> list[dict]:
    """Read every cold + direct + legacy file and project to Opportunity dicts."""
    out: list[dict] = []

    # Cold (and legacy) files — rows are dicts already.
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

    # Direct files — rows are dicts mapped from DirectLead columns.
    for f in list_files("direct"):
        try:
            _, rows = read_leads(f["name"], "direct")
        except Exception:
            continue
        for row in rows:
            # Re-hydrate enough of a DirectLead to reuse the converter.
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
                matched_skills=[
                    s.strip()
                    for s in (row.get("Matched_Skills") or "").split(",")
                    if s.strip()
                ],
                outreach_status=row.get("Outreach_Status") or "new",
                notes=row.get("Notes") or "",
            )
            # DirectLead.__post_init__ recomputes lead_id from source|url; if we
            # have an explicit Lead_ID in the row, prefer it (handles legacy data).
            if row.get("Lead_ID"):
                lead.lead_id = str(row["Lead_ID"])
            opp = direct_lead_to_opportunity(lead, source_file=f["name"])
            if opp.id:
                out.append(asdict(opp))

    return out


@router.get("")
async def list_opportunities(
    type: Optional[str] = Query(None, pattern="^(direct|cold)$"),
    priority: Optional[str] = Query(None, pattern="^(hot|warm|cold)$"),
    stage: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    sort: str = Query("score", pattern="^(score|value|recent)$"),
    limit: int = Query(200, ge=1, le=2000),
):
    items = _load_all_opportunities()

    # Filter
    if type:
        items = [o for o in items if o["type"] == type]
    if priority:
        items = [o for o in items if o["priority"] == priority]
    if stage:
        items = [o for o in items if o["stage"] == stage]
    if source:
        items = [o for o in items if o["source"] == source]
    if q:
        ql = q.lower()
        items = [
            o
            for o in items
            if ql in (o["title"] or "").lower()
            or ql in (o["company_name"] or "").lower()
            or ql in (o["source"] or "").lower()
            or ql in (o["location"] or "").lower()
            or ql in (o["description"] or "").lower()
        ]

    # Sort
    if sort == "score":
        items.sort(key=lambda o: o["score"], reverse=True)
    elif sort == "value":
        items.sort(key=lambda o: o["estimated_value_usd"], reverse=True)
    elif sort == "recent":
        items.sort(key=lambda o: o["posted_date"] or "", reverse=True)

    total = len(items)
    items = items[:limit]
    return {"opportunities": items, "total": total}


@router.get("/{opp_id}")
async def get_opportunity(opp_id: str):
    for opp in _load_all_opportunities():
        if opp["id"] == opp_id:
            return opp
    raise HTTPException(status_code=404, detail="Opportunity not found")


@router.patch("/{opp_id}/stage")
async def update_opportunity_stage(opp_id: str, patch: StagePatch):
    """Persist stage change to the underlying Excel file via storage.update_lead.

    storage.update_lead writes to the `Outreach_Status` column."""
    for opp in _load_all_opportunities():
        if opp["id"] != opp_id:
            continue
        section = "cold" if opp["type"] == "cold" else "direct"
        try:
            update_lead(
                opp["source_file"],
                opp["raw_lead_id"],
                {"Outreach_Status": patch.stage.value},
                section,
            )
        except (KeyError, FileNotFoundError) as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"ok": True, "id": opp_id, "stage": patch.stage.value}
    raise HTTPException(status_code=404, detail="Opportunity not found")
