# Pulse — Outreach + Templates + Settings + Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Commit message rule (project-wide):** NEVER add `Co-Authored-By: Claude`, "Generated with Claude Code", or any AI/assistant attribution to any commit message. Each task spec gives the exact message — use it verbatim.

**Goal:** Make the last three placeholder pages real — **Outreach** (pick an opportunity → pick a template → preview with variables filled → send via SMTP), **Templates** (full CRUD with `{variable}` substitution), **Settings** (real round-trip: load existing values, save updates, persist to JSON file, mask SMTP password) — plus **delete the deprecated `/cold/*` and `/direct/*` route tree** so the codebase is unified on Pulse only. After this plan, every sidebar link works, every setting persists, and the user can run an end-to-end loop: scrape → triage in Inbox → drag through Pipeline → write template → send email → tracked stage update.

**Architecture:**
- **New backend:** `backend/services/settings_store.py` (JSON-backed settings with masked secrets), `backend/services/templates_store.py` (JSON-backed templates with built-in defaults), `backend/routers/settings.py`, `backend/routers/templates.py`, `backend/routers/outreach.py`. The outreach router reuses `smtplib` via the new settings (no env-var reads).
- **Modified backend:** `backend/app.py` (register 3 new routers), `backend/routers/shared.py` (existing `EMAIL_TEMPLATES` hardcoded list moves to be the seed data for `templates_store` — old `/api/email/*` endpoints stay for one release).
- **New frontend:** Real `SettingsPage`, `TemplatesPage`, `OutreachPage`, plus a shared `TemplateEditor` modal.
- **Cleanup:** Delete `frontend/src/pages/cold/**`, `frontend/src/pages/direct/**`, `frontend/src/pages/Settings.tsx` (old), `frontend/src/layouts/AppLayout.tsx`, and the old `components/{TopNav,Sidebar,PageHeader,EmptyState,StatCard,StatusBadge,Button,BatchEmailDialog}.tsx`. Remove their imports and routes from `App.tsx`. Old `/api/email/*` endpoints stay (the outreach UI uses the new `/api/outreach/send` instead).

**Tech Stack:** React 18, react-query 5, Tailwind v4, FastAPI, Python 3.12, pytest, smtplib (stdlib). No new dependencies.

---

## Scope decision

This is the **final plan in the original 5**. After this:

| # | Plan | Status |
|---|---|---|
| 1 | Foundation & Inbox | ✅ |
| 2 | Hub & Live PulseBar | ✅ |
| 3 | Pipeline Kanban | ✅ |
| 4 | Sources & scheduler | ✅ |
| **5 (this)** | **Outreach + Templates + Settings + cleanup** | About to ship |
| 6 | Tanit Jobs scraper (Cloudflare-protected, Scrapling stealth) | Pending — separate plan |
| 7 | Supabase migration | Pending — separate plan |

**Deferred from prototype:** the Outreach prototype mockup hasn't been created, so this plan ships a clean minimal Outreach UX (pick opportunity → pick template → preview → send). Multi-touch sequences, scheduled-send queue, and reply tracking are explicitly NOT in v1 — those are post-v1 polish.

---

## File structure (this plan)

**New backend files:**
- `backend/services/settings_store.py` — read/write `output/settings.json`; mask SMTP password on read
- `backend/services/templates_store.py` — read/write `output/email_templates.json`; seed with the existing 4 hardcoded templates on first load
- `backend/routers/settings.py` — `GET /api/settings`, `PUT /api/settings`
- `backend/routers/templates.py` — `GET /api/templates`, `GET /api/templates/{id}`, `POST /api/templates`, `PUT /api/templates/{id}`, `DELETE /api/templates/{id}`
- `backend/routers/outreach.py` — `POST /api/outreach/send` (uses settings + templates services)

**Modified backend files:**
- `backend/app.py` — register `settings`, `templates`, `outreach` routers
- (Plan 5 explicitly leaves `backend/routers/shared.py` untouched. Old `/api/email/*` endpoints continue to work for any external integration but aren't used by the new UI.)

**New backend tests:**
- `tests/backend/test_settings_store.py`
- `tests/backend/test_settings_router.py`
- `tests/backend/test_templates_store.py`
- `tests/backend/test_templates_router.py`

**New frontend files:**
- `frontend/src/types/settings.ts` — `Settings`, `SettingsProfile`, `SettingsEmail`, `SettingsScraping`
- `frontend/src/types/template.ts` — `EmailTemplate`
- `frontend/src/api/settings.ts` — `useSettings`, `useUpdateSettings`
- `frontend/src/api/templates.ts` — `useTemplates`, `useCreateTemplate`, `useUpdateTemplate`, `useDeleteTemplate`
- `frontend/src/api/outreach.ts` — `useSendOutreach`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/templates/TemplatesPage.tsx`
- `frontend/src/pages/templates/TemplateEditor.tsx` (modal)
- `frontend/src/pages/outreach/OutreachPage.tsx`

**Modified frontend files:**
- `frontend/src/App.tsx` — replace 3 placeholder routes (`/settings`, `/templates`, `/outreach`); remove all `/cold/*` and `/direct/*` routes; remove the `<Route element={<AppLayout />}>` wrapper

**Files DELETED in cleanup:**
- `frontend/src/pages/cold/` (whole directory: Dashboard.tsx, Leads.tsx, NewRun.tsx, Runs.tsx, Email.tsx)
- `frontend/src/pages/direct/` (whole directory: Dashboard.tsx, Leads.tsx, LeadDetail.tsx, NewScan.tsx, Scans.tsx, SavedSearches.tsx)
- `frontend/src/pages/Settings.tsx` (old — replaced by `pages/settings/SettingsPage.tsx`)
- `frontend/src/layouts/AppLayout.tsx`
- `frontend/src/components/{TopNav,Sidebar,PageHeader,EmptyState,StatCard,StatusBadge,Button,BatchEmailDialog}.tsx` (old versions — `components/shell/` and `design/primitives/` are the new ones; do NOT touch those)

**Files NOT touched (preserved):**
- All Plan 1-4 code: opportunities, hub, pipeline, sources routers + their tests
- `frontend/src/components/shell/**` (new shell)
- `frontend/src/design/primitives/**`
- `frontend/src/pages/{inbox,hub,pipeline,sources,PlaceholderPage}.tsx` (Plan 1-4 pages — PlaceholderPage stays unused but as a future-proofing component)
- `backend/routers/shared.py` (old `/api/email/*` and `/api/stats*` stay alive)

---

## Conventions

- **Variable substitution syntax:** single brace, e.g. `{name}` (matches existing `EMAIL_TEMPLATES` convention in `shared.py`). NOT mustache `{{name}}`.
- **Standard variables auto-filled from an `Opportunity`:**
  - `{name}` — `contact_name` if present, else `company_name`, else `(no name)`
  - `{first_name}` — first whitespace-separated token of `{name}`
  - `{company}` — `company_name`
  - `{title}` — opportunity title
  - `{value}` — formatted dollar amount (e.g. `"$2,500"`)
  - `{source}` — source slug (e.g. `"reddit"`)
  - `{location}` — `location` field
  - `{sender_name}` — `settings.profile.name` (falls back to `"Lead Prospector"`)
- **Settings JSON structure** (file: `output/settings.json`):
  ```json
  {
    "profile": {
      "name": "Amine",
      "skills": ["react", "typescript"],
      "services": ["landing pages"],
      "hourly_rate": 75,
      "min_budget": 500
    },
    "email": {
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_user": "amine@example.com",
      "smtp_password": "secret",
      "sender_name": "Amine",
      "from_email": "amine@example.com"
    },
    "scraping": {
      "proxy_url": null,
      "max_concurrent": 5
    }
  }
  ```
- **Password masking:** `GET /api/settings` returns `email.smtp_password` as the literal string `"••••••••"` if a password is set, else `""`. `PUT /api/settings` only updates the password if the incoming value is non-empty AND not `"••••••••"`.
- **Template ID:** 8-char hex generated server-side. User can't edit ID.
- **Template seed data:** when `email_templates.json` doesn't exist, the store seeds itself with the 4 templates currently hardcoded in `shared.py` (`initial`, `initial_with_review`, `followup`, `final`).
- **Stage update on send:** when outreach send succeeds, the lead's stage advances to `contacted` (only if currently `new`, `researching`, or empty — don't downgrade later stages). Uses `storage.update_lead` with the correct section (`cold` for cold opportunities, `direct` for direct).

---

## Pre-flight

- [ ] **Step 0.1: Verify Plan 4 is committed and the branch is clean**

```bash
cd C:\Users\JIMMY\lead_prospector
git status
git log --oneline pulse-foundation -5
```
Expected: working tree clean, latest commit is `652cd38 fix(layout): drop max-w-[1400px] mx-auto on Hub + Sources` or later.

- [ ] **Step 0.2: Backend + frontend running**

```powershell
.venv\Scripts\python.exe run_server.py --no-reload
cd frontend; npm run dev
```

---

## Task 1: Backend — `SettingsStore` service (TDD)

**Files:**
- Create: `backend/services/settings_store.py`
- Test: `tests/backend/test_settings_store.py`

- [ ] **Step 1.1: Write failing test**

Create `tests/backend/test_settings_store.py`:

```python
"""Tests for backend.services.settings_store."""
from __future__ import annotations

import json

import pytest

from backend.services import settings_store


@pytest.fixture
def tmp_settings_file(tmp_path, monkeypatch):
    p = tmp_path / "settings.json"
    monkeypatch.setattr(settings_store, "_SETTINGS_FILE", p)
    return p


def test_get_returns_defaults_when_no_file(tmp_settings_file):
    s = settings_store.get_masked()
    assert s["profile"]["name"] == ""
    assert s["email"]["smtp_host"] == "smtp.gmail.com"
    assert s["email"]["smtp_port"] == 587
    assert s["email"]["smtp_password"] == ""  # No password set → empty
    assert s["scraping"]["max_concurrent"] == 5


def test_save_persists_and_get_masks_password(tmp_settings_file):
    settings_store.save({
        "profile": {"name": "Amine", "skills": ["react"], "services": [], "hourly_rate": 75, "min_budget": 0},
        "email": {"smtp_host": "smtp.gmail.com", "smtp_port": 587, "smtp_user": "a@b.com",
                  "smtp_password": "secret123", "sender_name": "Amine", "from_email": "a@b.com"},
        "scraping": {"proxy_url": None, "max_concurrent": 5},
    })
    raw = json.loads(tmp_settings_file.read_text())
    assert raw["email"]["smtp_password"] == "secret123"  # Stored unmasked

    masked = settings_store.get_masked()
    assert masked["profile"]["name"] == "Amine"
    assert masked["email"]["smtp_password"] == "••••••••"  # Masked on read


def test_save_preserves_password_when_incoming_is_mask_placeholder(tmp_settings_file):
    """PUT with the mask placeholder must NOT overwrite the real password."""
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "real_secret", "sender_name": "x", "from_email": "x"},
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "••••••••", "sender_name": "x", "from_email": "x"},  # Mask placeholder
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    raw = json.loads(tmp_settings_file.read_text())
    assert raw["email"]["smtp_password"] == "real_secret"  # Preserved


def test_save_preserves_password_when_incoming_is_empty(tmp_settings_file):
    """PUT with empty password must NOT overwrite the real password."""
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "real_secret", "sender_name": "x", "from_email": "x"},
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "", "sender_name": "x", "from_email": "x"},  # Empty
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    raw = json.loads(tmp_settings_file.read_text())
    assert raw["email"]["smtp_password"] == "real_secret"


def test_get_raw_returns_actual_password(tmp_settings_file):
    """get_raw is for backend use only (e.g., outreach send) — returns real password."""
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "real", "sender_name": "x", "from_email": "x"},
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    raw = settings_store.get_raw()
    assert raw["email"]["smtp_password"] == "real"


def test_corrupted_file_returns_defaults(tmp_settings_file):
    tmp_settings_file.write_text("{not valid json")
    s = settings_store.get_masked()
    assert s["profile"]["name"] == ""
    assert s["email"]["smtp_host"] == "smtp.gmail.com"
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_settings_store.py -v
```
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 1.3: Implement**

Create `backend/services/settings_store.py`:

```python
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
```

- [ ] **Step 1.4: Run tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_settings_store.py -v
```
Expected: 6 passed.

- [ ] **Step 1.5: Commit**

```bash
git add backend/services/settings_store.py tests/backend/test_settings_store.py
git commit -m "feat(services): add SettingsStore with masked-password round-trip"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 2: Backend — `/api/settings` router (TDD)

**Files:**
- Create: `backend/routers/settings.py`
- Modify: `backend/app.py`
- Test: `tests/backend/test_settings_router.py`

- [ ] **Step 2.1: Write failing test**

Create `tests/backend/test_settings_router.py`:

```python
"""Tests for backend.routers.settings."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_settings_returns_full_shape(client):
    res = client.get("/api/settings")
    assert res.status_code == 200
    body = res.json()
    for top in ("profile", "email", "scraping"):
        assert top in body
    for k in ("name", "skills", "services", "hourly_rate", "min_budget"):
        assert k in body["profile"]
    for k in ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "sender_name", "from_email"):
        assert k in body["email"]


def test_put_settings_round_trip(client, tmp_path, monkeypatch):
    """Save profile fields, get back what we saved (except password is masked)."""
    from backend.services import settings_store
    monkeypatch.setattr(settings_store, "_SETTINGS_FILE", tmp_path / "settings.json")

    payload = {
        "profile": {"name": "Amine", "skills": ["react", "ts"], "services": ["landing"],
                    "hourly_rate": 100, "min_budget": 500},
        "email": {"smtp_host": "smtp.x.com", "smtp_port": 465, "smtp_user": "u",
                  "smtp_password": "newpass", "sender_name": "A", "from_email": "u@x.com"},
        "scraping": {"proxy_url": "http://proxy", "max_concurrent": 3},
    }
    res = client.put("/api/settings", json=payload)
    assert res.status_code == 200

    res = client.get("/api/settings")
    body = res.json()
    assert body["profile"]["name"] == "Amine"
    assert body["profile"]["hourly_rate"] == 100
    assert body["email"]["smtp_user"] == "u"
    assert body["email"]["smtp_password"] == "••••••••"  # Masked
    assert body["scraping"]["proxy_url"] == "http://proxy"
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_settings_router.py -v
```
Expected: FAIL with 404 on every endpoint.

- [ ] **Step 2.3: Implement**

Create `backend/routers/settings.py`:

```python
"""Settings GET + PUT endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.services import settings_store

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings() -> dict[str, Any]:
    return settings_store.get_masked()


@router.put("")
async def update_settings(body: dict) -> dict[str, Any]:
    settings_store.save(body)
    return settings_store.get_masked()
```

- [ ] **Step 2.4: Register in `backend/app.py`**

Find:
```python
from backend.routers import cold_outreach, direct_leads, hub, opportunities, shared, sources
```
Replace with:
```python
from backend.routers import cold_outreach, direct_leads, hub, opportunities, settings as settings_router, shared, sources
```

Find:
```python
app.include_router(sources.router)
```
Add after:
```python
app.include_router(settings_router.router)
```

(Note the alias `settings_router` to avoid collision with the stdlib `settings` symbol if ever imported.)

- [ ] **Step 2.5: Run tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_settings_router.py -v
```
Expected: 2 passed.

- [ ] **Step 2.6: Commit**

```bash
git add backend/routers/settings.py backend/app.py tests/backend/test_settings_router.py
git commit -m "feat(api): add /api/settings GET + PUT with masked-password round-trip"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 3: Backend — `TemplatesStore` service (TDD)

**Files:**
- Create: `backend/services/templates_store.py`
- Test: `tests/backend/test_templates_store.py`

- [ ] **Step 3.1: Write failing test**

Create `tests/backend/test_templates_store.py`:

```python
"""Tests for backend.services.templates_store."""
from __future__ import annotations

import json

import pytest

from backend.services import templates_store


@pytest.fixture
def tmp_templates_file(tmp_path, monkeypatch):
    p = tmp_path / "email_templates.json"
    monkeypatch.setattr(templates_store, "_TEMPLATES_FILE", p)
    return p


def test_get_all_seeds_defaults_on_first_call(tmp_templates_file):
    """First call should return the 4 hardcoded seed templates."""
    templates = templates_store.get_all()
    assert len(templates) == 4
    ids = {t["id"] for t in templates}
    assert {"initial", "initial_with_review", "followup", "final"}.issubset(ids)


def test_create_template_assigns_id_and_persists(tmp_templates_file):
    t = templates_store.create({"name": "My Template", "subject": "Hi {name}", "body": "Hey {first_name}"})
    assert "id" in t
    assert len(t["id"]) == 8
    assert t["name"] == "My Template"
    # Persists across "process restart"
    all_t = templates_store.get_all()
    assert any(x["id"] == t["id"] for x in all_t)


def test_update_template(tmp_templates_file):
    t = templates_store.create({"name": "Orig", "subject": "Orig subj", "body": "Orig body"})
    updated = templates_store.update(t["id"], {"name": "New", "subject": "New subj", "body": "New body"})
    assert updated["name"] == "New"
    assert updated["subject"] == "New subj"
    fetched = templates_store.get_by_id(t["id"])
    assert fetched["name"] == "New"


def test_update_unknown_returns_none(tmp_templates_file):
    assert templates_store.update("does_not_exist", {"name": "X", "subject": "X", "body": "X"}) is None


def test_delete_template(tmp_templates_file):
    t = templates_store.create({"name": "X", "subject": "X", "body": "X"})
    assert templates_store.delete(t["id"]) is True
    assert templates_store.get_by_id(t["id"]) is None
    # Idempotent: deleting again returns False
    assert templates_store.delete(t["id"]) is False


def test_get_by_id_returns_seed_templates(tmp_templates_file):
    t = templates_store.get_by_id("initial")
    assert t is not None
    assert t["name"] == "Initial Outreach"
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_templates_store.py -v
```
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3.3: Implement**

Create `backend/services/templates_store.py`:

```python
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
```

- [ ] **Step 3.4: Run tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_templates_store.py -v
```
Expected: 6 passed.

- [ ] **Step 3.5: Commit**

```bash
git add backend/services/templates_store.py tests/backend/test_templates_store.py
git commit -m "feat(services): add TemplatesStore (CRUD + seeded defaults)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 4: Backend — `/api/templates` router (TDD)

**Files:**
- Create: `backend/routers/templates.py`
- Modify: `backend/app.py`
- Test: `tests/backend/test_templates_router.py`

- [ ] **Step 4.1: Write failing test**

Create `tests/backend/test_templates_router.py`:

```python
"""Tests for backend.routers.templates."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_templates(client):
    res = client.get("/api/templates")
    assert res.status_code == 200
    body = res.json()
    assert "templates" in body
    assert isinstance(body["templates"], list)
    assert len(body["templates"]) >= 4  # Seeds


def test_get_one_template(client):
    res = client.get("/api/templates/initial")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "initial"
    assert body["name"] == "Initial Outreach"


def test_get_unknown_404(client):
    res = client.get("/api/templates/nonexistent_xxxxx")
    assert res.status_code == 404


def test_create_template(client):
    payload = {"name": "Test create", "subject": "S", "body": "B"}
    res = client.post("/api/templates", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Test create"
    new_id = body["id"]
    # Cleanup
    client.delete(f"/api/templates/{new_id}")


def test_update_template(client):
    created = client.post("/api/templates", json={"name": "Orig", "subject": "S", "body": "B"}).json()
    res = client.put(f"/api/templates/{created['id']}", json={"name": "Updated", "subject": "S2", "body": "B2"})
    assert res.status_code == 200
    assert res.json()["name"] == "Updated"
    # Cleanup
    client.delete(f"/api/templates/{created['id']}")


def test_update_unknown_404(client):
    res = client.put("/api/templates/nonexistent", json={"name": "X", "subject": "X", "body": "X"})
    assert res.status_code == 404


def test_delete_template(client):
    created = client.post("/api/templates", json={"name": "ToDelete", "subject": "S", "body": "B"}).json()
    res = client.delete(f"/api/templates/{created['id']}")
    assert res.status_code == 200
    res = client.get(f"/api/templates/{created['id']}")
    assert res.status_code == 404
```

- [ ] **Step 4.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_templates_router.py -v
```
Expected: FAIL — 404 on every endpoint.

- [ ] **Step 4.3: Implement**

Create `backend/routers/templates.py`:

```python
"""Email templates CRUD router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.services import templates_store

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def list_templates() -> dict[str, Any]:
    return {"templates": templates_store.get_all()}


@router.get("/{template_id}")
async def get_one(template_id: str) -> dict[str, Any]:
    t = templates_store.get_by_id(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.post("")
async def create_template(body: dict) -> dict[str, Any]:
    return templates_store.create(body)


@router.put("/{template_id}")
async def update_template(template_id: str, body: dict) -> dict[str, Any]:
    t = templates_store.update(template_id, body)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.delete("/{template_id}")
async def delete_template(template_id: str) -> dict[str, Any]:
    if not templates_store.delete(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}
```

- [ ] **Step 4.4: Register in `backend/app.py`**

Find the import line:
```python
from backend.routers import cold_outreach, direct_leads, hub, opportunities, settings as settings_router, shared, sources
```
Replace with:
```python
from backend.routers import cold_outreach, direct_leads, hub, opportunities, settings as settings_router, shared, sources, templates
```

Find:
```python
app.include_router(settings_router.router)
```
Add after:
```python
app.include_router(templates.router)
```

- [ ] **Step 4.5: Run tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_templates_router.py -v
```
Expected: 7 passed.

- [ ] **Step 4.6: Commit**

```bash
git add backend/routers/templates.py backend/app.py tests/backend/test_templates_router.py
git commit -m "feat(api): add /api/templates CRUD endpoints"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 5: Backend — `/api/outreach/send` endpoint

**Why:** Send a single email by combining an opportunity, a template, and the user's SMTP settings. On success, advance the opportunity stage to `contacted` (only if currently `new` or `researching`). No TDD here — this endpoint is a thin wrapper around `smtplib` and the already-tested stores; integration testing would require a live SMTP server.

**Files:**
- Create: `backend/routers/outreach.py`
- Modify: `backend/app.py`

- [ ] **Step 5.1: Implement**

Create `backend/routers/outreach.py`:

```python
"""Outreach: send a single email using user settings + a template."""
from __future__ import annotations

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import settings_store, templates_store
from src.core.storage import update_lead

router = APIRouter(prefix="/api/outreach", tags=["outreach"])

# Stages we WILL advance to "contacted" on send. (Don't downgrade later stages.)
_ADVANCEABLE_STAGES = {"new", "researching", ""}


class OutreachSendRequest(BaseModel):
    opportunity_id: str
    opportunity_type: str  # "direct" or "cold"
    source_file: str  # Excel filename — the storage layer uses this to find/write
    raw_lead_id: str  # Original Lead_ID in the Excel row
    current_stage: str  # Current stage of the opp (used to decide whether to advance)
    template_id: Optional[str] = None
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None
    to_email: str
    to_name: str
    variables: dict[str, str] = {}


class OutreachSendResponse(BaseModel):
    success: bool
    message: str
    sent_at: Optional[datetime] = None
    stage_advanced: bool = False


def _substitute(text: str, variables: dict[str, str]) -> str:
    out = text
    for key, value in variables.items():
        out = out.replace("{" + key + "}", str(value))
    return out


@router.post("/send", response_model=OutreachSendResponse)
async def send(req: OutreachSendRequest) -> OutreachSendResponse:
    # 1. Get SMTP settings (raw — we need the real password)
    settings = settings_store.get_raw()
    email_cfg = settings.get("email", {})
    smtp_host = email_cfg.get("smtp_host") or "smtp.gmail.com"
    smtp_port = int(email_cfg.get("smtp_port") or 587)
    smtp_user = email_cfg.get("smtp_user") or ""
    smtp_password = email_cfg.get("smtp_password") or ""
    sender_name = email_cfg.get("sender_name") or "Lead Prospector"
    from_email = email_cfg.get("from_email") or smtp_user

    if not smtp_user or not smtp_password:
        return OutreachSendResponse(
            success=False,
            message="SMTP not configured — open Settings to set host, user, and password.",
        )

    # 2. Resolve subject + body (custom > template)
    if req.custom_subject is not None and req.custom_body is not None:
        subject = req.custom_subject
        body_text = req.custom_body
    else:
        if not req.template_id:
            raise HTTPException(status_code=400, detail="template_id or custom_subject+custom_body required")
        template = templates_store.get_by_id(req.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        subject = req.custom_subject or template["subject"]
        body_text = req.custom_body or template["body"]

    # 3. Substitute variables (caller-supplied + sender_name)
    variables = {"sender_name": sender_name, **req.variables}
    subject = _substitute(subject, variables)
    body_text = _substitute(body_text, variables)

    # 4. Send via SMTP
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{from_email}>"
        msg["To"] = f"{req.to_name} <{req.to_email}>"
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return OutreachSendResponse(success=False, message="SMTP authentication failed. Check your credentials.")
    except smtplib.SMTPException as e:
        return OutreachSendResponse(success=False, message=f"SMTP error: {e}")
    except Exception as e:
        return OutreachSendResponse(success=False, message=f"Send failed: {e}")

    # 5. Advance stage to "contacted" if not already past it
    advanced = False
    if (req.current_stage or "").lower() in _ADVANCEABLE_STAGES:
        section = "cold" if req.opportunity_type == "cold" else "direct"
        try:
            update_lead(
                req.source_file,
                req.raw_lead_id,
                {
                    "Outreach_Status": "contacted",
                    "Last_Contacted": datetime.now().strftime("%Y-%m-%d %H:%M"),
                },
                section,
            )
            advanced = True
        except Exception as e:
            # Send succeeded; stage update is best-effort.
            print(f"[OUTREACH] Stage advance failed: {e}", flush=True)

    return OutreachSendResponse(
        success=True,
        message=f"Email sent to {req.to_email}",
        sent_at=datetime.utcnow(),
        stage_advanced=advanced,
    )
```

- [ ] **Step 5.2: Register in `backend/app.py`**

Find:
```python
from backend.routers import cold_outreach, direct_leads, hub, opportunities, settings as settings_router, shared, sources, templates
```
Replace with:
```python
from backend.routers import cold_outreach, direct_leads, hub, opportunities, outreach, settings as settings_router, shared, sources, templates
```

Find:
```python
app.include_router(templates.router)
```
Add after:
```python
app.include_router(outreach.router)
```

- [ ] **Step 5.3: Manual smoke (no SMTP send — just confirm the endpoint loads)**

```bash
.venv/Scripts/python.exe -c "from backend.app import app; print([r.path for r in app.routes if hasattr(r,'path') and 'outreach' in r.path])"
```
Expected: `['/api/outreach/send']`

- [ ] **Step 5.4: Commit**

```bash
git add backend/routers/outreach.py backend/app.py
git commit -m "feat(api): add POST /api/outreach/send (templated email + stage advance)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 6: Frontend — TS types + react-query hooks

**Files:**
- Create: `frontend/src/types/settings.ts`
- Create: `frontend/src/types/template.ts`
- Create: `frontend/src/api/settings.ts`
- Create: `frontend/src/api/templates.ts`
- Create: `frontend/src/api/outreach.ts`

- [ ] **Step 6.1: Create `frontend/src/types/settings.ts`**

```ts
export interface SettingsProfile {
  name: string;
  skills: string[];
  services: string[];
  hourly_rate: number;
  min_budget: number;
}

export interface SettingsEmail {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  sender_name: string;
  from_email: string;
}

export interface SettingsScraping {
  proxy_url: string | null;
  max_concurrent: number;
}

export interface Settings {
  profile: SettingsProfile;
  email: SettingsEmail;
  scraping: SettingsScraping;
}
```

- [ ] **Step 6.2: Create `frontend/src/types/template.ts`**

```ts
export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  created_at?: string;
  updated_at?: string;
}

export interface TemplatesResponse {
  templates: EmailTemplate[];
}
```

- [ ] **Step 6.3: Create `frontend/src/api/settings.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { Settings } from "../types/settings";

export function useSettings() {
  return useQuery<Settings>({
    queryKey: ["settings"],
    queryFn: () => apiFetch("/settings"),
    staleTime: 60_000,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Settings) =>
      apiFetch<Settings>("/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}
```

- [ ] **Step 6.4: Create `frontend/src/api/templates.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { EmailTemplate, TemplatesResponse } from "../types/template";

export function useTemplates() {
  return useQuery<TemplatesResponse>({
    queryKey: ["templates", "list"],
    queryFn: () => apiFetch("/templates"),
    staleTime: 60_000,
  });
}

export function useCreateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<EmailTemplate>) =>
      apiFetch<EmailTemplate>("/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["templates"] }),
  });
}

export function useUpdateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<EmailTemplate> }) =>
      apiFetch<EmailTemplate>(`/templates/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["templates"] }),
  });
}

export function useDeleteTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/templates/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["templates"] }),
  });
}
```

- [ ] **Step 6.5: Create `frontend/src/api/outreach.ts`**

```ts
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "./client";

export interface OutreachSendBody {
  opportunity_id: string;
  opportunity_type: "direct" | "cold";
  source_file: string;
  raw_lead_id: string;
  current_stage: string;
  template_id?: string;
  custom_subject?: string;
  custom_body?: string;
  to_email: string;
  to_name: string;
  variables?: Record<string, string>;
}

export interface OutreachSendResponse {
  success: boolean;
  message: string;
  sent_at: string | null;
  stage_advanced: boolean;
}

export function useSendOutreach() {
  return useMutation<OutreachSendResponse, Error, OutreachSendBody>({
    mutationFn: (body) =>
      apiFetch("/outreach/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  });
}
```

- [ ] **Step 6.6: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/types/settings.ts frontend/src/types/template.ts frontend/src/api/settings.ts frontend/src/api/templates.ts frontend/src/api/outreach.ts
git commit -m "feat(api): add Settings + Templates + Outreach types and hooks"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 7: Frontend — `SettingsPage`

**File:** `frontend/src/pages/settings/SettingsPage.tsx`

The directory `frontend/src/pages/settings/` doesn't exist yet — create it.

- [ ] **Step 7.1: Create the file**

```tsx
import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { Button, Card } from "../../design/primitives";
import { useSettings, useUpdateSettings } from "../../api/settings";
import type { Settings } from "../../types/settings";

const EMPTY_SETTINGS: Settings = {
  profile: { name: "", skills: [], services: [], hourly_rate: 0, min_budget: 0 },
  email: { smtp_host: "smtp.gmail.com", smtp_port: 587, smtp_user: "", smtp_password: "", sender_name: "", from_email: "" },
  scraping: { proxy_url: null, max_concurrent: 5 },
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">{label}</label>
      {children}
    </div>
  );
}

const inputClass =
  "h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]";

export function SettingsPage() {
  const { data, isLoading } = useSettings();
  const update = useUpdateSettings();
  const [draft, setDraft] = useState<Settings>(EMPTY_SETTINGS);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  async function save() {
    await update.mutateAsync(draft);
    setSavedAt(Date.now());
    setTimeout(() => setSavedAt(null), 2500);
  }

  if (isLoading) {
    return (
      <div className="p-6 text-[12px] text-[var(--color-text-tertiary)]">Loading…</div>
    );
  }

  return (
    <div className="p-6 flex flex-col gap-4 w-full">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Settings</div>
          <div className="text-[11px] text-[var(--color-text-tertiary)]">
            Profile, email, and scraping configuration
          </div>
        </div>
        <div className="flex items-center gap-2">
          {savedAt && (
            <span className="text-[11px] text-[var(--color-accent)]">Saved</span>
          )}
          <Button variant="primary" size="md" onClick={save} disabled={update.isPending}>
            <Save className="w-3.5 h-3.5" />
            {update.isPending ? "Saving…" : "Save settings"}
          </Button>
        </div>
      </div>

      {/* Profile */}
      <Card className="p-5 flex flex-col gap-3">
        <h2 className="text-[13px] font-semibold text-[var(--color-text-primary)]">Profile</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Your name">
            <input className={inputClass} value={draft.profile.name}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, name: e.target.value } })} />
          </Field>
          <Field label="Hourly rate (USD)">
            <input type="number" className={inputClass} value={draft.profile.hourly_rate}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, hourly_rate: parseInt(e.target.value) || 0 } })} />
          </Field>
          <Field label="Skills (comma-separated)">
            <input className={inputClass} value={draft.profile.skills.join(", ")}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, skills: e.target.value.split(",").map(s => s.trim()).filter(Boolean) } })} />
          </Field>
          <Field label="Services (comma-separated)">
            <input className={inputClass} value={draft.profile.services.join(", ")}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, services: e.target.value.split(",").map(s => s.trim()).filter(Boolean) } })} />
          </Field>
          <Field label="Min budget (USD)">
            <input type="number" className={inputClass} value={draft.profile.min_budget}
              onChange={(e) => setDraft({ ...draft, profile: { ...draft.profile, min_budget: parseInt(e.target.value) || 0 } })} />
          </Field>
        </div>
      </Card>

      {/* Email */}
      <Card className="p-5 flex flex-col gap-3">
        <h2 className="text-[13px] font-semibold text-[var(--color-text-primary)]">Email (SMTP)</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="SMTP host">
            <input className={inputClass} value={draft.email.smtp_host}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, smtp_host: e.target.value } })} />
          </Field>
          <Field label="SMTP port">
            <input type="number" className={inputClass} value={draft.email.smtp_port}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, smtp_port: parseInt(e.target.value) || 587 } })} />
          </Field>
          <Field label="SMTP user / email">
            <input className={inputClass} value={draft.email.smtp_user}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, smtp_user: e.target.value } })} />
          </Field>
          <Field label="SMTP password">
            <input type="password" className={inputClass} value={draft.email.smtp_password}
              placeholder={draft.email.smtp_password === "••••••••" ? "(set — leave blank to keep)" : "(not set)"}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, smtp_password: e.target.value } })} />
          </Field>
          <Field label="Sender name">
            <input className={inputClass} value={draft.email.sender_name}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, sender_name: e.target.value } })} />
          </Field>
          <Field label="From email">
            <input className={inputClass} value={draft.email.from_email}
              onChange={(e) => setDraft({ ...draft, email: { ...draft.email, from_email: e.target.value } })} />
          </Field>
        </div>
        <p className="text-[11px] text-[var(--color-text-tertiary)]">
          Leave password blank to keep the existing one. Mask "••••••••" means a password is set.
        </p>
      </Card>

      {/* Scraping */}
      <Card className="p-5 flex flex-col gap-3">
        <h2 className="text-[13px] font-semibold text-[var(--color-text-primary)]">Scraping</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Proxy URL (optional)">
            <input className={inputClass} value={draft.scraping.proxy_url ?? ""}
              onChange={(e) => setDraft({ ...draft, scraping: { ...draft.scraping, proxy_url: e.target.value || null } })} />
          </Field>
          <Field label="Max concurrent scrapers">
            <input type="number" className={inputClass} value={draft.scraping.max_concurrent}
              onChange={(e) => setDraft({ ...draft, scraping: { ...draft.scraping, max_concurrent: parseInt(e.target.value) || 5 } })} />
          </Field>
        </div>
      </Card>
    </div>
  );
}
```

- [ ] **Step 7.2: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/settings/SettingsPage.tsx
git commit -m "feat(settings): add SettingsPage with full round-trip + masked password"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 8: Frontend — `TemplateEditor` modal + `TemplatesPage`

**Files:**
- Create: `frontend/src/pages/templates/TemplateEditor.tsx`
- Create: `frontend/src/pages/templates/TemplatesPage.tsx`

The directory `frontend/src/pages/templates/` doesn't exist yet — create it.

- [ ] **Step 8.1: Create `TemplateEditor.tsx`**

```tsx
import { useState } from "react";
import { X } from "lucide-react";
import { Button, Card } from "../../design/primitives";
import { useCreateTemplate, useUpdateTemplate } from "../../api/templates";
import type { EmailTemplate } from "../../types/template";

interface Props {
  initial?: EmailTemplate;
  onClose: () => void;
}

const inputClass =
  "h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] w-full";

export function TemplateEditor({ initial, onClose }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [subject, setSubject] = useState(initial?.subject ?? "");
  const [body, setBody] = useState(initial?.body ?? "");

  const create = useCreateTemplate();
  const update = useUpdateTemplate();
  const isPending = create.isPending || update.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !subject.trim() || !body.trim()) return;
    if (initial) {
      await update.mutateAsync({ id: initial.id, body: { name, subject, body } });
    } else {
      await create.mutateAsync({ name, subject, body });
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <Card
        className="w-[640px] max-h-[85vh] overflow-auto p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-[var(--color-text-primary)]">
            {initial ? "Edit template" : "New template"}
          </h2>
          <button type="button" onClick={onClose} className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Name</label>
            <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Subject</label>
            <input className={inputClass} value={subject} onChange={(e) => setSubject(e.target.value)} required
              placeholder="Quick idea for {company}" />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Body</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
              rows={14}
              className="px-2.5 py-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] font-mono resize-y"
              placeholder={"Hi {first_name},\n\n..."}
            />
            <p className="text-[10px] text-[var(--color-text-tertiary)]">
              Variables: <code>{"{name}"}</code> · <code>{"{first_name}"}</code> · <code>{"{company}"}</code> · <code>{"{title}"}</code> · <code>{"{value}"}</code> · <code>{"{source}"}</code> · <code>{"{location}"}</code> · <code>{"{sender_name}"}</code>
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={isPending}>
              {isPending ? "Saving…" : initial ? "Save changes" : "Create"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
```

- [ ] **Step 8.2: Create `TemplatesPage.tsx`**

```tsx
import { useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button, Card } from "../../design/primitives";
import { useTemplates, useDeleteTemplate } from "../../api/templates";
import { TemplateEditor } from "./TemplateEditor";
import type { EmailTemplate } from "../../types/template";

export function TemplatesPage() {
  const { data, isLoading } = useTemplates();
  const templates = data?.templates ?? [];
  const deleteMut = useDeleteTemplate();

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<EmailTemplate | null>(null);

  return (
    <div className="p-6 flex flex-col gap-4 w-full">
      <Card className="p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Templates</div>
            <div className="text-[11px] text-[var(--color-text-tertiary)]">
              {templates.length} {templates.length === 1 ? "template" : "templates"}
            </div>
          </div>
          <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
            <Plus className="w-3 h-3" /> New template
          </Button>
        </div>

        {isLoading && (
          <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
        )}

        <div className="flex flex-col">
          {templates.map((t) => (
            <div key={t.id} className="flex items-start gap-3 py-3 border-b border-[var(--color-border)] last:border-0">
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium text-[var(--color-text-primary)]">{t.name}</div>
                <div className="text-[12px] text-[var(--color-text-secondary)] truncate mt-0.5">{t.subject}</div>
                <div className="text-[11px] text-[var(--color-text-tertiary)] mt-1 whitespace-pre-line line-clamp-2">{t.body}</div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setEditing(t)}>
                <Pencil className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (confirm(`Delete template "${t.name}"?`)) deleteMut.mutate(t.id);
                }}
                disabled={deleteMut.isPending}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          ))}
        </div>
      </Card>

      {creating && <TemplateEditor onClose={() => setCreating(false)} />}
      {editing && <TemplateEditor initial={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}
```

- [ ] **Step 8.3: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/templates/TemplateEditor.tsx frontend/src/pages/templates/TemplatesPage.tsx
git commit -m "feat(templates): add TemplatesPage + TemplateEditor (full CRUD)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 9: Frontend — `OutreachPage`

**File:** `frontend/src/pages/outreach/OutreachPage.tsx`

The directory `frontend/src/pages/outreach/` doesn't exist yet — create it.

- [ ] **Step 9.1: Create the file**

```tsx
import { useMemo, useState } from "react";
import { Send } from "lucide-react";
import { Button, Card, MoneyValue, Pill } from "../../design/primitives";
import { useOpportunities } from "../../api/opportunities";
import { useTemplates } from "../../api/templates";
import { useSendOutreach } from "../../api/outreach";
import type { Opportunity } from "../../types/opportunity";
import type { EmailTemplate } from "../../types/template";

function buildVariables(opp: Opportunity): Record<string, string> {
  const fullName = (opp.contact_email && opp.contact_email.split("@")[0]) || opp.company_name || "";
  const cleanedName = (opp.company_name || fullName || "(no name)").trim();
  const firstName = cleanedName.split(/\s+/)[0] || cleanedName;
  return {
    name: cleanedName,
    first_name: firstName,
    company: opp.company_name || cleanedName,
    title: opp.title || "",
    value: opp.estimated_value_usd > 0 ? `$${opp.estimated_value_usd.toLocaleString("en-US")}` : "",
    source: opp.source || "",
    location: opp.location || "",
  };
}

function substitute(text: string, variables: Record<string, string>): string {
  let out = text;
  for (const [key, value] of Object.entries(variables)) {
    out = out.split("{" + key + "}").join(value);
  }
  return out;
}

export function OutreachPage() {
  const { data: oppData } = useOpportunities({ sort: "score", limit: 200 });
  const { data: tplData } = useTemplates();
  const opps = (oppData?.opportunities ?? []).filter((o) => o.contact_email);
  const templates = tplData?.templates ?? [];

  const [selectedOppId, setSelectedOppId] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [customSubject, setCustomSubject] = useState<string | null>(null);
  const [customBody, setCustomBody] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const send = useSendOutreach();
  const [result, setResult] = useState<string | null>(null);

  const opp = opps.find((o) => o.id === selectedOppId) ?? null;
  const template = templates.find((t) => t.id === selectedTemplateId) ?? null;

  const variables = useMemo(() => (opp ? buildVariables(opp) : {}), [opp]);

  const baseSubject = template?.subject ?? "";
  const baseBody = template?.body ?? "";
  const previewSubject = substitute(customSubject ?? baseSubject, variables);
  const previewBody = substitute(customBody ?? baseBody, variables);

  function reset() {
    setCustomSubject(null);
    setCustomBody(null);
    setEditing(false);
  }

  async function handleSend() {
    if (!opp || !template) return;
    setResult(null);
    const res = await send.mutateAsync({
      opportunity_id: opp.id,
      opportunity_type: opp.type,
      source_file: opp.source_file,
      raw_lead_id: opp.raw_lead_id,
      current_stage: opp.stage,
      template_id: template.id,
      custom_subject: customSubject ?? undefined,
      custom_body: customBody ?? undefined,
      to_email: opp.contact_email,
      to_name: variables.name,
      variables,
    });
    setResult(res.message);
    if (res.success) reset();
  }

  return (
    <div className="p-6 flex flex-col gap-4 w-full h-full">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Outreach</div>
          <div className="text-[11px] text-[var(--color-text-tertiary)]">
            {opps.length} opportunities have an email · pick one and a template to send
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4 flex-1 min-h-0">
        {/* Opportunity picker */}
        <Card className="p-3 flex flex-col gap-2 overflow-hidden">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium px-1">
            Opportunities with email
          </div>
          <div className="flex-1 overflow-auto flex flex-col">
            {opps.length === 0 && (
              <div className="text-[12px] text-[var(--color-text-tertiary)] p-4 text-center">
                No opportunities have a contact email yet. Run a scan with email extraction first.
              </div>
            )}
            {opps.map((o) => (
              <button
                key={o.id}
                type="button"
                onClick={() => { setSelectedOppId(o.id); reset(); }}
                className={
                  "px-2 py-2 text-left rounded-[var(--radius-sm)] flex flex-col gap-0.5 transition-colors " +
                  (o.id === selectedOppId ? "bg-[var(--color-surface-raised)]" : "hover:bg-[var(--color-surface-raised)]")
                }
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-[12px] font-medium text-[var(--color-text-primary)] truncate flex-1">
                    {o.title || o.company_name || "(no title)"}
                  </span>
                  <MoneyValue usd={o.estimated_value_usd} size="sm" tone="accent" />
                </div>
                <div className="text-[10px] text-[var(--color-text-tertiary)] flex items-center gap-1.5">
                  <Pill tone="neutral">{o.source}</Pill>
                  <span className="truncate">{o.contact_email}</span>
                </div>
              </button>
            ))}
          </div>
        </Card>

        {/* Composer */}
        <Card className="p-5 flex flex-col gap-3 overflow-auto">
          {!opp && (
            <div className="text-[12px] text-[var(--color-text-tertiary)] p-8 text-center">
              Select an opportunity from the left to compose.
            </div>
          )}

          {opp && (
            <>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[14px] font-semibold text-[var(--color-text-primary)]">{opp.title}</div>
                  <div className="text-[11px] text-[var(--color-text-tertiary)] mt-0.5">
                    To: {variables.name} &lt;{opp.contact_email}&gt;
                  </div>
                </div>
                <MoneyValue usd={opp.estimated_value_usd} size="lg" tone="accent" />
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Template</span>
                <select
                  value={selectedTemplateId ?? ""}
                  onChange={(e) => { setSelectedTemplateId(e.target.value || null); reset(); }}
                  className="h-8 px-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[12px] text-[var(--color-text-primary)] flex-1"
                >
                  <option value="">— choose a template —</option>
                  {templates.map((t) => (<option key={t.id} value={t.id}>{t.name}</option>))}
                </select>
                {template && (
                  <Button variant="ghost" size="sm" onClick={() => setEditing(!editing)}>
                    {editing ? "Use preview" : "Edit"}
                  </Button>
                )}
              </div>

              {template && !editing && (
                <div className="flex flex-col gap-3 bg-[var(--color-bg)] p-4 rounded-[var(--radius-md)] border border-[var(--color-border)]">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1">Subject</div>
                    <div className="text-[13px] text-[var(--color-text-primary)]">{previewSubject}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1">Body</div>
                    <pre className="text-[12px] text-[var(--color-text-primary)] whitespace-pre-wrap font-sans leading-relaxed">{previewBody}</pre>
                  </div>
                </div>
              )}

              {template && editing && (
                <div className="flex flex-col gap-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Subject (override)</label>
                    <input
                      value={customSubject ?? baseSubject}
                      onChange={(e) => setCustomSubject(e.target.value)}
                      className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Body (override)</label>
                    <textarea
                      value={customBody ?? baseBody}
                      onChange={(e) => setCustomBody(e.target.value)}
                      rows={14}
                      className="px-2.5 py-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[12px] text-[var(--color-text-primary)] font-mono resize-y"
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 pt-2">
                <Button variant="primary" onClick={handleSend} disabled={!template || send.isPending}>
                  <Send className="w-3.5 h-3.5" />
                  {send.isPending ? "Sending…" : "Send email"}
                </Button>
                {result && (
                  <span className={"text-[12px] " + (result.toLowerCase().includes("sent") ? "text-[var(--color-accent)]" : "text-[var(--color-hot)]")}>
                    {result}
                  </span>
                )}
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 9.2: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/outreach/OutreachPage.tsx
git commit -m "feat(outreach): add OutreachPage (pick opp + template, preview, send)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 10: Wire 3 routes + delete deprecated `/cold/*` and `/direct/*`

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: many (see list below)

- [ ] **Step 10.1: Read current `App.tsx`**

```bash
cat frontend/src/App.tsx
```

- [ ] **Step 10.2: Update imports — add new pages, remove old**

In `frontend/src/App.tsx`:

REMOVE these old imports (they reference files we're about to delete):
- Any import of `AppLayout` (from `./layouts/AppLayout`)
- Any imports from `./pages/cold/*`
- Any imports from `./pages/direct/*`
- The import of the OLD `./pages/Settings`

ADD these new imports (place near the existing `HubPage` / `PipelinePage` / `SourcesPage` import block):

```tsx
import { SettingsPage } from "./pages/settings/SettingsPage";
import { TemplatesPage } from "./pages/templates/TemplatesPage";
import { OutreachPage } from "./pages/outreach/OutreachPage";
```

- [ ] **Step 10.3: Replace the 3 placeholder routes**

In the `<Route element={<AppShell />}>` block, find each of these and replace:

```tsx
<Route path="/outreach" element={<PlaceholderPage title="Outreach" shipping="Plan 5 — Outreach revamp" />} />
```
→
```tsx
<Route path="/outreach" element={<OutreachPage />} />
```

```tsx
<Route path="/templates" element={<PlaceholderPage title="Templates" shipping="Plan 5 — Templates" />} />
```
→
```tsx
<Route path="/templates" element={<TemplatesPage />} />
```

```tsx
<Route path="/settings" element={<PlaceholderPage title="Settings" shipping="Plan 5 — Settings round-trip" />} />
```
→
```tsx
<Route path="/settings" element={<SettingsPage />} />
```

- [ ] **Step 10.4: Delete the entire `<Route element={<AppLayout />}>` block**

Find and DELETE the entire JSX block that begins with:
```tsx
<Route element={<AppLayout />}>
```
…through its closing `</Route>`. This block contains all the old `/cold/*` and `/direct/*` routes that are being deprecated. Make sure no other JSX is inside it that you need.

- [ ] **Step 10.5: Verify build (will fail if any deleted file is still imported elsewhere)**

```powershell
cd frontend && npm run build
cd ..
```

If the build fails with "Could not resolve" errors, those are dangling imports — fix them by removing the offending import line. If the build complains about a SHARED component (e.g., something in `components/shell/` or `design/primitives/`), STOP — do NOT delete those. Only delete the OLD components (PageHeader, EmptyState, StatCard, StatusBadge, the OLD Sidebar, the OLD TopNav, the OLD Button, BatchEmailDialog, AppLayout).

- [ ] **Step 10.6: Delete the deprecated files**

```bash
# Old pages
rm -rf frontend/src/pages/cold
rm -rf frontend/src/pages/direct
rm -f frontend/src/pages/Settings.tsx

# Old layout + old components
rm -f frontend/src/layouts/AppLayout.tsx
rm -f frontend/src/components/TopNav.tsx
rm -f frontend/src/components/Sidebar.tsx
rm -f frontend/src/components/PageHeader.tsx
rm -f frontend/src/components/EmptyState.tsx
rm -f frontend/src/components/StatCard.tsx
rm -f frontend/src/components/StatusBadge.tsx
rm -f frontend/src/components/Button.tsx
rm -f frontend/src/components/BatchEmailDialog.tsx
```

(If `frontend/src/layouts/` is now empty, also `rm -rf frontend/src/layouts`.)

- [ ] **Step 10.7: Re-run build to confirm clean**

```powershell
cd frontend && npm run build
cd ..
```
Expected: success. If anything still references a deleted file, the error message will tell you exactly where.

- [ ] **Step 10.8: Commit**

```bash
git add -A
git commit -m "feat(routes): mount Settings/Templates/Outreach; remove deprecated /cold and /direct"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 11: E2E smoke + visual check

- [ ] **Step 11.1: Run all backend tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend -v --ignore=tests/backend/test_routers.py
```
Expected: all pass — Plans 1-4 = 57 tests + Plan 5 new tests = 57 + 6 + 2 + 6 + 7 = 78 tests.

- [ ] **Step 11.2: Frontend build**

```powershell
cd frontend && npm run build
cd ..
```
Expected: success. Bundle size may have decreased noticeably from the deleted code.

- [ ] **Step 11.3: Manual E2E check**

Restart backend (so the new routers load) + frontend. Then:

1. Open `http://localhost:5173/settings`. Expected: form loads with empty defaults (or your previous values if `output/settings.json` already exists from a prior dev session). Fill in name, hourly rate, SMTP host/port/user/password, sender name, from email. Click "Save settings". Reload — values persist. Password field shows `••••••••`.

2. Open `http://localhost:5173/templates`. Expected: 4 seeded templates listed (Initial Outreach, Initial Outreach (with insights), Follow-up, Final Follow-up). Click "New template", fill in name/subject/body, save. New template appears. Click pencil on any template → edit → save → row updates. Click trash → confirm → row disappears.

3. Open `http://localhost:5173/outreach`. Expected: left pane lists opportunities that have a `contact_email` (may be 0 if no email extraction has been done — that's fine). Right pane says "Select an opportunity…". Click an opp → composer appears with To/email. Pick a template → preview renders with `{name}`, `{first_name}`, `{company}`, `{title}` etc. substituted. Click "Edit" to override subject/body. Click "Send email" — if SMTP isn't configured, you'll get "SMTP not configured" message; if it is, the email actually sends and the opp's stage advances to `contacted` (visible in Pipeline + Inbox).

4. Try every sidebar nav link — Hub, Inbox, Pipeline, Sources, Outreach, Templates, Settings. ALL should load real pages now (no more placeholders).

5. Try `/cold/dashboard` or `/direct/scans/new` directly in the URL bar. Expected: redirect to `/inbox` (the root redirect catches everything unmatched, since the old route block is gone).

- [ ] **Step 11.4: Cleanup commit (only if anything is uncommitted)**

```bash
git status
# If there's anything outstanding, commit it.
```

---

## Self-review notes (already addressed inline)

- **Spec coverage:** Outreach (pick opp → template → preview → send) ✓, Templates CRUD ✓, Settings full round-trip with masked password ✓, Cleanup of `/cold/*` + `/direct/*` and dead components ✓.
- **Placeholders:** None. Every step has full code.
- **Type consistency:** `Settings` shape matches between Python (`settings_store._DEFAULTS`) and TypeScript (`types/settings.ts`). `EmailTemplate` shape matches between Python (`templates_store._SEED`) and TypeScript (`types/template.ts`). `OutreachSendRequest` Pydantic model matches `OutreachSendBody` TypeScript interface.
- **Stage advance correctness:** outreach send only writes `contacted` when current stage is `new`/`researching`/empty — never downgrades a `meeting`/`won`/`lost` lead. Section is auto-derived from `opportunity_type` (cold → cold section, direct → direct section). Plan 1's bug (hardcoded `cold` section) does NOT regress — Plan 5 explicitly passes the right section.
- **Backwards compat:** Old `/api/email/*` endpoints in `shared.py` are NOT removed in this plan. They're still hardcoded with the same 4 templates. If anything external (e.g., a test, a CLI script) calls them, it keeps working. The new UI uses `/api/outreach/send` exclusively. Removing the old endpoints is a future cleanup if they're confirmed unused.
- **Risk #1 — settings.json contains plaintext SMTP password:** Acceptable for a single-user local tool. If multi-user / cloud deployment ever happens, switch to a secret store (or move to Supabase encrypted storage in Plan 7).
- **Risk #2 — old `EMAIL_TEMPLATES` in `shared.py` diverges from new templates_store:** Acceptable for v1 — the old endpoints are legacy and the seed data in templates_store mirrors them. If we delete the old endpoints in a future cleanup, we delete `EMAIL_TEMPLATES` too.
- **Risk #3 — deleting `frontend/src/components/Button.tsx`:** the new design system has its own `Button` in `frontend/src/design/primitives/Button.tsx`. As long as no NEW page imports the old `components/Button`, deletion is safe. Step 10.5 catches this via the build.
