"""Per-source enabled flag — Supabase-backed (`app_settings` row 'source_state').

Default: every source is enabled. Disabling a source means the scheduler will
skip it when running saved searches. On-demand `POST /sources/{name}/run`
ignores this flag — explicit user action wins.
"""
from __future__ import annotations

from backend.services.supabase_client import get_client


_KEY = "source_state"


def get_all() -> dict[str, bool]:
    resp = (
        get_client()
        .table("app_settings")
        .select("value")
        .eq("key", _KEY)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return {}
    val = rows[0].get("value") or {}
    if not isinstance(val, dict):
        return {}
    return {str(k): bool(v) for k, v in val.items()}


def is_enabled(source: str) -> bool:
    return get_all().get(source, True)


def set_enabled(source: str, enabled: bool) -> None:
    state = get_all()
    state[source] = bool(enabled)
    get_client().table("app_settings").upsert(
        {"key": _KEY, "value": state},
        on_conflict="key",
    ).execute()


def toggle(source: str) -> bool:
    new_value = not is_enabled(source)
    set_enabled(source, new_value)
    return new_value
