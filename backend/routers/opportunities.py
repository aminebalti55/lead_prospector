"""Opportunities router — Supabase-backed.

Replaces the previous Excel-aggregator implementation. Every read and write
goes through the service-role Supabase client.
"""
from __future__ import annotations

from datetime import datetime as _dt
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.core.models import Stage
from backend.services.supabase_client import get_client

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


class StagePatch(BaseModel):
    stage: Stage


# Columns the API surfaces. Aliases the Supabase row to the legacy
# Opportunity shape the frontend already consumes.
_OPP_FIELDS = (
    "id, type, source, lead_subtype, title, description, url, "
    "posted_date, company_name, location, contact_email, contact_phone, "
    "score, priority, stage, estimated_value_usd, "
    "matched_skills, budget_signal, urgency_signal, pain_tags, notes, "
    "source_file"
)


def _row_to_opportunity(row: dict) -> dict:
    """Project a Supabase row to the Opportunity dict the frontend expects."""
    return {
        "id": row["id"],
        "type": row["type"],
        "source": row["source"],
        "lead_subtype": row.get("lead_subtype") or "hiring",
        "title": row.get("title") or "",
        "description": row.get("description") or "",
        "url": row.get("url") or "",
        "posted_date": row.get("posted_date"),
        "company_name": row.get("company_name") or "",
        "location": row.get("location") or "",
        "contact_email": row.get("contact_email") or "",
        "contact_phone": row.get("contact_phone") or "",
        "score": int(row.get("score") or 0),
        "priority": row.get("priority") or "cold",
        "stage": row.get("stage") or "new",
        "estimated_value_usd": int(row.get("estimated_value_usd") or 0),
        "matched_skills": row.get("matched_skills") or [],
        "budget_signal": row.get("budget_signal") or "",
        "urgency_signal": row.get("urgency_signal") or "",
        "pain_tags": row.get("pain_tags") or [],
        "notes": row.get("notes") or "",
        # Legacy alias kept for the frontend hook signature; backed by id.
        "source_file": row.get("source_file") or "",
        "raw_lead_id": row["id"],
    }


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
    client = get_client()
    query = client.table("opportunities").select(_OPP_FIELDS, count="exact")

    if type:
        query = query.eq("type", type)
    if priority:
        query = query.eq("priority", priority)
    if stage:
        query = query.eq("stage", stage)
    if source:
        query = query.eq("source", source)
    if q:
        # PostgREST `or` filter — search across title/company/source/location/description.
        # `.ilike` does case-insensitive substring matching with `%pattern%`.
        ql = q.replace("%", r"\%").replace(",", " ")
        pattern = f"%{ql}%"
        query = query.or_(
            f"title.ilike.{pattern},"
            f"company_name.ilike.{pattern},"
            f"source.ilike.{pattern},"
            f"location.ilike.{pattern},"
            f"description.ilike.{pattern}"
        )

    if sort == "score":
        query = query.order("score", desc=True)
    elif sort == "value":
        query = query.order("estimated_value_usd", desc=True)
    elif sort == "recent":
        # Postgres NULLs default to "first" on desc; force them last so
        # cold prospects (no posted_date) don't crowd recent direct leads.
        query = query.order("posted_date", desc=True, nullsfirst=False)

    query = query.limit(limit)

    try:
        resp = query.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase query failed: {e}")

    items = [_row_to_opportunity(r) for r in (resp.data or [])]
    total = resp.count if resp.count is not None else len(items)
    return {"opportunities": items, "total": total}


@router.get("/{opp_id}")
async def get_opportunity(opp_id: str):
    client = get_client()
    resp = (
        client.table("opportunities")
        .select(_OPP_FIELDS)
        .eq("id", opp_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return _row_to_opportunity(rows[0])


@router.patch("/{opp_id}/stage")
async def update_opportunity_stage(opp_id: str, patch: StagePatch):
    """Persist stage change directly to Supabase. Outreach send code uses
    this same column to mark leads contacted."""
    client = get_client()
    payload = {"stage": patch.stage.value}
    if patch.stage.value == "contacted":
        payload["last_contacted"] = _dt.utcnow().isoformat()

    try:
        resp = (
            client.table("opportunities")
            .update(payload)
            .eq("id", opp_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase update failed: {e}")

    if not resp.data:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"ok": True, "id": opp_id, "stage": patch.stage.value}
