"""User settings — Supabase-backed.

Persisted in `app_settings` as one row per top-level section:
  key='profile'  → profile JSON
  key='email'    → SMTP / IMAP / sender JSON
  key='scraping' → proxy / concurrency JSON

Two read paths:
  - get_masked(): API responses; SMTP password replaced with `••••••••`
  - get_raw():    backend internals; returns real password
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.services.supabase_client import get_client


_PASSWORD_MASK = "••••••••"

_SECTIONS = ("profile", "email", "scraping")

_DEFAULTS: dict[str, Any] = {
    "profile": {
        "name": "",
        "skills": [],
        "services": [],
        "hourly_rate": 0,
        "min_budget": 0,
    },
    "email": {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "sender_name": "Lead Prospector",
        "from_email": "",
        # Plan 10 — IMAP for reply detection
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "imap_user": "",
        "imap_password": "",
        # Plan 10 — sender-rate throttling state
        "daily_send_cap": 30,
    },
    "scraping": {
        "proxy_url": None,
        "max_concurrent": 5,
    },
}


def _fetch_section(key: str) -> dict[str, Any]:
    resp = (
        get_client()
        .table("app_settings")
        .select("value")
        .eq("key", key)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return {}
    val = rows[0].get("value") or {}
    return val if isinstance(val, dict) else {}


def _save_section(key: str, value: dict[str, Any]) -> None:
    get_client().table("app_settings").upsert(
        {"key": key, "value": value},
        on_conflict="key",
    ).execute()


def _read_raw() -> dict[str, Any]:
    out = deepcopy(_DEFAULTS)
    for section in _SECTIONS:
        loaded = _fetch_section(section)
        if loaded:
            out[section].update(loaded)
    return out


def get_raw() -> dict[str, Any]:
    """Real settings (real password) — backend only."""
    return _read_raw()


def get_masked() -> dict[str, Any]:
    """Mask SMTP + IMAP passwords for the API surface."""
    out = _read_raw()
    if out["email"]["smtp_password"]:
        out["email"]["smtp_password"] = _PASSWORD_MASK
    if out["email"].get("imap_password"):
        out["email"]["imap_password"] = _PASSWORD_MASK
    return out


def save(incoming: dict[str, Any]) -> None:
    """Persist incoming settings. Mask placeholders (or empty) preserve the
    existing password — treats them as 'no change'."""
    current = _read_raw()
    merged = deepcopy(_DEFAULTS)
    for section in _SECTIONS:
        merged[section].update(current.get(section, {}))
        if section in incoming and isinstance(incoming[section], dict):
            merged[section].update(incoming[section])

    # Preserve real passwords when user submits mask / empty.
    for pw_key in ("smtp_password", "imap_password"):
        incoming_pw = (incoming.get("email") or {}).get(pw_key, "")
        if not incoming_pw or incoming_pw == _PASSWORD_MASK:
            merged["email"][pw_key] = current["email"].get(pw_key, "")

    for section in _SECTIONS:
        _save_section(section, merged[section])
