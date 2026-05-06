"""Saved searches — Supabase-backed.

Replaces the legacy saved_searches.json file. Used by:
  - direct_leads router (CRUD endpoints)
  - scheduler (picks searches with next_run_at <= now)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from backend.services.supabase_client import get_client


_FIELDS = (
    "id, name, type, keywords, sources, locations, niches, frequency, "
    "max_results, is_paused, last_run_at, next_run_at, created_at, updated_at"
)


def get_all() -> list[dict[str, Any]]:
    resp = (
        get_client()
        .table("saved_searches")
        .select(_FIELDS)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def get_by_id(search_id: str) -> Optional[dict[str, Any]]:
    resp = (
        get_client()
        .table("saved_searches")
        .select(_FIELDS)
        .eq("id", search_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def create(payload: dict[str, Any]) -> dict[str, Any]:
    row = {
        "name": payload.get("name") or "Untitled search",
        "type": payload.get("type") or "direct",
        "keywords": payload.get("keywords") or [],
        "sources": payload.get("sources") or [],
        "locations": payload.get("locations") or [],
        "niches": payload.get("niches") or [],
        "frequency": payload.get("frequency") or "daily",
        "max_results": int(payload.get("max_results") or 50),
        "is_paused": bool(payload.get("is_paused") or False),
    }
    resp = get_client().table("saved_searches").insert(row).execute()
    return (resp.data or [None])[0]


def update(search_id: str, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    row = {
        k: payload[k]
        for k in (
            "name", "type", "keywords", "sources", "locations", "niches",
            "frequency", "max_results", "is_paused",
            "last_run_at", "next_run_at",
        )
        if k in payload
    }
    if not row:
        return get_by_id(search_id)
    resp = (
        get_client()
        .table("saved_searches")
        .update(row)
        .eq("id", search_id)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def delete(search_id: str) -> bool:
    resp = (
        get_client()
        .table("saved_searches")
        .delete()
        .eq("id", search_id)
        .execute()
    )
    return bool(resp.data)


def mark_run_started(search_id: str) -> None:
    get_client().table("saved_searches").update(
        {"last_run_at": datetime.utcnow().isoformat()}
    ).eq("id", search_id).execute()
