"""Email template CRUD — Supabase-backed.

Templates live in the `templates` table. Defaults are seeded at schema-init
time, not on first read, so this module never writes seed data.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from backend.services.supabase_client import get_client


_FIELDS = "id, name, subject, body, persona, is_default, created_at, updated_at"


def get_all() -> list[dict[str, Any]]:
    resp = (
        get_client()
        .table("templates")
        .select(_FIELDS)
        .order("is_default", desc=True)
        .order("name")
        .execute()
    )
    return resp.data or []


def get_by_id(template_id: str) -> Optional[dict[str, Any]]:
    resp = (
        get_client()
        .table("templates")
        .select(_FIELDS)
        .eq("id", template_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def create(payload: dict[str, Any]) -> dict[str, Any]:
    row = {
        "name": payload.get("name") or "Untitled",
        "subject": payload.get("subject") or "",
        "body": payload.get("body") or "",
        "persona": payload.get("persona"),
    }
    resp = get_client().table("templates").insert(row).execute()
    return (resp.data or [None])[0]


def update(template_id: str, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    row = {
        k: payload[k]
        for k in ("name", "subject", "body", "persona")
        if k in payload
    }
    if not row:
        return get_by_id(template_id)
    resp = (
        get_client()
        .table("templates")
        .update(row)
        .eq("id", template_id)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def delete(template_id: str) -> bool:
    resp = (
        get_client()
        .table("templates")
        .delete()
        .eq("id", template_id)
        .execute()
    )
    return bool(resp.data)
