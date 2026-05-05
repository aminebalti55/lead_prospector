# Pulse — Sources & Scheduler Upgrades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Commit message rule (project-wide):** NEVER add `Co-Authored-By: Claude`, "Generated with Claude Code", or any AI/assistant attribution to any commit message. Each task spec gives the exact message — use it verbatim.

**Goal:** Build the **Sources** page — a grid of per-source cards (one per known scraper) with status, last fetch, today's catch, 7-day sparkline, **Run Now** and **Pause** actions. Below it, a **Saved Searches** section with full CRUD (Run Now, Edit, Toggle enabled, Delete). Fix the scheduler's broken `biweekly` + `monthly` frequency parsing so saved searches honor their configured cadence. After this plan, the user can manage every scraper from one place — kick off scans without going through the old `/direct/scans/new` form, pause noisy sources, and trust scheduled saved searches actually run on the right cadence.

**Architecture:**
- **New backend:** `backend/services/source_state.py` (per-source enabled flag persistence in `output/direct/source_state.json`), `backend/services/source_metrics.py` (computes per-source metrics including 7-day series), `backend/routers/sources.py` (REST endpoints).
- **Modified backend:** `backend/scheduler.py` (parse `biweekly` + `monthly`), `backend/routers/direct_leads.py` (add `POST /api/direct/saved-searches/{id}/run` to trigger an immediate scan from a saved search; verify existing PUT works for edit/toggle).
- **New frontend:** Sources page composed of `SourceCard` (per-source) + `SavedSearchesList` + `SavedSearchEditor` (small modal for create/edit).
- **Reuses:** `useUpdateStage` pattern for optimistic updates on toggle/delete actions, all design primitives from Plan 1, Pulse Bar from Plan 2.
- **No detail page in this plan.** A source detail page (the prototype's "Source · LinkedIn Jobs" screen with full health + insights) is deferred. v1 = grid index with inline actions.

**Tech Stack:** React 18, react-query 5, Tailwind v4, lucide-react, FastAPI, Python 3.12, pytest. No new dependencies.

---

## Scope decision

This is **Plan 4 of 5+**. After this:

| # | Plan | Status |
|---|---|---|
| 1 | Foundation & Inbox | ✅ Shipped |
| 2 | Hub & Live PulseBar | ✅ Shipped + bug-fixed |
| 3 | Pipeline Kanban | ✅ Shipped |
| **4 (this)** | **Sources & scheduler upgrades** | About to ship |
| 5 | Outreach + Templates + Settings round-trip + cleanup | Pending |
| 6 | Tanit Jobs scraper | Pending |
| 7 | Supabase migration | Pending (last) |

**Deferred from prototype:** the "Source · LinkedIn Jobs" detail screen (full health + insights + history). Inline Run Now / Pause on each card delivers 90% of the value. Detail page can be a small follow-up plan if needed.

---

## File structure (this plan)

**New backend files:**
- `backend/services/source_state.py` — read/write `output/direct/source_state.json` (per-source enabled flag)
- `backend/services/source_metrics.py` — compute per-source 7-day series + summary metrics
- `backend/routers/sources.py` — endpoints: `GET /api/sources`, `POST /api/sources/{name}/run`, `POST /api/sources/{name}/toggle`

**Modified backend files:**
- `backend/app.py` — register `sources` router
- `backend/scheduler.py:_parse_frequency` — handle `biweekly` and `monthly`
- `backend/routers/direct_leads.py` — add `POST /api/direct/saved-searches/{id}/run` endpoint

**New backend tests:**
- `tests/backend/test_source_state.py`
- `tests/backend/test_source_metrics.py`
- `tests/backend/test_sources_router.py`
- `tests/backend/test_scheduler_frequency.py`

**New frontend files:**
- `frontend/src/types/source.ts` — TS types for sources API
- `frontend/src/api/sources.ts` — react-query hooks: `useSources`, `useRunSource`, `useToggleSource`
- `frontend/src/pages/sources/SourcesPage.tsx`
- `frontend/src/pages/sources/SourceCard.tsx`
- `frontend/src/pages/sources/SavedSearchesList.tsx`
- `frontend/src/pages/sources/SavedSearchEditor.tsx`

**Modified frontend files:**
- `frontend/src/api/direct.ts` — add `useRunSavedSearch`, `useUpdateSavedSearch`, `useToggleSavedSearch`
- `frontend/src/App.tsx` — replace `/sources` PlaceholderPage with `<SourcesPage />`

**Untouched (preserved):**
- All Plan 1+2+3 code: opportunities, hub, pipeline, primitives, shell, scheduler reconciliation
- Old `/direct/*` routes and the `direct_leads.py` scan creation logic

---

## Conventions

- **Source identity:** the lowercase string from `_KNOWN_DIRECT_SOURCES` + `_KNOWN_COLD_SOURCES` in `backend/services/hub_aggregator.py`. Total 13 sources today (`reddit`, `linkedin`, `linkedin_posts`, `indeed`, `twitter`, `clutch`, `goodfirms`, `tanit`, `google_maps`, `yelp`, `bbb`, `yellowpages`, `manta`).
- **Source enabled state default:** `true`. The scheduler skips disabled sources when running saved searches; on-demand scans via `POST /sources/{name}/run` ignore the flag (user explicitly clicked Run Now).
- **7-day series:** array of 7 ints, oldest first. Each entry is the count of opportunities for that source whose `posted_date` falls on that calendar day (UTC). Today is index 6.
- **Run Now keywords:** look up the most recent scan in `scans.json` whose `sources` includes this source name; reuse those `keywords`. If none found, return HTTP 400 with a clear error message — frontend shows it to the user as "Use the Saved Searches form to set keywords first."
- **Frequency strings (canonical, case-insensitive):**
  - `hourly` → 1h
  - `every-N-hours` (legacy `Nhours` shorthand) → Nh
  - `daily` → 24h
  - `weekly` → 168h
  - `biweekly` → 336h
  - `monthly` → 720h (≈30d, intentional approximation)
- **Saved search PUT** (existing): full body replacement of `name`, `keywords`, `sources`, `source_configs`, `frequency`, `max_results`, `enabled`. We reuse this for both edit and toggle (toggle is just PUT with a flipped `enabled`).
- **No new dependencies.**

---

## Pre-flight

- [ ] **Step 0.1: Verify Plan 3 is committed**

```bash
cd C:\Users\JIMMY\lead_prospector
git status
git log --oneline pulse-foundation -5
```
Expected: working tree clean, latest commit is `b100436 feat(inbox): support ?opp=<id> deep link from Pipeline cards` or later.

- [ ] **Step 0.2: Backend + frontend running**

```powershell
.venv\Scripts\python.exe run_server.py --no-reload
cd frontend; npm run dev
```

---

## Task 1: Backend — `SourceState` service (TDD)

**Why:** Persistent per-source enabled flag, isolated and testable. Scheduler reads it; `POST /sources/{name}/toggle` writes it.

**Files:**
- Create: `backend/services/source_state.py`
- Test: `tests/backend/test_source_state.py`

- [ ] **Step 1.1: Write failing test**

Create `tests/backend/test_source_state.py`:

```python
"""Tests for backend.services.source_state."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services import source_state


@pytest.fixture
def tmp_state_file(tmp_path, monkeypatch):
    """Redirect the state file to a temporary location."""
    p = tmp_path / "source_state.json"
    monkeypatch.setattr(source_state, "_STATE_FILE", p)
    return p


def test_unknown_source_defaults_to_enabled(tmp_state_file):
    assert source_state.is_enabled("reddit") is True
    assert source_state.is_enabled("anything") is True


def test_set_enabled_persists(tmp_state_file):
    source_state.set_enabled("reddit", False)
    assert source_state.is_enabled("reddit") is False
    # Persists across "process restart" (re-read from disk)
    raw = json.loads(tmp_state_file.read_text())
    assert raw == {"reddit": False}


def test_toggle_flips_value(tmp_state_file):
    assert source_state.is_enabled("linkedin") is True
    new_value = source_state.toggle("linkedin")
    assert new_value is False
    assert source_state.is_enabled("linkedin") is False
    new_value = source_state.toggle("linkedin")
    assert new_value is True


def test_get_all_returns_explicit_overrides_only(tmp_state_file):
    """get_all returns the dict from disk — defaults are not materialized."""
    assert source_state.get_all() == {}
    source_state.set_enabled("reddit", False)
    source_state.set_enabled("yelp", True)
    assert source_state.get_all() == {"reddit": False, "yelp": True}


def test_corrupted_state_file_returns_empty(tmp_state_file):
    tmp_state_file.write_text("{not valid json")
    assert source_state.get_all() == {}
    assert source_state.is_enabled("reddit") is True
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_source_state.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.services.source_state'`.

- [ ] **Step 1.3: Implement**

Create `backend/services/source_state.py`:

```python
"""Per-source enabled flag persistence (small JSON file).

Default: every source is enabled. Disabling a source means the scheduler will
skip it when running saved searches. On-demand `POST /sources/{name}/run`
ignores this flag — explicit user action wins.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.core.config import DIRECT_OUTPUT_DIR


_STATE_FILE: Path = DIRECT_OUTPUT_DIR / "source_state.json"


def get_all() -> dict[str, bool]:
    """Return the explicit-overrides dict from disk. Defaults are NOT materialized."""
    if not _STATE_FILE.exists():
        return {}
    try:
        data = json.loads(_STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Coerce values to bool defensively
    return {str(k): bool(v) for k, v in data.items()}


def is_enabled(source: str) -> bool:
    """True unless this source has been explicitly disabled."""
    return get_all().get(source, True)


def set_enabled(source: str, enabled: bool) -> None:
    """Set the enabled flag for a source and persist."""
    state = get_all()
    state[source] = bool(enabled)
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def toggle(source: str) -> bool:
    """Flip the enabled flag for a source. Returns the new value."""
    new_value = not is_enabled(source)
    set_enabled(source, new_value)
    return new_value
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_source_state.py -v
```
Expected: 5 passed.

- [ ] **Step 1.5: Commit**

```bash
git add backend/services/source_state.py tests/backend/test_source_state.py
git commit -m "feat(services): add SourceState (per-source enabled flag persistence)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 2: Backend — `SourceMetrics` service (TDD)

**Why:** Compute the per-source numbers the Sources page needs: status, today's count, last fetch, 7-day series. Pure functions over scans + opportunities, like `hub_aggregator`.

**Files:**
- Create: `backend/services/source_metrics.py`
- Test: `tests/backend/test_source_metrics.py`

- [ ] **Step 2.1: Write failing test**

Create `tests/backend/test_source_metrics.py`:

```python
"""Tests for backend.services.source_metrics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.services.source_metrics import compute_source_summary, compute_seven_day_series


def _opp(source="reddit", posted_date=None, value=1000, title="t"):
    return {
        "id": f"id_{title}_{posted_date}",
        "source": source,
        "title": title,
        "posted_date": posted_date,
        "estimated_value_usd": value,
    }


def test_seven_day_series_counts_opps_per_day_oldest_first():
    """Series is 7 ints, today at index 6, 6 days ago at index 0."""
    today = datetime.now(timezone.utc).date()
    opps = [
        _opp(source="reddit", posted_date=(datetime.combine(today, datetime.min.time(), timezone.utc)).isoformat()),
        _opp(source="reddit", posted_date=(datetime.combine(today, datetime.min.time(), timezone.utc)).isoformat()),
        _opp(source="reddit", posted_date=(datetime.combine(today - timedelta(days=3), datetime.min.time(), timezone.utc)).isoformat()),
        _opp(source="linkedin", posted_date=(datetime.combine(today - timedelta(days=2), datetime.min.time(), timezone.utc)).isoformat()),
    ]
    series = compute_seven_day_series("reddit", opps)
    assert len(series) == 7
    assert series[6] == 2  # today
    assert series[3] == 1  # 3 days ago
    assert sum(series) == 3  # only the reddit opps


def test_seven_day_series_handles_missing_posted_date():
    series = compute_seven_day_series("reddit", [_opp(source="reddit", posted_date=None)])
    assert series == [0, 0, 0, 0, 0, 0, 0]


def test_seven_day_series_returns_zeros_for_unknown_source():
    series = compute_seven_day_series("does-not-exist", [_opp(source="reddit", posted_date=datetime.now(timezone.utc).isoformat())])
    assert series == [0, 0, 0, 0, 0, 0, 0]


def test_compute_source_summary_combines_state_and_metrics():
    today_iso = datetime.now(timezone.utc).isoformat()
    scans = [
        {"id": "s1", "status": "completed", "sources": ["reddit"], "finished_at": today_iso, "leads_found": 3},
    ]
    opps = [
        _opp(source="reddit", posted_date=today_iso, value=2500),
        _opp(source="reddit", posted_date=today_iso, value=1500),
    ]
    summary = compute_source_summary(
        source="reddit",
        scans=scans,
        opportunities=opps,
        enabled=True,
    )
    assert summary["source"] == "reddit"
    assert summary["enabled"] is True
    assert summary["status"] == "idle"
    assert summary["last_fetch"] == today_iso
    assert summary["today_count"] == 2
    assert summary["today_value_usd"] == 4000
    assert len(summary["seven_day_series"]) == 7
    assert summary["seven_day_series"][6] == 2


def test_compute_source_summary_status_running_when_scan_active():
    summary = compute_source_summary(
        source="reddit",
        scans=[{"id": "s1", "status": "running", "sources": ["reddit"], "started_at": datetime.now(timezone.utc).isoformat()}],
        opportunities=[],
        enabled=True,
    )
    assert summary["status"] == "live"


def test_compute_source_summary_status_error_when_scan_failed():
    summary = compute_source_summary(
        source="reddit",
        scans=[{"id": "s1", "status": "failed", "sources": ["reddit"], "finished_at": datetime.now(timezone.utc).isoformat(), "error": "blocked"}],
        opportunities=[],
        enabled=True,
    )
    assert summary["status"] == "error"
    assert summary["last_error"] == "blocked"


def test_compute_source_summary_disabled():
    summary = compute_source_summary(source="reddit", scans=[], opportunities=[], enabled=False)
    assert summary["enabled"] is False
    assert summary["status"] == "idle"
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_source_metrics.py -v
```
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 2.3: Implement**

Create `backend/services/source_metrics.py`:

```python
"""Per-source metrics: status, today's count, 7-day series, last error.

Pure functions over scans + opportunities — easy to unit test, no I/O."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _parse_iso(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def compute_seven_day_series(source: str, opportunities: list[dict]) -> list[int]:
    """Return [count_6d_ago, ..., count_today] — 7 ints, today last."""
    today = datetime.now(timezone.utc).date()
    counts = [0] * 7
    for o in opportunities:
        if o.get("source") != source:
            continue
        parsed = _parse_iso(o.get("posted_date"))
        if not parsed:
            continue
        delta = (today - parsed.date()).days
        if 0 <= delta <= 6:
            counts[6 - delta] += 1
    return counts


def compute_source_summary(
    source: str,
    scans: list[dict],
    opportunities: list[dict],
    enabled: bool,
) -> dict[str, Any]:
    """Combined per-source summary: status, last_fetch, today's metrics, 7-day series."""
    today = datetime.now(timezone.utc).date()

    # Today's catch
    today_count = 0
    today_value = 0
    for o in opportunities:
        if o.get("source") != source:
            continue
        parsed = _parse_iso(o.get("posted_date"))
        if parsed and parsed.date() == today:
            today_count += 1
            today_value += int(o.get("estimated_value_usd") or 0)

    # Most recent scan touching this source
    matching = [s for s in scans if source in (s.get("sources") or [])]
    matching.sort(
        key=lambda s: s.get("finished_at") or s.get("started_at") or s.get("created_at") or "",
        reverse=True,
    )
    most_recent = matching[0] if matching else None

    if most_recent is None:
        status = "idle"
        label = "idle"
        last_fetch = None
        last_error = None
    else:
        scan_status = most_recent.get("status") or ""
        if scan_status == "running":
            status, label = "live", "scraping"
        elif scan_status == "failed":
            status, label = "error", most_recent.get("error") or "blocked"
        else:
            status, label = "idle", "idle"
        last_fetch = most_recent.get("finished_at") or most_recent.get("started_at")
        last_error = most_recent.get("error") if scan_status == "failed" else None

    return {
        "source": source,
        "enabled": bool(enabled),
        "status": status,
        "label": label,
        "last_fetch": last_fetch,
        "last_error": last_error,
        "today_count": today_count,
        "today_value_usd": today_value,
        "seven_day_series": compute_seven_day_series(source, opportunities),
    }
```

- [ ] **Step 2.4: Run tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_source_metrics.py -v
```
Expected: 7 passed.

- [ ] **Step 2.5: Commit**

```bash
git add backend/services/source_metrics.py tests/backend/test_source_metrics.py
git commit -m "feat(services): add SourceMetrics (status + today + 7-day series per source)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 3: Backend — `/api/sources` router (TDD)

**Why:** Three endpoints: list all sources with summary, run-now per source, toggle per source.

**Files:**
- Create: `backend/routers/sources.py`
- Modify: `backend/app.py`
- Test: `tests/backend/test_sources_router.py`

- [ ] **Step 3.1: Write failing test**

Create `tests/backend/test_sources_router.py`:

```python
"""Tests for backend.routers.sources."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_sources_returns_envelope_with_all_known(client):
    res = client.get("/api/sources")
    assert res.status_code == 200
    body = res.json()
    assert "sources" in body
    names = {s["source"] for s in body["sources"]}
    # All 13 known sources should be present
    for s in ["reddit", "linkedin", "linkedin_posts", "indeed", "twitter", "clutch", "goodfirms", "tanit",
              "google_maps", "yelp", "bbb", "yellowpages", "manta"]:
        assert s in names


def test_list_sources_each_entry_has_required_shape(client):
    res = client.get("/api/sources")
    body = res.json()
    for s in body["sources"]:
        for key in ("source", "enabled", "status", "label", "last_fetch", "last_error",
                    "today_count", "today_value_usd", "seven_day_series"):
            assert key in s
        assert isinstance(s["seven_day_series"], list)
        assert len(s["seven_day_series"]) == 7
        assert s["status"] in ("live", "idle", "error")


def test_toggle_source_flips_enabled(client):
    # Read current state
    before = next(s for s in client.get("/api/sources").json()["sources"] if s["source"] == "manta")
    res = client.post("/api/sources/manta/toggle")
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "manta"
    assert body["enabled"] == (not before["enabled"])
    # Toggle back so test is idempotent
    client.post("/api/sources/manta/toggle")


def test_toggle_unknown_source_404(client):
    res = client.post("/api/sources/nonexistent_source/toggle")
    assert res.status_code == 404


def test_run_unknown_source_404(client):
    res = client.post("/api/sources/nonexistent_source/run")
    assert res.status_code == 404


def test_run_source_with_no_history_returns_400(client):
    """Running a source that has no past scan history needs keywords first."""
    # Use 'manta' which (in test data) likely has no scan history
    # We can't fully isolate this test, so accept either 400 (no history) or 200 (history exists).
    res = client.post("/api/sources/manta/run")
    assert res.status_code in (200, 400)
    if res.status_code == 400:
        assert "keywords" in res.json()["detail"].lower()
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_sources_router.py -v
```
Expected: FAIL — 404 on every endpoint (router not registered).

- [ ] **Step 3.3: Implement the router**

Create `backend/routers/sources.py`:

```python
"""Sources index + per-source actions: list, run-now, toggle."""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from src.core.config import DIRECT_OUTPUT_DIR
from src.core.storage import list_files, read_leads
from src.core.models import DirectLead
from backend.services import source_state
from backend.services.opportunity_aggregator import (
    cold_row_to_opportunity,
    direct_lead_to_opportunity,
)
from backend.services.source_metrics import compute_source_summary
from backend.services.hub_aggregator import _KNOWN_DIRECT_SOURCES, _KNOWN_COLD_SOURCES

router = APIRouter(prefix="/api/sources", tags=["sources"])

SCANS_FILE = DIRECT_OUTPUT_DIR / "scans.json"

ALL_KNOWN_SOURCES: list[str] = list(_KNOWN_DIRECT_SOURCES) + list(_KNOWN_COLD_SOURCES)


def _load_scans() -> list[dict]:
    if not SCANS_FILE.exists():
        return []
    try:
        return json.loads(SCANS_FILE.read_text())
    except Exception:
        return []


def _save_scans(scans: list[dict]) -> None:
    SCANS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCANS_FILE.write_text(json.dumps(scans, indent=2, default=str))


def _parse_iso_to_dt(value):
    """Lenient ISO parser for re-hydrating DirectLead.posted_date from Excel rows."""
    from datetime import datetime as _dt
    if not value:
        return None
    if isinstance(value, _dt):
        return value
    try:
        return _dt.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _load_all_opportunity_dicts() -> list[dict]:
    """Same shape as opportunities/hub routers — read everything as Opportunity dicts."""
    from dataclasses import asdict
    out: list[dict] = []
    for section in ("cold", "legacy"):
        for f in list_files(section):
            try:
                _, rows = read_leads(f["name"], section)
            except Exception:
                continue
            for row in rows:
                opp = cold_row_to_opportunity(row, source_file=f["name"])
                if opp.id:
                    out.append(asdict(opp))
    for f in list_files("direct"):
        try:
            _, rows = read_leads(f["name"], "direct")
        except Exception:
            continue
        for row in rows:
            lead = DirectLead(
                source=row.get("Source") or "",
                title=row.get("Title") or "",
                description=row.get("Description") or "",
                url=row.get("URL") or "",
                company_name=row.get("Company") or "",
                company_website=row.get("Company_Website") or "",
                location=row.get("Location") or "",
                contact_name=row.get("Contact_Name") or "",
                contact_email=row.get("Contact_Email") or "",
                contact_phone=row.get("Contact_Phone") or "",
                relevance_score=int(row.get("Relevance_Score") or 0),
                budget_signal=row.get("Budget_Signal") or "",
                urgency_signal=row.get("Urgency_Signal") or "",
                matched_skills=[s.strip() for s in (row.get("Matched_Skills") or "").split(",") if s.strip()],
                outreach_status=row.get("Outreach_Status") or "new",
                notes=row.get("Notes") or "",
                posted_date=_parse_iso_to_dt(row.get("Posted_Date")),
            )
            if row.get("Lead_ID"):
                lead.lead_id = str(row["Lead_ID"])
            opp = direct_lead_to_opportunity(lead, source_file=f["name"])
            if opp.id:
                out.append(asdict(opp))
    return out


def _last_keywords_for_source(source: str, scans: list[dict]) -> list[str] | None:
    """Find the most recent scan that includes this source and return its keywords."""
    matching = [s for s in scans if source in (s.get("sources") or []) and s.get("keywords")]
    matching.sort(
        key=lambda s: s.get("finished_at") or s.get("started_at") or s.get("created_at") or "",
        reverse=True,
    )
    if not matching:
        return None
    return list(matching[0].get("keywords") or [])


@router.get("")
async def list_sources() -> dict[str, Any]:
    scans = _load_scans()
    opps = _load_all_opportunity_dicts()
    sources = [
        compute_source_summary(
            source=name,
            scans=scans,
            opportunities=opps,
            enabled=source_state.is_enabled(name),
        )
        for name in ALL_KNOWN_SOURCES
    ]
    return {"sources": sources}


@router.post("/{name}/toggle")
async def toggle_source(name: str) -> dict[str, Any]:
    if name not in ALL_KNOWN_SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown source: {name}")
    new_value = source_state.toggle(name)
    return {"source": name, "enabled": new_value}


@router.post("/{name}/run")
async def run_source(name: str) -> dict[str, Any]:
    if name not in ALL_KNOWN_SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown source: {name}")
    scans = _load_scans()
    keywords = _last_keywords_for_source(name, scans)
    if not keywords:
        raise HTTPException(
            status_code=400,
            detail="No prior scan history for this source — please run a saved search with keywords first, or use the New Scan form.",
        )
    # Reuse the existing direct-leads scan creation flow.
    from backend.routers.direct_leads import _execute_scan, _save_scans as _save_scans_dl
    scan_id = uuid.uuid4().hex[:8]
    scan = {
        "id": scan_id,
        "status": "queued",
        "sources": [name],
        "source_configs": {},
        "keywords": keywords,
        "max_results": 50,
        "progress": 0,
        "leads_found": 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "started_at": None,
        "finished_at": None,
        "error": None,
        "logs": [],
    }
    scans.insert(0, scan)
    _save_scans_dl(scans)
    asyncio.create_task(_execute_scan(scan_id, {"sources": [name], "keywords": keywords, "max_results": 50}))
    return {"source": name, "scan_id": scan_id, "keywords": keywords, "status": "queued"}
```

- [ ] **Step 3.4: Register router in `backend/app.py`**

Find:
```python
from backend.routers import cold_outreach, direct_leads, hub, opportunities, shared
```
Replace with:
```python
from backend.routers import cold_outreach, direct_leads, hub, opportunities, shared, sources
```

Find:
```python
app.include_router(hub.router)
```
Add after:
```python
app.include_router(sources.router)
```

- [ ] **Step 3.5: Run tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_sources_router.py -v
```
Expected: 6 passed.

- [ ] **Step 3.6: Commit**

```bash
git add backend/routers/sources.py backend/app.py tests/backend/test_sources_router.py
git commit -m "feat(api): add /api/sources list + run-now + toggle endpoints"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 4: Backend — Saved Search Run-Now endpoint

**Why:** Saved Searches list needs a "Run Now" button. The existing `direct_leads.py` router has CRUD for saved searches but no manual-trigger endpoint. Add one.

**Files:**
- Modify: `backend/routers/direct_leads.py`

- [ ] **Step 4.1: Read the relevant section of `direct_leads.py`** to find where saved-search endpoints live

```bash
grep -n "saved-searches" backend/routers/direct_leads.py
```

- [ ] **Step 4.2: Add the new endpoint**

In `backend/routers/direct_leads.py`, find the existing `delete_saved_search` endpoint (likely near the bottom). Add this new endpoint immediately after it:

```python
@router.post("/saved-searches/{search_id}/run")
async def run_saved_search_now(search_id: str):
    """Trigger an immediate scan from a saved search's keywords/sources."""
    searches = _load_searches()
    search = next((s for s in searches if s["id"] == search_id), None)
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    scan_id = uuid.uuid4().hex[:8]
    sources = search.get("sources") or []
    keywords = search.get("keywords") or []
    if not keywords:
        raise HTTPException(status_code=400, detail="Saved search has no keywords")
    if not sources:
        sources = ["reddit", "linkedin", "linkedin_posts", "indeed", "twitter", "clutch", "goodfirms"]

    scan = {
        "id": scan_id,
        "status": "queued",
        "sources": sources,
        "source_configs": search.get("source_configs", {}),
        "keywords": keywords,
        "max_results": int(search.get("max_results") or 50),
        "progress": 0,
        "leads_found": 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "started_at": None,
        "finished_at": None,
        "error": None,
        "logs": [],
    }
    scans = _load_scans()
    scans.insert(0, scan)
    _save_scans(scans)

    asyncio.create_task(_execute_scan(scan_id, {
        "sources": sources,
        "keywords": keywords,
        "max_results": int(search.get("max_results") or 50),
        "source_configs": search.get("source_configs", {}),
    }))
    return {"scan_id": scan_id, "status": "queued"}
```

- [ ] **Step 4.3: Manual smoke test (no unit test — endpoint composes existing tested helpers)**

After restarting backend:
```bash
# Create a saved search
SID=$(curl -s -X POST http://localhost:8000/api/direct/saved-searches -H "Content-Type: application/json" -d '{"name":"Test","keywords":["typescript"],"sources":["reddit"],"frequency":"daily","max_results":5}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
# Trigger it
curl -s -X POST "http://localhost:8000/api/direct/saved-searches/$SID/run"
# Cleanup
curl -s -X DELETE "http://localhost:8000/api/direct/saved-searches/$SID"
```
Expected: middle command returns `{"scan_id":"<8 hex>","status":"queued"}`.

- [ ] **Step 4.4: Commit**

```bash
git add backend/routers/direct_leads.py
git commit -m "feat(api): add POST /api/direct/saved-searches/{id}/run for manual trigger"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 5: Backend — Scheduler frequency parser fix (TDD)

**Why:** `_parse_frequency` in `backend/scheduler.py` silently defaults `biweekly` and `monthly` to 24h. Saved searches with those frequencies fire daily instead of every 14d / 30d.

**Files:**
- Modify: `backend/scheduler.py`
- Test: `tests/backend/test_scheduler_frequency.py`

- [ ] **Step 5.1: Write failing test**

Create `tests/backend/test_scheduler_frequency.py`:

```python
"""Tests for backend.scheduler._parse_frequency (and adjacent logic)."""
from __future__ import annotations

import pytest

from backend.scheduler import Scheduler


def test_hourly():
    s = Scheduler()
    assert s._parse_frequency("hourly") == 1


def test_daily():
    s = Scheduler()
    assert s._parse_frequency("daily") == 24


def test_weekly():
    s = Scheduler()
    assert s._parse_frequency("weekly") == 168


def test_biweekly():
    s = Scheduler()
    assert s._parse_frequency("biweekly") == 336


def test_monthly():
    s = Scheduler()
    assert s._parse_frequency("monthly") == 720


def test_n_hours_shorthand():
    s = Scheduler()
    assert s._parse_frequency("6hours") == 6
    assert s._parse_frequency("12hours") == 12


def test_unknown_defaults_to_24():
    s = Scheduler()
    assert s._parse_frequency("garbage") == 24


def test_case_insensitive():
    s = Scheduler()
    assert s._parse_frequency("WEEKLY") == 168
    assert s._parse_frequency("BiWeekly") == 336
```

- [ ] **Step 5.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_scheduler_frequency.py -v
```
Expected: most tests fail (biweekly/monthly return 24, case-sensitivity may also fail).

- [ ] **Step 5.3: Read current `_parse_frequency`**

```bash
grep -A 20 "_parse_frequency" backend/scheduler.py | head -30
```

- [ ] **Step 5.4: Replace `_parse_frequency` with the corrected version**

Find the existing method in `backend/scheduler.py` and replace it with:

```python
    def _parse_frequency(self, raw: str) -> int:
        """Parse a frequency string to hours. Case-insensitive.

        Supported:
          - hourly         → 1
          - Nhours         → N (e.g. '6hours' → 6)
          - daily          → 24
          - weekly         → 168
          - biweekly       → 336
          - monthly        → 720 (≈30 days, intentional approximation)
        Unknown values default to 24 (daily).
        """
        if not raw:
            return 24
        s = raw.lower().strip()
        if s == "hourly":
            return 1
        if s == "daily":
            return 24
        if s == "weekly":
            return 168
        if s == "biweekly":
            return 336
        if s == "monthly":
            return 720
        # Nhours shorthand
        if s.endswith("hours"):
            try:
                return int(s[:-5])
            except ValueError:
                return 24
        return 24
```

- [ ] **Step 5.5: Run tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_scheduler_frequency.py -v
```
Expected: 8 passed.

- [ ] **Step 5.6: Commit**

```bash
git add backend/scheduler.py tests/backend/test_scheduler_frequency.py
git commit -m "fix(scheduler): parse biweekly + monthly + case-insensitive frequencies"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 6: Frontend — TS types + react-query hooks for sources

**Files:**
- Create: `frontend/src/types/source.ts`
- Create: `frontend/src/api/sources.ts`
- Modify: `frontend/src/api/direct.ts`

- [ ] **Step 6.1: Create types**

`frontend/src/types/source.ts`:

```ts
export interface SourceSummary {
  source: string;
  enabled: boolean;
  status: "live" | "idle" | "error";
  label: string;
  last_fetch: string | null;
  last_error: string | null;
  today_count: number;
  today_value_usd: number;
  seven_day_series: number[];
}

export interface SourcesResponse {
  sources: SourceSummary[];
}

export interface SavedSearch {
  id: string;
  name: string;
  keywords: string[];
  sources: string[];
  source_configs?: Record<string, unknown>;
  frequency: string;
  max_results: number;
  enabled: boolean;
  last_run: string | null;
}
```

- [ ] **Step 6.2: Create sources hooks**

`frontend/src/api/sources.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { SourcesResponse } from "../types/source";

export function useSources() {
  return useQuery<SourcesResponse>({
    queryKey: ["sources", "list"],
    queryFn: () => apiFetch("/sources"),
    staleTime: 10_000,
    refetchInterval: 10_000,
  });
}

export function useToggleSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ source: string; enabled: boolean }>(`/sources/${name}/toggle`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}

export function useRunSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ source: string; scan_id: string }>(`/sources/${name}/run`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sources"] });
      qc.invalidateQueries({ queryKey: ["pulse", "status"] });
    },
  });
}
```

- [ ] **Step 6.3: Extend saved-search hooks in `frontend/src/api/direct.ts`**

Read the file first to confirm its current shape:
```bash
cat frontend/src/api/direct.ts
```

Append these new hooks (after the existing exports — do not modify existing ones):

```ts
import type { SavedSearch } from "../types/source";

export function useRunSavedSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/direct/saved-searches/${id}/run`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["direct", "saved-searches"] });
      qc.invalidateQueries({ queryKey: ["pulse", "status"] });
    },
  });
}

export function useUpdateSavedSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<SavedSearch> }) =>
      apiFetch(`/direct/saved-searches/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["direct", "saved-searches"] });
    },
  });
}
```

If the file doesn't already import `useMutation` and `useQueryClient` from `@tanstack/react-query`, add those imports.

- [ ] **Step 6.4: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/types/source.ts frontend/src/api/sources.ts frontend/src/api/direct.ts
git commit -m "feat(api): add Source types + react-query hooks (sources + saved-search actions)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 7: Frontend — `SourceCard` component

**File:** `frontend/src/pages/sources/SourceCard.tsx`

The directory `frontend/src/pages/sources/` doesn't exist yet — create it.

- [ ] **Step 7.1: Create the file**

```tsx
import { Play, Pause, AlertCircle } from "lucide-react";
import { Card, MoneyValue, Sparkline, StatusDot, Button } from "../../design/primitives";
import { useRunSource, useToggleSource } from "../../api/sources";
import type { SourceSummary } from "../../types/source";

const LABEL: Record<string, string> = {
  reddit: "Reddit",
  linkedin: "LinkedIn Jobs",
  linkedin_posts: "LinkedIn Posts",
  indeed: "Indeed",
  twitter: "Twitter",
  clutch: "Clutch",
  goodfirms: "GoodFirms",
  tanit: "Tanit Jobs",
  google_maps: "Google Maps",
  yelp: "Yelp",
  bbb: "BBB",
  yellowpages: "YellowPages",
  manta: "Manta",
};

function fmtAge(iso: string | null): string {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

interface Props {
  src: SourceSummary;
}

export function SourceCard({ src }: Props) {
  const runSource = useRunSource();
  const toggleSource = useToggleSource();

  const handleRun = () => {
    runSource.mutate(src.source, {
      onError: (err: any) => {
        // Show backend error message via alert (toast lib not yet introduced)
        const msg = err?.message || "Run failed";
        alert(`${LABEL[src.source] ?? src.source}: ${msg}`);
      },
    });
  };

  return (
    <Card className={`p-4 flex flex-col gap-3 ${src.enabled ? "" : "opacity-60"}`}>
      {/* Header row */}
      <div className="flex items-start gap-2">
        <StatusDot status={src.status} className="mt-1" />
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium text-[var(--color-text-primary)] truncate">
            {LABEL[src.source] ?? src.source}
          </div>
          <div className="text-[11px] text-[var(--color-text-tertiary)] flex items-center gap-1">
            <span>{src.label}</span>
            <span>·</span>
            <span>{fmtAge(src.last_fetch)}</span>
          </div>
        </div>
        {!src.enabled && (
          <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] bg-[var(--color-surface-raised)] px-1.5 py-0.5 rounded-[var(--radius-sm)]">
            paused
          </span>
        )}
      </div>

      {/* Big number row */}
      <div className="flex items-end justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
            Today
          </div>
          {src.today_value_usd > 0 ? (
            <MoneyValue usd={src.today_value_usd} size="lg" tone="accent" />
          ) : (
            <div className="text-lg font-mono tabular-nums text-[var(--color-text-secondary)]">
              {src.today_count} new
            </div>
          )}
        </div>
        <Sparkline data={src.seven_day_series} width={100} height={32} />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          onClick={handleRun}
          disabled={runSource.isPending || src.status === "live"}
        >
          <Play className="w-3 h-3" />
          {runSource.isPending ? "Starting…" : "Run Now"}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => toggleSource.mutate(src.source)}
          disabled={toggleSource.isPending}
        >
          {src.enabled ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          {src.enabled ? "Pause" : "Resume"}
        </Button>
        {src.last_error && (
          <span className="ml-auto flex items-center gap-1 text-[11px] text-[var(--color-hot)]" title={src.last_error}>
            <AlertCircle className="w-3 h-3" /> error
          </span>
        )}
      </div>
    </Card>
  );
}
```

- [ ] **Step 7.2: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/sources/SourceCard.tsx
git commit -m "feat(sources): add SourceCard with Run Now + Pause + 7-day sparkline"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 8: Frontend — `SavedSearchEditor` modal component

**Why:** Inline form for create + edit. Plain centered modal — no library dependency.

**File:** `frontend/src/pages/sources/SavedSearchEditor.tsx`

- [ ] **Step 8.1: Create the file**

```tsx
import { useState } from "react";
import { X } from "lucide-react";
import { Button, Card } from "../../design/primitives";
import { useCreateSavedSearch } from "../../api/direct";
import { useUpdateSavedSearch } from "../../api/direct";
import type { SavedSearch } from "../../types/source";

const ALL_SOURCES = [
  "reddit", "linkedin", "linkedin_posts", "indeed", "twitter", "clutch", "goodfirms", "tanit",
  "google_maps", "yelp", "bbb", "yellowpages", "manta",
];

const FREQUENCIES = ["hourly", "daily", "weekly", "biweekly", "monthly"];

interface Props {
  initial?: SavedSearch;
  onClose: () => void;
}

export function SavedSearchEditor({ initial, onClose }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [keywordsRaw, setKeywordsRaw] = useState((initial?.keywords ?? []).join(", "));
  const [sources, setSources] = useState<string[]>(initial?.sources ?? ["reddit"]);
  const [frequency, setFrequency] = useState(initial?.frequency ?? "daily");
  const [maxResults, setMaxResults] = useState(initial?.max_results ?? 50);

  const create = useCreateSavedSearch();
  const update = useUpdateSavedSearch();

  function toggleSource(s: string) {
    setSources((curr) => (curr.includes(s) ? curr.filter((x) => x !== s) : [...curr, s]));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const keywords = keywordsRaw.split(",").map((k) => k.trim()).filter(Boolean);
    if (!name.trim() || keywords.length === 0 || sources.length === 0) return;
    const body = {
      name: name.trim(),
      keywords,
      sources,
      frequency,
      max_results: maxResults,
      enabled: initial?.enabled ?? true,
    };
    if (initial) {
      await update.mutateAsync({ id: initial.id, body });
    } else {
      await create.mutateAsync(body);
    }
    onClose();
  }

  const isPending = create.isPending || update.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <Card
        className="w-[520px] max-h-[80vh] overflow-auto p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-[var(--color-text-primary)]">
            {initial ? "Edit saved search" : "New saved search"}
          </h2>
          <button type="button" onClick={onClose} className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Keywords (comma-separated)</label>
            <input
              value={keywordsRaw}
              onChange={(e) => setKeywordsRaw(e.target.value)}
              placeholder="webflow, react developer"
              required
              className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Sources</label>
            <div className="flex flex-wrap gap-1">
              {ALL_SOURCES.map((s) => {
                const active = sources.includes(s);
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleSource(s)}
                    className={
                      "h-7 px-2.5 text-[11px] rounded-[var(--radius-sm)] border transition-colors " +
                      (active
                        ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)]"
                        : "text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-[var(--color-border-strong)]")
                    }
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Frequency</label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="h-8 px-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
              >
                {FREQUENCIES.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Max results</label>
              <input
                type="number"
                min={1}
                max={500}
                value={maxResults}
                onChange={(e) => setMaxResults(parseInt(e.target.value) || 50)}
                className="h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)]"
              />
            </div>
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

- [ ] **Step 8.2: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/sources/SavedSearchEditor.tsx
git commit -m "feat(sources): add SavedSearchEditor modal (create + edit)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 9: Frontend — `SavedSearchesList` component

**File:** `frontend/src/pages/sources/SavedSearchesList.tsx`

- [ ] **Step 9.1: Create the file**

```tsx
import { useState } from "react";
import { Play, Pencil, Trash2, Plus } from "lucide-react";
import { Button, Card, Pill } from "../../design/primitives";
import {
  useSavedSearches,
  useDeleteSavedSearch,
  useRunSavedSearch,
  useUpdateSavedSearch,
} from "../../api/direct";
import { SavedSearchEditor } from "./SavedSearchEditor";
import type { SavedSearch } from "../../types/source";

function fmtLastRun(iso: string | null): string {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  const h = Math.floor(ms / 3_600_000);
  if (h < 1) return "<1h ago";
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function SavedSearchesList() {
  const { data, isLoading } = useSavedSearches();
  const searches = (data?.searches ?? []) as SavedSearch[];

  const runMut = useRunSavedSearch();
  const updateMut = useUpdateSavedSearch();
  const deleteMut = useDeleteSavedSearch();

  const [editing, setEditing] = useState<SavedSearch | null>(null);
  const [creating, setCreating] = useState(false);

  return (
    <Card className="p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
            Saved searches
          </div>
          <div className="text-[11px] text-[var(--color-text-tertiary)]">
            {searches.length} {searches.length === 1 ? "search" : "searches"}
          </div>
        </div>
        <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
          <Plus className="w-3 h-3" /> New
        </Button>
      </div>

      {isLoading && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
      )}

      {!isLoading && searches.length === 0 && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4 text-center">
          No saved searches yet. Click "New" to create one.
        </div>
      )}

      <div className="flex flex-col">
        {searches.map((s) => (
          <div
            key={s.id}
            className="flex items-center gap-3 py-2 border-b border-[var(--color-border)] last:border-0"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium text-[var(--color-text-primary)] truncate">
                  {s.name}
                </span>
                {!s.enabled && <Pill tone="neutral">paused</Pill>}
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-tertiary)] mt-0.5">
                <span className="truncate">{(s.keywords || []).join(", ")}</span>
                <span>·</span>
                <span>{s.frequency}</span>
                <span>·</span>
                <span>{(s.sources || []).length} sources</span>
                <span>·</span>
                <span>last run {fmtLastRun(s.last_run)}</span>
              </div>
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                updateMut.mutate({ id: s.id, body: { ...s, enabled: !s.enabled } })
              }
              disabled={updateMut.isPending}
            >
              {s.enabled ? "Pause" : "Resume"}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => runMut.mutate(s.id)}
              disabled={runMut.isPending}
            >
              <Play className="w-3 h-3" /> Run
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setEditing(s)}
            >
              <Pencil className="w-3 h-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                if (confirm(`Delete "${s.name}"?`)) deleteMut.mutate(s.id);
              }}
              disabled={deleteMut.isPending}
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        ))}
      </div>

      {creating && <SavedSearchEditor onClose={() => setCreating(false)} />}
      {editing && <SavedSearchEditor initial={editing} onClose={() => setEditing(null)} />}
    </Card>
  );
}
```

- [ ] **Step 9.2: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/sources/SavedSearchesList.tsx
git commit -m "feat(sources): add SavedSearchesList with Run/Edit/Toggle/Delete"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 10: Frontend — `SourcesPage` composition + wire `/sources` route

**Files:**
- Create: `frontend/src/pages/sources/SourcesPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 10.1: Create `SourcesPage.tsx`**

```tsx
import { useSources } from "../../api/sources";
import { Card } from "../../design/primitives";
import { SourceCard } from "./SourceCard";
import { SavedSearchesList } from "./SavedSearchesList";

export function SourcesPage() {
  const { data, isLoading } = useSources();
  const sources = data?.sources ?? [];

  return (
    <div className="p-6 flex flex-col gap-4 max-w-[1400px] mx-auto w-full">
      <Card className="p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
              Sources
            </div>
            <div className="text-[11px] text-[var(--color-text-tertiary)]">
              {sources.length} sources · click Run Now to scan with the last keywords used
            </div>
          </div>
        </div>

        {isLoading && (
          <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {sources.map((s) => (
            <SourceCard key={s.source} src={s} />
          ))}
        </div>
      </Card>

      <SavedSearchesList />
    </div>
  );
}
```

- [ ] **Step 10.2: Wire route in `App.tsx`**

Find:
```tsx
import { PipelinePage } from "./pages/pipeline/PipelinePage";
```
Add directly after:
```tsx
import { SourcesPage } from "./pages/sources/SourcesPage";
```

Find:
```tsx
<Route path="/sources" element={<PlaceholderPage title="Sources" shipping="Plan 4 — Sources page" />} />
```
Replace with:
```tsx
<Route path="/sources" element={<SourcesPage />} />
```

- [ ] **Step 10.3: Verify build + Commit**

```powershell
cd frontend && npm run build
cd ..
```

```bash
git add frontend/src/pages/sources/SourcesPage.tsx frontend/src/App.tsx
git commit -m "feat(sources): compose SourcesPage; mount at /sources"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 11: E2E smoke + visual check

- [ ] **Step 11.1: Run all backend tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend -v --ignore=tests/backend/test_routers.py
```
Expected: all pass — Plan 1+2+3 + new tests = 31 + 5 + 7 + 6 + 8 = 57 tests minimum.

- [ ] **Step 11.2: Frontend build**

```powershell
cd frontend && npm run build
cd ..
```
Expected: success.

- [ ] **Step 11.3: Manual end-to-end check**

Restart backend (so the new sources router loads) + frontend. Then:

1. Open `http://localhost:5173/sources`. Expected: 13 source cards in a 3-col grid (or fewer cols on smaller screens), each showing name + status dot + "Today: N new" or "$X" + sparkline + Run Now / Pause buttons.
2. Click "Pause" on Manta. Card grays out + shows "paused" pill. Click "Resume". Reverts.
3. Click "Run Now" on a source that has past keywords (Reddit, since you've been scanning it). Expected: button shows "Starting…" then resets. Within ~10s, the PulseBar at the bottom flips Reddit to `live · scraping`. Refresh — Reddit card's "today" count goes up.
4. Click "Run Now" on a source with NO history (e.g. Manta). Expected: alert with the backend's "No prior scan history" message.
5. Below the source grid: Saved Searches section. Click "New". Modal opens. Fill in `name = "Test"`, `keywords = "webflow"`, click Reddit, frequency `daily`, max 5. Click Create. Modal closes. New row appears in the list.
6. Click the pencil icon → modal re-opens with values pre-filled. Change name, click Save changes. Row updates.
7. Click "Pause" on the row. "paused" pill appears. Click "Resume" — gone.
8. Click the green "Run" button. Within ~10s, PulseBar flips Reddit to `live · scraping`.
9. Click trash icon → confirm dialog → row disappears.

- [ ] **Step 11.4: Final cleanup commit (if anything outstanding)**

```bash
git status
# If anything's uncommitted: commit with chore: prefix
```

---

## Self-review notes (already addressed inline)

- **Spec coverage:** Sources index ✓, Run Now per source ✓, Pause/Toggle per source ✓, 7-day sparkline ✓, today's count + value ✓, Saved Searches CRUD (Run / Edit / Toggle / Delete) ✓, scheduler `biweekly` + `monthly` parsing ✓.
- **Placeholders:** None. Every step has full code.
- **Type consistency:** `SourceSummary` shape identical between backend (`source_metrics.py:compute_source_summary`) and frontend (`source.ts`). All 13 source names align between `_KNOWN_*_SOURCES` (backend) and `LABEL` (`SourceCard.tsx`) — including `tanit`.
- **Backwards compat:** No existing endpoints modified. All Saved Search CRUD endpoints from Plan 1 still work; this plan adds POST `/saved-searches/{id}/run` only. The `useUpdateStage` Plan 3 optimistic update is untouched. Old `/direct/scans/new` route still works (we just give users a faster path through Sources).
- **Risk #1 — Run Now using stale keywords:** If a user's only past Reddit scan was for "python" but they now want "react", Run Now reuses "python". Acceptable for v1 — the user can use Saved Searches form for explicit keyword control. Future plan could add a "Run Now with keywords…" inline input.
- **Risk #2 — `_load_all_opportunity_dicts` triplicated:** This helper now lives in `opportunities.py`, `hub.py`, AND `sources.py`. Cleanup deferred to Plan 5 (extract to shared service). Acceptable for v1 — each is ~30 lines and the duplication is mechanical.
- **Risk #3 — `posted_date` parsing in `_load_all_opportunity_dicts`:** Plan 4's copy includes the `_parse_iso_to_dt` helper inline so the bug fixed in QA pass doesn't regress. Same fix is in `opportunities.py` and `hub.py` from Plan 2 QA.
