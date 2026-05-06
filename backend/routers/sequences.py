"""Sequences router — enroll leads, list sequences, manage enrollments."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import sequence_worker
from backend.services.supabase_client import get_client


router = APIRouter(prefix="/api/sequences", tags=["sequences"])


@router.get("")
async def list_sequences() -> dict[str, Any]:
    """List every sequence with its step count + active enrollment count."""
    client = get_client()
    seqs = (
        client.table("sequences")
        .select("id, name, description, is_active, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    out: list[dict[str, Any]] = []
    for s in seqs.data or []:
        steps = (
            client.table("sequence_steps")
            .select("id, step_index, delay_days, template_id", count="exact")
            .eq("sequence_id", s["id"])
            .execute()
        )
        active = (
            client.table("sequence_enrollments")
            .select("id", count="exact")
            .eq("sequence_id", s["id"])
            .eq("status", "active")
            .execute()
        )
        out.append({
            **s,
            "step_count": steps.count or 0,
            "active_enrollments": active.count or 0,
        })
    return {"sequences": out}


@router.get("/{sequence_id}")
async def get_sequence(sequence_id: str) -> dict[str, Any]:
    client = get_client()
    seq_resp = (
        client.table("sequences")
        .select("*")
        .eq("id", sequence_id)
        .limit(1)
        .execute()
    )
    seqs = seq_resp.data or []
    if not seqs:
        raise HTTPException(status_code=404, detail="Sequence not found")

    steps_resp = (
        client.table("sequence_steps")
        .select(
            "id, step_index, delay_days, template_id, reuse_subject_thread, "
            "templates(id, name, subject, body)"
        )
        .eq("sequence_id", sequence_id)
        .order("step_index")
        .execute()
    )

    return {**seqs[0], "steps": steps_resp.data or []}


class EnrollRequest(BaseModel):
    opportunity_ids: list[str]
    sequence_id: str


@router.post("/enroll")
async def enroll_leads(req: EnrollRequest) -> dict[str, Any]:
    """Bulk-enroll leads into a sequence. Returns per-lead status."""
    if not req.opportunity_ids:
        raise HTTPException(status_code=400, detail="opportunity_ids required")

    enrolled: list[str] = []
    skipped: list[str] = []
    for opp_id in req.opportunity_ids:
        if sequence_worker.enroll(opp_id, req.sequence_id):
            enrolled.append(opp_id)
        else:
            skipped.append(opp_id)
    return {
        "enrolled": len(enrolled),
        "skipped": len(skipped),
        "skipped_ids": skipped,
    }


@router.get("/enrollments/{opportunity_id}")
async def get_enrollments(opportunity_id: str) -> dict[str, Any]:
    """Show every sequence this lead is in (active or finished)."""
    resp = (
        get_client()
        .table("sequence_enrollments")
        .select(
            "id, sequence_id, current_step, status, next_send_at, "
            "enrolled_at, completed_at, sequences(name)"
        )
        .eq("opportunity_id", opportunity_id)
        .order("enrolled_at", desc=True)
        .execute()
    )
    return {"enrollments": resp.data or []}


@router.post("/enrollments/{enrollment_id}/pause")
async def pause_enrollment(enrollment_id: str) -> dict[str, Any]:
    sequence_worker.pause(enrollment_id)
    return {"ok": True, "id": enrollment_id, "status": "paused"}


@router.delete("/enrollments/{enrollment_id}")
async def cancel_enrollment(enrollment_id: str) -> dict[str, Any]:
    resp = (
        get_client()
        .table("sequence_enrollments")
        .delete()
        .eq("id", enrollment_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return {"ok": True}
