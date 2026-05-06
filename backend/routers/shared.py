"""Shared root endpoints — health + Supabase connectivity probe.

Dashboard stats live in `/api/hub/stats`. Email send + bulk send live in
`/api/outreach/*`. Templates live in `/api/templates`. This module used to
host every kitchen-sink endpoint; we kept it down to the connectivity probe.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.services.supabase_client import verify_connection

router = APIRouter(tags=["shared"])


@router.get("/api/health")
async def health() -> dict[str, Any]:
    """Liveness check + Supabase connectivity probe."""
    sb = verify_connection()
    return {"ok": sb.get("supabase") == "ok", "supabase": sb}
