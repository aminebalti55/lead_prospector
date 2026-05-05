"""User settings persistence (JSON file).

Two read paths:
  - get_masked(): for API responses; SMTP password is replaced with `••••••••`
  - get_raw():    for backend use (outreach send); returns real password
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.core.config import OUTPUT_DIR


_SETTINGS_FILE: Path = OUTPUT_DIR / "settings.json"
_PASSWORD_MASK = "••••••••"


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
    },
    "scraping": {
        "proxy_url": None,
        "max_concurrent": 5,
    },
}


def _read_raw() -> dict[str, Any]:
    """Read raw settings from disk; merge with defaults so missing keys are filled."""
    out = deepcopy(_DEFAULTS)
    if not _SETTINGS_FILE.exists():
        return out
    try:
        data = json.loads(_SETTINGS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return out
    if not isinstance(data, dict):
        return out
    # Shallow-merge each section so a missing key falls back to the default
    for section in ("profile", "email", "scraping"):
        if section in data and isinstance(data[section], dict):
            out[section].update(data[section])
    return out


def get_raw() -> dict[str, Any]:
    """Read settings WITH the real SMTP password — for backend use only."""
    return _read_raw()


def get_masked() -> dict[str, Any]:
    """Read settings with SMTP password masked — for API responses."""
    out = _read_raw()
    if out["email"]["smtp_password"]:
        out["email"]["smtp_password"] = _PASSWORD_MASK
    else:
        out["email"]["smtp_password"] = ""
    return out


def save(incoming: dict[str, Any]) -> None:
    """Write settings to disk. The incoming password is preserved if it's the
    mask placeholder or empty (treats those as 'no change')."""
    current = _read_raw()
    merged = deepcopy(_DEFAULTS)
    for section in ("profile", "email", "scraping"):
        merged[section].update(current.get(section, {}))
        if section in incoming and isinstance(incoming[section], dict):
            merged[section].update(incoming[section])

    # Preserve real password if user submitted mask placeholder or empty
    incoming_pw = (incoming.get("email") or {}).get("smtp_password", "")
    if not incoming_pw or incoming_pw == _PASSWORD_MASK:
        merged["email"]["smtp_password"] = current["email"]["smtp_password"]

    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(merged, indent=2))
