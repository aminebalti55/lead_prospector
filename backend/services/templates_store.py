"""Email template CRUD with JSON file persistence and seeded defaults."""
from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.core.config import OUTPUT_DIR


_TEMPLATES_FILE: Path = OUTPUT_DIR / "email_templates.json"


# Seed data — same as the legacy hardcoded EMAIL_TEMPLATES in shared.py.
# Used only when the file doesn't exist yet.
_SEED: list[dict[str, Any]] = [
    {
        "id": "initial",
        "name": "Initial Outreach",
        "subject": "Quick idea for {company}",
        "body": (
            "Hi {first_name},\n\n"
            "I came across {company} and wanted to share a quick thought.\n\n"
            "Most customers today decide based on what they see online — reviews, your site, your Google listing. "
            "Small improvements there often turn into more calls.\n\n"
            "I help businesses like yours sharpen that. Worth a 10-min chat this week?\n\n"
            "Best,\n{sender_name}"
        ),
        "created_at": "",
        "updated_at": "",
    },
    {
        "id": "initial_with_review",
        "name": "Initial Outreach (with insights)",
        "subject": "I took a look at {company}'s online presence",
        "body": (
            "Hi {first_name},\n\n"
            "I spent a few minutes looking at {company} online and noticed a few opportunities.\n\n"
            "Happy to share what I found in a quick call — no pitch, just useful observations.\n\n"
            "Best,\n{sender_name}"
        ),
        "created_at": "",
        "updated_at": "",
    },
    {
        "id": "followup",
        "name": "Follow-up",
        "subject": "Following up — {company}",
        "body": (
            "Hi {first_name},\n\n"
            "Floating this back up in case it got buried.\n\n"
            "If getting more inbound is on your radar, I'd love to share a few specific ideas for {company}.\n\n"
            "Worth a quick chat?\n\n"
            "Best,\n{sender_name}"
        ),
        "created_at": "",
        "updated_at": "",
    },
    {
        "id": "final",
        "name": "Final Follow-up",
        "subject": "Last note — {company}",
        "body": (
            "Hi {first_name},\n\n"
            "Last note from me. If the timing isn't right, no worries — I'll stop reaching out.\n\n"
            "Wishing you continued success either way.\n\n"
            "Best,\n{sender_name}"
        ),
        "created_at": "",
        "updated_at": "",
    },
]


def _load() -> list[dict[str, Any]]:
    if not _TEMPLATES_FILE.exists():
        # Seed on first read
        _save_all(deepcopy(_SEED))
        return deepcopy(_SEED)
    try:
        data = json.loads(_TEMPLATES_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return deepcopy(_SEED)
    if not isinstance(data, list):
        return deepcopy(_SEED)
    return data


def _save_all(templates: list[dict[str, Any]]) -> None:
    _TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TEMPLATES_FILE.write_text(json.dumps(templates, indent=2))


def get_all() -> list[dict[str, Any]]:
    return _load()


def get_by_id(template_id: str) -> Optional[dict[str, Any]]:
    return next((t for t in _load() if t.get("id") == template_id), None)


def create(payload: dict[str, Any]) -> dict[str, Any]:
    new_id = uuid.uuid4().hex[:8]
    now = datetime.utcnow().isoformat() + "Z"
    template = {
        "id": new_id,
        "name": payload.get("name", "Untitled"),
        "subject": payload.get("subject", ""),
        "body": payload.get("body", ""),
        "created_at": now,
        "updated_at": now,
    }
    templates = _load()
    templates.append(template)
    _save_all(templates)
    return template


def update(template_id: str, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    templates = _load()
    found = None
    for t in templates:
        if t.get("id") == template_id:
            t["name"] = payload.get("name", t["name"])
            t["subject"] = payload.get("subject", t["subject"])
            t["body"] = payload.get("body", t["body"])
            t["updated_at"] = datetime.utcnow().isoformat() + "Z"
            found = t
            break
    if found:
        _save_all(templates)
    return found


def delete(template_id: str) -> bool:
    templates = _load()
    before = len(templates)
    templates = [t for t in templates if t.get("id") != template_id]
    if len(templates) == before:
        return False
    _save_all(templates)
    return True
