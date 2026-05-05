# Pulse — Hub & Live PulseBar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Commit message rule (project-wide):** NEVER add `Co-Authored-By: Claude`, "Generated with Claude Code", or any AI/assistant attribution to any commit message. Each task spec gives the exact message — use it verbatim.

**Goal:** Build the **Hub** dashboard (money-first hero stat + hottest opps + scraper status grid + recent activity feed) and wire the existing static `PulseBar` to live scraper data via a polling endpoint. After this plan ships, opening `/hub` shows a real, useful operator cockpit showing actual `$` in pipeline, top opportunities to work today, scraper health, and recent events. The Pulse Bar at the bottom of every page reflects real scraper activity instead of demo placeholders.

**Architecture:**
- **Backend, additive:** add a new `backend/routers/hub.py` exposing `GET /api/hub/stats`, `GET /api/hub/activity`, `GET /api/pulse/status`. All three are read-aggregators over the existing storage layer (Excel files + scans.json), no new persistence. Polling is preferred over WebSockets for v1 — simpler, works with the existing FastAPI setup, fine at 5-second cadence.
- **Frontend:** add `frontend/src/pages/hub/HubPage.tsx` composed of 4 sub-components (`HeroStat`, `HottestOpps`, `ScraperStatusGrid`, `ActivityFeed`). Update the existing `PulseBar` to consume a `usePulseStatus` polling hook instead of static data. Wire `/hub` to the new page (currently a placeholder).
- **Reuses Plan 1:** the `Opportunity` shape, `OpportunityListItem` (renamed export reused), and all design primitives (`Card`, `MoneyValue`, `Sparkline`, `StatusDot`, `Pill`).

**Tech Stack:** React 18, react-query 5, Tailwind v4, lucide-react. FastAPI, Python 3.12, pytest. No new dependencies.

---

## Scope decision

This is **Plan 2 of 5**. Plans 3–5 still to come:

| # | Plan | Status |
|---|---|---|
| 1 | Foundation & Inbox | ✅ Shipped |
| **2 (this)** | **Hub & Live PulseBar** | About to ship |
| 3 | Pipeline Kanban (drag-drop, stage transitions, $ totals per lane) | Pending |
| 4 | Sources & scheduler upgrades (Run Now, Pause, Edit, frequency fixes) | Pending |
| 5 | Outreach + Settings round-trip + cleanup (remove old `/cold/*` and `/direct/*` routes) | Pending |

---

## File structure (this plan)

**New backend files:**
- `backend/routers/hub.py` — three endpoints: stats, activity, pulse-status
- `backend/services/hub_aggregator.py` — pure functions that compute stats / activity / pulse-status from existing storage; tested in isolation

**Modified backend files:**
- `backend/app.py` — register the new router

**New backend tests:**
- `tests/backend/test_hub_aggregator.py`
- `tests/backend/test_hub_router.py`

**New frontend files:**
- `frontend/src/types/hub.ts` — TS types matching the new endpoints
- `frontend/src/api/hub.ts` — react-query hooks (`useHubStats`, `useHubActivity`, `usePulseStatus`)
- `frontend/src/pages/hub/HubPage.tsx`
- `frontend/src/pages/hub/HeroStat.tsx`
- `frontend/src/pages/hub/HottestOpps.tsx`
- `frontend/src/pages/hub/ScraperStatusGrid.tsx`
- `frontend/src/pages/hub/ScraperStatusCard.tsx`
- `frontend/src/pages/hub/ActivityFeed.tsx`

**Modified frontend files:**
- `frontend/src/components/shell/PulseBar.tsx` — replace static array with `usePulseStatus` hook
- `frontend/src/App.tsx` — swap `/hub` placeholder for `<HubPage />`

**Untouched (preserved):**
- All Plan 1 code: opportunities router, Inbox page, primitives, shell, etc.
- Old `/cold/*` and `/direct/*` routes — still alive

---

## Conventions

- **Stage groupings (from Plan 1's `Stage` enum):**
  - `pipeline` = `{new, researching, contacted, replied, meeting}` — actively being worked
  - `closed_won` = `{won}`
  - `closed_lost` = `{lost}`
- **Pipeline `$` value** = sum of `estimated_value_usd` for opps with stage in `pipeline`.
- **"Won this month" `$` value** = sum of `estimated_value_usd` for opps with stage = `won`. (We don't track stage-change timestamps yet, so we count CURRENT won. Limitation accepted for v1.)
- **"This week" `$` value** = sum of `estimated_value_usd` for opps with `posted_date >= 7 days ago` and stage in `pipeline`.
- **Response rate** = `(opps with stage in {replied, meeting, won}) / (opps with stage != new and != lost)` — i.e., of the opps we've actually contacted, how many replied? Returns `0` if denominator is 0.
- **Pulse status sources** = derived from the unique `source` values seen in `scans.json` PLUS a fixed list of known direct-leads sources (`reddit`, `linkedin`, `linkedin_posts`, `indeed`, `twitter`, `clutch`, `goodfirms`). Plus cold sources (`google_maps`, `yelp`, `bbb`, `yellowpages`, `manta`). The frontend renders all of them; ones with no activity show as `idle`.
- **Activity feed events** are derived from:
  - Each completed scan in `scans.json` → one `scan_completed` event
  - Each in-progress scan → one `scan_running` event
  - The N most recent opportunities by `posted_date` → `lead_added` events
  - Sort all by timestamp desc, take top 30.
- **Polling cadence:** Hub stats polled every 30s; pulse status polled every 5s; activity polled every 15s. (Hardcoded in the hooks for simplicity — no global config.)

---

## Pre-flight

- [ ] **Step 0.1: Verify Plan 1 is committed and the branch is up-to-date**

```bash
cd C:\Users\JIMMY\lead_prospector
git status
git log --oneline pulse-foundation -5
```
Expected: working tree clean, on `pulse-foundation`, latest commit is the polish pass `7077e8d feat(shell): add static PulseBar, workspace footer, polished placeholder pages` or later.

- [ ] **Step 0.2: Backend + frontend running**

If not already running, start them in separate terminals:
```powershell
.venv\Scripts\python.exe run_server.py --no-reload
cd frontend; npm run dev
```

---

## Task 1: Backend — `HubAggregator` service (TDD)

**Why:** Pure functions that compute stats / activity / pulse-status from existing data. Tested in isolation so the router is just transport.

**Files:**
- Create: `backend/services/hub_aggregator.py`
- Test: `tests/backend/test_hub_aggregator.py`

- [ ] **Step 1.1: Write the failing test**

Create `tests/backend/test_hub_aggregator.py`:

```python
"""Tests for backend.services.hub_aggregator."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.services.hub_aggregator import (
    compute_stats,
    compute_pulse_status,
    compute_activity,
)


def _opp(stage="new", value=1000, posted_date=None, type_="direct", source="reddit", title="t"):
    """Helper to build an opportunity-shaped dict."""
    return {
        "id": f"id_{title}_{stage}_{value}",
        "type": type_,
        "source": source,
        "title": title,
        "stage": stage,
        "estimated_value_usd": value,
        "score": 50,
        "priority": "warm",
        "posted_date": posted_date,
        "company_name": "",
        "location": "",
        "matched_skills": [],
    }


def test_stats_pipeline_sums_active_stages():
    opps = [
        _opp(stage="new", value=1000),
        _opp(stage="contacted", value=2000),
        _opp(stage="meeting", value=3000),
        _opp(stage="won", value=4000),       # excluded (closed)
        _opp(stage="lost", value=5000),       # excluded (closed)
    ]
    stats = compute_stats(opps)
    assert stats["pipeline_total_usd"] == 6000
    assert stats["won_total_usd"] == 4000


def test_stats_response_rate():
    """Replied/meeting/won as % of contacted-or-later."""
    opps = [
        _opp(stage="new"),       # not in denominator
        _opp(stage="contacted"), # denominator
        _opp(stage="contacted"), # denominator
        _opp(stage="replied"),   # denominator + numerator
        _opp(stage="meeting"),   # denominator + numerator
        _opp(stage="won"),       # denominator + numerator
        _opp(stage="lost"),      # not in denominator
    ]
    stats = compute_stats(opps)
    # 5 in denominator (contacted, contacted, replied, meeting, won), 3 in numerator
    assert stats["response_rate"] == pytest.approx(0.6, abs=0.001)


def test_stats_response_rate_zero_when_no_contacts():
    stats = compute_stats([_opp(stage="new"), _opp(stage="new")])
    assert stats["response_rate"] == 0.0


def test_stats_this_week_sums_recent_pipeline_only():
    now = datetime.now()
    recent = (now - timedelta(days=2)).isoformat()
    old = (now - timedelta(days=10)).isoformat()
    opps = [
        _opp(stage="new", value=500, posted_date=recent),       # included
        _opp(stage="contacted", value=700, posted_date=recent), # included
        _opp(stage="new", value=1000, posted_date=old),         # excluded (old)
        _opp(stage="won", value=2000, posted_date=recent),      # excluded (won)
    ]
    stats = compute_stats(opps)
    assert stats["this_week_usd"] == 1200


def test_stats_count_breakdown():
    opps = [
        _opp(stage="new"),
        _opp(stage="new"),
        _opp(stage="contacted"),
        _opp(stage="won"),
    ]
    stats = compute_stats(opps)
    assert stats["count_total"] == 4
    assert stats["count_pipeline"] == 3
    assert stats["count_won"] == 1


def test_pulse_status_returns_known_sources_with_idle_default():
    """Always return entries for ALL known direct + cold sources, even if no activity."""
    pulse = compute_pulse_status(scans=[], opportunities=[])
    sources = {p["source"] for p in pulse}
    # Direct sources
    for s in ["reddit", "linkedin", "indeed", "twitter", "clutch", "goodfirms"]:
        assert s in sources
    # Cold sources
    for s in ["google_maps", "yelp", "bbb", "yellowpages", "manta"]:
        assert s in sources
    # All idle when there's no scan history
    assert all(p["status"] == "idle" for p in pulse)


def test_pulse_status_running_for_active_scan():
    scans = [
        {
            "id": "s1",
            "status": "running",
            "sources": ["reddit"],
            "started_at": datetime.now().isoformat(),
            "leads_found": 0,
        }
    ]
    pulse = compute_pulse_status(scans=scans, opportunities=[])
    reddit = next(p for p in pulse if p["source"] == "reddit")
    assert reddit["status"] == "live"
    assert reddit["label"] == "scraping"


def test_pulse_status_failed_for_recent_failed_scan():
    scans = [
        {
            "id": "s1",
            "status": "failed",
            "sources": ["tanit"],
            "finished_at": datetime.now().isoformat(),
            "error": "blocked",
            "leads_found": 0,
        }
    ]
    # tanit isn't in known list — it'll appear because it was in a scan
    pulse = compute_pulse_status(scans=scans, opportunities=[])
    tanit = next((p for p in pulse if p["source"] == "tanit"), None)
    assert tanit is not None
    assert tanit["status"] == "error"
    assert tanit["label"] == "blocked"


def test_pulse_status_today_count_from_opportunities():
    today = datetime.now().isoformat()
    opps = [
        _opp(source="reddit", posted_date=today, title="a"),
        _opp(source="reddit", posted_date=today, title="b"),
        _opp(source="linkedin", posted_date=today, title="c"),
    ]
    pulse = compute_pulse_status(scans=[], opportunities=opps)
    reddit = next(p for p in pulse if p["source"] == "reddit")
    linkedin = next(p for p in pulse if p["source"] == "linkedin")
    assert reddit["today_count"] == 2
    assert linkedin["today_count"] == 1


def test_activity_includes_scan_completed():
    finish_time = datetime.now().isoformat()
    scans = [
        {
            "id": "s1",
            "status": "completed",
            "sources": ["reddit"],
            "keywords": ["webflow"],
            "leads_found": 5,
            "finished_at": finish_time,
        }
    ]
    activity = compute_activity(scans=scans, opportunities=[], limit=10)
    assert len(activity) >= 1
    e = activity[0]
    assert e["kind"] == "scan_completed"
    assert e["leads_found"] == 5
    assert "reddit" in e["sources"]


def test_activity_sorted_by_timestamp_desc_and_limited():
    now = datetime.now()
    scans = [
        {"id": "s1", "status": "completed", "sources": ["reddit"], "keywords": ["a"], "leads_found": 1, "finished_at": (now - timedelta(hours=2)).isoformat()},
        {"id": "s2", "status": "completed", "sources": ["linkedin"], "keywords": ["b"], "leads_found": 2, "finished_at": (now - timedelta(hours=1)).isoformat()},
        {"id": "s3", "status": "completed", "sources": ["indeed"], "keywords": ["c"], "leads_found": 3, "finished_at": now.isoformat()},
    ]
    activity = compute_activity(scans=scans, opportunities=[], limit=2)
    assert len(activity) == 2
    # Most recent first
    assert activity[0]["id"].endswith("s3")
    assert activity[1]["id"].endswith("s2")
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_hub_aggregator.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.services.hub_aggregator'`.

- [ ] **Step 1.3: Implement the aggregator**

Create `backend/services/hub_aggregator.py`:

```python
"""Hub dashboard aggregations: pipeline stats, scraper pulse status, recent activity.

Pure functions over storage data — easy to unit test, no I/O."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


# Stage groupings — must match src/core/models.py Stage enum
_PIPELINE_STAGES = {"new", "researching", "contacted", "replied", "meeting"}
_CONTACTED_OR_LATER = {"contacted", "replied", "meeting", "won", "lost"}
_RESPONDED = {"replied", "meeting", "won"}

# Sources we always show in the Pulse Bar / Scraper Status (even if idle).
_KNOWN_DIRECT_SOURCES = ["reddit", "linkedin", "linkedin_posts", "indeed", "twitter", "clutch", "goodfirms"]
_KNOWN_COLD_SOURCES = ["google_maps", "yelp", "bbb", "yellowpages", "manta"]


def compute_stats(opportunities: list[dict]) -> dict[str, Any]:
    """Compute money-first stats for the Hub hero + secondary cards."""
    pipeline_total = 0
    won_total = 0
    this_week_total = 0
    count_pipeline = 0
    count_won = 0
    contacted_or_later = 0
    responded = 0

    week_ago = datetime.now() - timedelta(days=7)

    for o in opportunities:
        stage = o.get("stage") or "new"
        value = int(o.get("estimated_value_usd") or 0)

        if stage in _PIPELINE_STAGES:
            pipeline_total += value
            count_pipeline += 1
            posted = o.get("posted_date")
            if posted:
                try:
                    if datetime.fromisoformat(posted) >= week_ago:
                        this_week_total += value
                except (ValueError, TypeError):
                    pass

        if stage == "won":
            won_total += value
            count_won += 1

        if stage in _CONTACTED_OR_LATER:
            contacted_or_later += 1
            if stage in _RESPONDED:
                responded += 1

    response_rate = (responded / contacted_or_later) if contacted_or_later else 0.0

    return {
        "pipeline_total_usd": pipeline_total,
        "won_total_usd": won_total,
        "this_week_usd": this_week_total,
        "response_rate": round(response_rate, 4),
        "count_total": len(opportunities),
        "count_pipeline": count_pipeline,
        "count_won": count_won,
    }


def compute_pulse_status(scans: list[dict], opportunities: list[dict]) -> list[dict[str, Any]]:
    """Per-source live status for the Pulse Bar + Scraper Status Grid.

    Returns one dict per source with: source, status (live|idle|error), label, last_fetch, today_count.
    """
    today = datetime.now().date()

    # Today's catch by source from opportunities
    today_count: dict[str, int] = {}
    for o in opportunities:
        posted = o.get("posted_date")
        if not posted:
            continue
        try:
            if datetime.fromisoformat(posted).date() == today:
                src = o.get("source") or ""
                today_count[src] = today_count.get(src, 0) + 1
        except (ValueError, TypeError):
            continue

    # Per-source state derived from scans (most recent wins per source)
    per_source: dict[str, dict[str, Any]] = {}
    # Sort scans newest first so first-seen-per-source is the most recent.
    scans_sorted = sorted(
        scans,
        key=lambda s: s.get("finished_at") or s.get("started_at") or s.get("created_at") or "",
        reverse=True,
    )
    for scan in scans_sorted:
        for src in scan.get("sources") or []:
            if src in per_source:
                continue
            status_str = scan.get("status") or ""
            if status_str == "running":
                per_source[src] = {"status": "live", "label": "scraping"}
            elif status_str == "failed":
                per_source[src] = {"status": "error", "label": scan.get("error") or "blocked"}
            elif status_str == "completed":
                per_source[src] = {"status": "idle", "label": "idle"}
            else:
                per_source[src] = {"status": "idle", "label": status_str or "idle"}
            per_source[src]["last_fetch"] = scan.get("finished_at") or scan.get("started_at")

    # Build the final list — every known source plus any extras seen in scans.
    all_sources = list(_KNOWN_DIRECT_SOURCES) + list(_KNOWN_COLD_SOURCES)
    for s in per_source:
        if s not in all_sources:
            all_sources.append(s)

    out = []
    for src in all_sources:
        state = per_source.get(src, {"status": "idle", "label": "idle", "last_fetch": None})
        out.append({
            "source": src,
            "status": state["status"],
            "label": state["label"],
            "last_fetch": state.get("last_fetch"),
            "today_count": today_count.get(src, 0),
        })
    return out


def compute_activity(scans: list[dict], opportunities: list[dict], limit: int = 30) -> list[dict[str, Any]]:
    """Recent activity feed. Mixes scan events and lead-added events, sorted by time desc."""
    events: list[dict] = []

    for scan in scans:
        ts = scan.get("finished_at") or scan.get("started_at") or scan.get("created_at")
        if not ts:
            continue
        kind = "scan_completed" if scan.get("status") == "completed" else (
            "scan_failed" if scan.get("status") == "failed" else "scan_running"
        )
        events.append({
            "id": f"scan_{scan.get('id', '')}",
            "kind": kind,
            "ts": ts,
            "sources": scan.get("sources") or [],
            "keywords": scan.get("keywords") or [],
            "leads_found": scan.get("leads_found") or 0,
            "error": scan.get("error"),
        })

    # Lead-added events from opportunities with posted_date
    for o in opportunities:
        posted = o.get("posted_date")
        if not posted:
            continue
        events.append({
            "id": f"lead_{o.get('id', '')}",
            "kind": "lead_added",
            "ts": posted,
            "title": o.get("title") or "",
            "source": o.get("source") or "",
            "value_usd": int(o.get("estimated_value_usd") or 0),
            "priority": o.get("priority") or "cold",
        })

    events.sort(key=lambda e: e["ts"], reverse=True)
    return events[:limit]
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_hub_aggregator.py -v
```
Expected: 11 passed.

- [ ] **Step 1.5: Commit**

```bash
git add backend/services/hub_aggregator.py tests/backend/test_hub_aggregator.py
git commit -m "feat(services): add HubAggregator (stats + pulse status + activity)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 2: Backend — `/api/hub` + `/api/pulse` router (TDD)

**Why:** Three endpoints that read storage and call the aggregator. The router is thin transport.

**Files:**
- Create: `backend/routers/hub.py`
- Modify: `backend/app.py`
- Test: `tests/backend/test_hub_router.py`

- [ ] **Step 2.1: Write the failing test**

Create `tests/backend/test_hub_router.py`:

```python
"""Tests for backend.routers.hub."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_hub_stats_returns_required_keys(client):
    res = client.get("/api/hub/stats")
    assert res.status_code == 200
    body = res.json()
    for k in ("pipeline_total_usd", "won_total_usd", "this_week_usd", "response_rate", "count_total", "count_pipeline", "count_won"):
        assert k in body
    assert isinstance(body["pipeline_total_usd"], int)
    assert isinstance(body["response_rate"], (int, float))


def test_hub_activity_returns_list_envelope(client):
    res = client.get("/api/hub/activity")
    assert res.status_code == 200
    body = res.json()
    assert "events" in body
    assert isinstance(body["events"], list)


def test_hub_activity_respects_limit(client):
    res = client.get("/api/hub/activity?limit=5")
    assert res.status_code == 200
    assert len(res.json()["events"]) <= 5


def test_pulse_status_returns_list_envelope(client):
    res = client.get("/api/pulse/status")
    assert res.status_code == 200
    body = res.json()
    assert "sources" in body
    assert isinstance(body["sources"], list)
    # All known direct + cold sources should always be present.
    sources = {s["source"] for s in body["sources"]}
    for s in ["reddit", "linkedin", "google_maps", "yelp"]:
        assert s in sources


def test_pulse_status_each_entry_has_required_shape(client):
    res = client.get("/api/pulse/status")
    body = res.json()
    for s in body["sources"]:
        assert "source" in s
        assert "status" in s
        assert s["status"] in ("live", "idle", "error")
        assert "label" in s
        assert "today_count" in s
        assert "last_fetch" in s  # may be None
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_hub_router.py -v
```
Expected: FAIL with 404 on every endpoint (router not registered).

- [ ] **Step 2.3: Implement the router**

Create `backend/routers/hub.py`:

```python
"""Hub + Pulse status endpoints. Read-aggregators over the existing storage."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from src.core.config import DIRECT_OUTPUT_DIR
from src.core.storage import list_files, read_leads
from src.core.models import DirectLead
from backend.services.opportunity_aggregator import (
    cold_row_to_opportunity,
    direct_lead_to_opportunity,
)
from backend.services.hub_aggregator import (
    compute_stats,
    compute_pulse_status,
    compute_activity,
)

router = APIRouter(tags=["hub"])

SCANS_FILE = DIRECT_OUTPUT_DIR / "scans.json"


def _load_scans() -> list[dict]:
    if not SCANS_FILE.exists():
        return []
    try:
        return json.loads(SCANS_FILE.read_text())
    except Exception:
        return []


def _load_all_opportunity_dicts() -> list[dict]:
    """Same logic as opportunities router — read everything as Opportunity dicts."""
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
            )
            if row.get("Lead_ID"):
                lead.lead_id = str(row["Lead_ID"])
            opp = direct_lead_to_opportunity(lead, source_file=f["name"])
            if opp.id:
                out.append(asdict(opp))
    return out


@router.get("/api/hub/stats")
async def get_hub_stats() -> dict[str, Any]:
    opps = _load_all_opportunity_dicts()
    return compute_stats(opps)


@router.get("/api/hub/activity")
async def get_hub_activity(limit: int = Query(30, ge=1, le=200)) -> dict[str, Any]:
    opps = _load_all_opportunity_dicts()
    scans = _load_scans()
    return {"events": compute_activity(scans, opps, limit=limit)}


@router.get("/api/pulse/status")
async def get_pulse_status() -> dict[str, Any]:
    opps = _load_all_opportunity_dicts()
    scans = _load_scans()
    return {"sources": compute_pulse_status(scans, opps)}
```

- [ ] **Step 2.4: Register the router**

Edit `backend/app.py`:

Find the line:
```python
from backend.routers import cold_outreach, direct_leads, opportunities, shared
```
Replace with:
```python
from backend.routers import cold_outreach, direct_leads, hub, opportunities, shared
```

Find the line:
```python
app.include_router(opportunities.router)
```
Add immediately after:
```python
app.include_router(hub.router)
```

- [ ] **Step 2.5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_hub_router.py -v
```
Expected: 5 passed.

- [ ] **Step 2.6: Commit**

```bash
git add backend/routers/hub.py backend/app.py tests/backend/test_hub_router.py
git commit -m "feat(api): add /api/hub/stats, /api/hub/activity, /api/pulse/status"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 3: Frontend — TS types + react-query hooks for Hub & Pulse

**Files:**
- Create: `frontend/src/types/hub.ts`
- Create: `frontend/src/api/hub.ts`

- [ ] **Step 3.1: Create the types**

`frontend/src/types/hub.ts`:

```ts
export interface HubStats {
  pipeline_total_usd: number;
  won_total_usd: number;
  this_week_usd: number;
  response_rate: number;
  count_total: number;
  count_pipeline: number;
  count_won: number;
}

export interface PulseSource {
  source: string;
  status: "live" | "idle" | "error";
  label: string;
  last_fetch: string | null;
  today_count: number;
}

export interface PulseStatusResponse {
  sources: PulseSource[];
}

export type ActivityEventKind =
  | "scan_running"
  | "scan_completed"
  | "scan_failed"
  | "lead_added";

export interface ActivityEvent {
  id: string;
  kind: ActivityEventKind;
  ts: string;
  // scan_* fields
  sources?: string[];
  keywords?: string[];
  leads_found?: number;
  error?: string | null;
  // lead_added fields
  title?: string;
  source?: string;
  value_usd?: number;
  priority?: "hot" | "warm" | "cold";
}

export interface ActivityResponse {
  events: ActivityEvent[];
}
```

- [ ] **Step 3.2: Create the hooks**

`frontend/src/api/hub.ts`:

```ts
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  HubStats,
  PulseStatusResponse,
  ActivityResponse,
} from "../types/hub";

export function useHubStats() {
  return useQuery<HubStats>({
    queryKey: ["hub", "stats"],
    queryFn: () => apiFetch("/hub/stats"),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

export function useHubActivity(limit = 30) {
  return useQuery<ActivityResponse>({
    queryKey: ["hub", "activity", limit],
    queryFn: () => apiFetch(`/hub/activity?limit=${limit}`),
    staleTime: 15_000,
    refetchInterval: 15_000,
  });
}

export function usePulseStatus() {
  return useQuery<PulseStatusResponse>({
    queryKey: ["pulse", "status"],
    queryFn: () => apiFetch("/pulse/status"),
    staleTime: 5_000,
    refetchInterval: 5_000,
  });
}
```

- [ ] **Step 3.3: Verify build + Commit**

```bash
cd frontend && npm run build
cd ..
git add frontend/src/types/hub.ts frontend/src/api/hub.ts
git commit -m "feat(api): add Hub types + react-query hooks (stats, activity, pulse)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 4: Frontend — `HeroStat` component

**Why:** The hero `$47,200 in pipeline this month` with sparkline is the single most important visual on the dashboard. Standalone component because it's reused (Hub page + future Pipeline page header).

**File:** `frontend/src/pages/hub/HeroStat.tsx`

- [ ] **Step 4.1: Create the component**

```tsx
import { ArrowUpRight } from "lucide-react";
import { Card, MoneyValue, Sparkline } from "../../design/primitives";

interface Props {
  label: string;
  usd: number;
  trend?: number[]; // optional sparkline series
  delta?: number;   // optional % change vs previous period
}

export function HeroStat({ label, usd, trend, delta }: Props) {
  return (
    <Card className="p-5 flex items-center gap-6">
      <div className="flex flex-col gap-1 min-w-0">
        <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
          {label}
        </span>
        <MoneyValue usd={usd} size="xl" tone="accent" abbreviate={false} />
        {delta !== undefined && (
          <span className="flex items-center gap-1 text-[11px] text-[var(--color-text-secondary)]">
            <ArrowUpRight className="w-3 h-3 text-[var(--color-accent)]" />
            <span className="tabular-nums">{(delta * 100).toFixed(1)}%</span>
            <span className="text-[var(--color-text-tertiary)]">vs last month</span>
          </span>
        )}
      </div>
      {trend && trend.length > 1 && (
        <div className="ml-auto">
          <Sparkline data={trend} width={140} height={42} />
        </div>
      )}
    </Card>
  );
}
```

- [ ] **Step 4.2: Verify build + Commit**

```bash
cd frontend && npm run build
cd ..
git add frontend/src/pages/hub/HeroStat.tsx
git commit -m "feat(hub): add HeroStat with sparkline + delta"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 5: Frontend — `HottestOpps` component

**Why:** Top-5 opportunities by score, single-line each. Reuses the existing `OpportunityListItem` (or a slimmer variant). Click → navigate to /inbox with the opp pre-selected.

**File:** `frontend/src/pages/hub/HottestOpps.tsx`

- [ ] **Step 5.1: Create the component**

```tsx
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useOpportunities } from "../../api/opportunities";
import { Card, MoneyValue, Pill, StatusDot } from "../../design/primitives";

export function HottestOpps() {
  const navigate = useNavigate();
  const { data, isLoading } = useOpportunities({
    sort: "score",
    priority: "hot",
    limit: 5,
  });
  const items = data?.opportunities ?? [];

  return (
    <Card className="p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
          Today's hottest opps
        </span>
        <button
          type="button"
          onClick={() => navigate("/inbox")}
          className="text-[11px] text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] flex items-center gap-1 transition-colors"
        >
          View all <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {isLoading && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
      )}

      {!isLoading && items.length === 0 && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">
          No hot opportunities yet. Run a scan to catch some.
        </div>
      )}

      <div className="flex flex-col">
        {items.map((opp) => (
          <button
            key={opp.id}
            type="button"
            onClick={() => navigate("/inbox")}
            className="flex items-center gap-2 py-1.5 text-left hover:bg-[var(--color-surface-raised)] rounded-[var(--radius-sm)] px-1 -mx-1 transition-colors"
          >
            <StatusDot status="hot" />
            <span className="text-[13px] text-[var(--color-text-primary)] truncate flex-1">
              {opp.title || "(no title)"}
            </span>
            <Pill tone="neutral">{opp.source}</Pill>
            <MoneyValue usd={opp.estimated_value_usd} size="sm" tone="accent" />
          </button>
        ))}
      </div>
    </Card>
  );
}
```

- [ ] **Step 5.2: Verify build + Commit**

```bash
cd frontend && npm run build
cd ..
git add frontend/src/pages/hub/HottestOpps.tsx
git commit -m "feat(hub): add HottestOpps top-5 list"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 6: Frontend — `ScraperStatusCard` + `ScraperStatusGrid`

**Files:**
- Create: `frontend/src/pages/hub/ScraperStatusCard.tsx`
- Create: `frontend/src/pages/hub/ScraperStatusGrid.tsx`

- [ ] **Step 6.1: Create `ScraperStatusCard.tsx`**

```tsx
import clsx from "clsx";
import { StatusDot, Pill } from "../../design/primitives";
import type { PulseSource } from "../../types/hub";

const LABEL: Record<string, string> = {
  reddit: "Reddit",
  linkedin: "LinkedIn Jobs",
  linkedin_posts: "LinkedIn Posts",
  indeed: "Indeed",
  twitter: "Twitter",
  clutch: "Clutch",
  goodfirms: "GoodFirms",
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
  src: PulseSource;
}

export function ScraperStatusCard({ src }: Props) {
  return (
    <div
      className={clsx(
        "p-3 rounded-[var(--radius-md)] border bg-[var(--color-surface)]",
        src.status === "error"
          ? "border-[var(--color-hot-soft)]"
          : "border-[var(--color-border)]",
      )}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <StatusDot status={src.status} />
        <span className="text-[12px] font-medium text-[var(--color-text-primary)] flex-1 truncate">
          {LABEL[src.source] ?? src.source}
        </span>
        {src.today_count > 0 && (
          <Pill tone="accent">{src.today_count}</Pill>
        )}
      </div>
      <div className="text-[11px] text-[var(--color-text-tertiary)] flex items-center justify-between">
        <span className="truncate">{src.label}</span>
        <span className="tabular-nums shrink-0 ml-2">{fmtAge(src.last_fetch)}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 6.2: Create `ScraperStatusGrid.tsx`**

```tsx
import { Card } from "../../design/primitives";
import { usePulseStatus } from "../../api/hub";
import { ScraperStatusCard } from "./ScraperStatusCard";

export function ScraperStatusGrid() {
  const { data, isLoading } = usePulseStatus();
  const sources = data?.sources ?? [];

  return (
    <Card className="p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
          Scraper status
        </span>
        <span className="text-[11px] text-[var(--color-text-tertiary)]">
          {sources.length} sources
        </span>
      </div>

      {isLoading && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
        {sources.map((s) => (
          <ScraperStatusCard key={s.source} src={s} />
        ))}
      </div>
    </Card>
  );
}
```

- [ ] **Step 6.3: Verify build + Commit**

```bash
cd frontend && npm run build
cd ..
git add frontend/src/pages/hub/ScraperStatusCard.tsx frontend/src/pages/hub/ScraperStatusGrid.tsx
git commit -m "feat(hub): add ScraperStatusGrid + ScraperStatusCard with live polling"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 7: Frontend — `ActivityFeed` component

**File:** `frontend/src/pages/hub/ActivityFeed.tsx`

- [ ] **Step 7.1: Create the component**

```tsx
import { Activity, AlertCircle, CheckCircle2, Plus, Loader2 } from "lucide-react";
import { Card, MoneyValue, Pill } from "../../design/primitives";
import { useHubActivity } from "../../api/hub";
import type { ActivityEvent } from "../../types/hub";

function fmtAge(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60_000);
  if (m < 1) return "now";
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

function EventIcon({ kind }: { kind: ActivityEvent["kind"] }) {
  const props = { className: "w-3.5 h-3.5", strokeWidth: 1.75 };
  switch (kind) {
    case "scan_running":
      return <Loader2 {...props} className="w-3.5 h-3.5 text-[var(--color-accent)] animate-spin" />;
    case "scan_completed":
      return <CheckCircle2 {...props} className="w-3.5 h-3.5 text-[var(--color-accent)]" />;
    case "scan_failed":
      return <AlertCircle {...props} className="w-3.5 h-3.5 text-[var(--color-hot)]" />;
    case "lead_added":
      return <Plus {...props} className="w-3.5 h-3.5 text-[var(--color-cool)]" />;
    default:
      return <Activity {...props} className="w-3.5 h-3.5" />;
  }
}

function EventRow({ e }: { e: ActivityEvent }) {
  let middle: React.ReactNode = null;

  if (e.kind === "scan_completed") {
    middle = (
      <span>
        Scan completed: <span className="text-[var(--color-text-primary)]">{(e.keywords || []).join(", ")}</span>
        {e.sources && e.sources.length > 0 && (
          <> on {e.sources.join(", ")}</>
        )} — caught {e.leads_found ?? 0} leads
      </span>
    );
  } else if (e.kind === "scan_running") {
    middle = (
      <span>
        Scanning: <span className="text-[var(--color-text-primary)]">{(e.keywords || []).join(", ")}</span>
      </span>
    );
  } else if (e.kind === "scan_failed") {
    middle = (
      <span>
        Scan failed: <span className="text-[var(--color-text-primary)]">{(e.keywords || []).join(", ")}</span>
        {e.error && <span className="text-[var(--color-hot)]"> — {e.error}</span>}
      </span>
    );
  } else if (e.kind === "lead_added") {
    middle = (
      <span className="flex items-center gap-1.5 min-w-0">
        <span className="truncate">New lead: <span className="text-[var(--color-text-primary)]">{e.title}</span></span>
        {e.source && <Pill tone="neutral">{e.source}</Pill>}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-2.5 py-2 border-b border-[var(--color-border)] last:border-0 text-[12px] text-[var(--color-text-secondary)]">
      <EventIcon kind={e.kind} />
      <div className="flex-1 min-w-0 flex items-center gap-2">
        {middle}
      </div>
      {e.kind === "lead_added" && typeof e.value_usd === "number" && e.value_usd > 0 && (
        <MoneyValue usd={e.value_usd} size="sm" tone="accent" />
      )}
      <span className="text-[11px] text-[var(--color-text-tertiary)] tabular-nums shrink-0">
        {fmtAge(e.ts)}
      </span>
    </div>
  );
}

export function ActivityFeed() {
  const { data, isLoading } = useHubActivity(20);
  const events = data?.events ?? [];

  return (
    <Card className="p-4 flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">
          Recent activity
        </span>
        <span className="text-[11px] text-[var(--color-text-tertiary)]">
          {events.length} events
        </span>
      </div>

      {isLoading && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
      )}

      {!isLoading && events.length === 0 && (
        <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">
          No activity yet. Run a scan to start the feed.
        </div>
      )}

      <div className="flex flex-col">
        {events.map((e) => (
          <EventRow key={e.id} e={e} />
        ))}
      </div>
    </Card>
  );
}
```

- [ ] **Step 7.2: Verify build + Commit**

```bash
cd frontend && npm run build
cd ..
git add frontend/src/pages/hub/ActivityFeed.tsx
git commit -m "feat(hub): add ActivityFeed (scan + lead events)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 8: Frontend — `HubPage` composition

**File:** `frontend/src/pages/hub/HubPage.tsx`

- [ ] **Step 8.1: Create the page**

```tsx
import { useHubStats } from "../../api/hub";
import { HeroStat } from "./HeroStat";
import { HottestOpps } from "./HottestOpps";
import { ScraperStatusGrid } from "./ScraperStatusGrid";
import { ActivityFeed } from "./ActivityFeed";

export function HubPage() {
  const { data: stats } = useHubStats();
  const pipeline = stats?.pipeline_total_usd ?? 0;
  const won = stats?.won_total_usd ?? 0;
  const week = stats?.this_week_usd ?? 0;
  const responseRate = stats?.response_rate ?? 0;

  return (
    <div className="p-6 flex flex-col gap-4 max-w-[1400px] mx-auto w-full">
      {/* Hero row: 1 big + 3 small */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
        <div className="lg:col-span-2">
          <HeroStat label="Pipeline this month" usd={pipeline} />
        </div>
        <HeroStat label="This week" usd={week} />
        <HeroStat label="Won this month" usd={won} />
      </div>

      {/* Secondary metric row */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
        <div className="lg:col-span-1 p-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
          <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1">
            Response rate
          </div>
          <div className="text-2xl font-mono tabular-nums text-[var(--color-text-primary)] font-medium">
            {(responseRate * 100).toFixed(1)}%
          </div>
        </div>
        <div className="lg:col-span-3 grid grid-cols-3 gap-3">
          <Tiny label="Total opps" value={stats?.count_total ?? 0} />
          <Tiny label="In pipeline" value={stats?.count_pipeline ?? 0} />
          <Tiny label="Won" value={stats?.count_won ?? 0} />
        </div>
      </div>

      {/* Body: hottest + status side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <HottestOpps />
        <ScraperStatusGrid />
      </div>

      {/* Activity feed full width */}
      <ActivityFeed />
    </div>
  );
}

function Tiny({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium mb-1">
        {label}
      </div>
      <div className="text-2xl font-mono tabular-nums text-[var(--color-text-primary)] font-medium">
        {value}
      </div>
    </div>
  );
}
```

- [ ] **Step 8.2: Verify build + Commit**

```bash
cd frontend && npm run build
cd ..
git add frontend/src/pages/hub/HubPage.tsx
git commit -m "feat(hub): compose HubPage from HeroStat + HottestOpps + ScraperStatusGrid + ActivityFeed"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 9: Frontend — Wire `/hub` route to `HubPage`

**File:** `frontend/src/App.tsx`

- [ ] **Step 9.1: Read current App.tsx**

```bash
cat frontend/src/App.tsx
```

- [ ] **Step 9.2: Update the import block**

Find the import of `PlaceholderPage`:
```tsx
import { PlaceholderPage } from "./pages/PlaceholderPage";
```
Add directly after:
```tsx
import { HubPage } from "./pages/hub/HubPage";
```

- [ ] **Step 9.3: Replace the `/hub` route element**

Find this line in the `<Route element={<AppShell />}>` block:
```tsx
<Route path="/hub" element={<PlaceholderPage title="Hub" shipping="Plan 2 — Hub & Pulse Bar" />} />
```
Replace with:
```tsx
<Route path="/hub" element={<HubPage />} />
```

- [ ] **Step 9.4: Verify build + Commit**

```bash
cd frontend && npm run build
cd ..
git add frontend/src/App.tsx
git commit -m "feat(routes): mount HubPage at /hub"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 10: Frontend — Wire `PulseBar` to live data

**Why:** The PulseBar exists but uses static demo data. Swap to the `usePulseStatus` polling hook so it breathes with real scraper activity.

**File:** `frontend/src/components/shell/PulseBar.tsx`

- [ ] **Step 10.1: Read current `PulseBar.tsx`**

```bash
cat frontend/src/components/shell/PulseBar.tsx
```

- [ ] **Step 10.2: Replace the file fully**

Overwrite `frontend/src/components/shell/PulseBar.tsx` with:

```tsx
import { StatusDot } from "../../design/primitives";
import { usePulseStatus } from "../../api/hub";

function fmtAge(iso: string | null): string {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

// Show only the most informative slice of sources in the bar (running first,
// then errors, then any with today_count > 0, then a couple idle to fill).
function pickShown(sources: ReturnType<typeof usePulseStatus>["data"] extends infer T ? T extends { sources: infer S } ? S : never : never): typeof sources {
  if (!sources) return [] as never;
  const live = sources.filter((s) => s.status === "live");
  const error = sources.filter((s) => s.status === "error");
  const active = sources.filter((s) => s.status === "idle" && s.today_count > 0);
  const filler = sources.filter((s) => s.status === "idle" && s.today_count === 0).slice(0, 3);
  const merged = [...live, ...error, ...active, ...filler];
  // Dedup by source name (keep first occurrence)
  const seen = new Set<string>();
  return merged.filter((s) => {
    if (seen.has(s.source)) return false;
    seen.add(s.source);
    return true;
  }).slice(0, 6) as never;
}

export function PulseBar() {
  const { data } = usePulseStatus();
  const sources = data?.sources ?? [];
  const shown = pickShown(sources);

  // Most recent last_fetch across all sources for the right-side timestamp
  const lastSyncs = sources.map((s) => s.last_fetch).filter((x): x is string => !!x);
  const lastSync = lastSyncs.sort().slice(-1)[0] ?? null;

  return (
    <footer className="h-7 shrink-0 border-t border-[var(--color-border)] bg-[var(--color-surface)] flex items-center px-4 gap-5 text-[11px] text-[var(--color-text-tertiary)] select-none">
      {shown.length === 0 && (
        <span className="text-[var(--color-text-tertiary)]">No scrapers configured</span>
      )}
      {shown.map((s) => (
        <span key={s.source} className="flex items-center gap-1.5">
          <StatusDot status={s.status} />
          <span className="text-[var(--color-text-secondary)] tabular-nums">{s.source}</span>
          <span>·</span>
          <span>
            {s.label}
            {s.today_count > 0 && s.status !== "live" && (
              <span className="text-[var(--color-accent)]"> · {s.today_count} new</span>
            )}
          </span>
        </span>
      ))}
      <span className="ml-auto text-[var(--color-text-tertiary)]">
        last sync {fmtAge(lastSync)}
      </span>
    </footer>
  );
}
```

- [ ] **Step 10.3: Verify build + Commit**

```bash
cd frontend && npm run build
cd ..
git add frontend/src/components/shell/PulseBar.tsx
git commit -m "feat(shell): wire PulseBar to live scraper status via 5s polling"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 11: E2E smoke + visual check

- [ ] **Step 11.1: Run all backend tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_opportunity_aggregator.py tests/backend/test_opportunities_router.py tests/backend/test_hub_aggregator.py tests/backend/test_hub_router.py -v
```
Expected: ~24 passed (Plan 1's 13 + Plan 2's 11 from aggregator + 5 from router = ~29; some tests may share names so confirm count).

- [ ] **Step 11.2: Build frontend**

```bash
cd frontend && npm run build
```
Expected: build succeeds, no type errors.

- [ ] **Step 11.3: Manual end-to-end check**

Restart backend + frontend. Open `http://localhost:5173/hub`. Expected:
1. Hero row shows three `$` cards (pipeline / this week / won) — all `$0` if no opportunities, but RENDER without errors.
2. Second row shows response rate + 3 small count tiles.
3. Below: HottestOpps card + ScraperStatusGrid card side-by-side.
4. Bottom: ActivityFeed card.
5. PulseBar at bottom of viewport shows real source state. With no scans run yet, all sources show as `idle · idle`.
6. If you start a scan from `/direct/scans/new` (old UI), within 5–10 seconds the PulseBar should flip the running source to `● live · scraping` (green pulsing dot). When scan completes, the ActivityFeed gets a new `Scan completed` event and the HottestOpps + stats update on the next 30s poll (or refresh).

- [ ] **Step 11.4: Final commit (if any housekeeping needed)**

```bash
git status
# Likely nothing to commit. If there is, commit it with a chore: prefix.
```

---

## Self-review notes (already addressed inline)

- **Spec coverage:** All 4 prototype Hub sections shipped (hero stats, hottest opps, scraper status grid, activity feed). PulseBar is now live. The prototype's "won this month" sparkline shows trend over time — we don't have stage-change history yet, so v1 has no sparkline data on the secondary stats. This is a known limitation; sparklines on secondary stats stay empty until Plan 4 adds event logging.
- **Stage filter on secondary `Tiny` tiles:** `count_pipeline` and `count_won` come from the stats endpoint, which uses the same Stage groupings as the Hub aggregator. Consistent.
- **Polling cadences:** stats 30s, activity 15s, pulse 5s. Spec doc above the file structure documents this.
- **Type consistency:** `PulseSource` and `ActivityEvent` field names match exactly between `backend/services/hub_aggregator.py` and `frontend/src/types/hub.ts`.
- **No placeholders:** Every `[ ]` task step contains the full code. No "see Task X" backreferences. Placeholder pages from Plan 1 stay for Pipeline/Sources/Outreach/Templates/Settings.
- **Backwards compat:** Plan 2 only ADDS files. The opportunities router from Plan 1 is untouched. The PulseBar's exported component name doesn't change, only its internals — `AppShell.tsx` doesn't need editing.
- **Risk:** `_load_all_opportunity_dicts` is duplicated between `hub.py` and `opportunities.py` routers. Acceptable for v1 — extracting a shared loader is a cleanup item for Plan 5. Tests cover both paths.
