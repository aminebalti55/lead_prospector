# Pulse — Foundation & Inbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebrand the lead_prospector frontend as **Pulse**, install a new dark-mode design system (Geist + volt-green accent on near-black), replace the cold/direct dual-app navigation with a unified shell (Hub / Inbox / Pipeline / Sources / Outreach / Templates / Settings), add a new unified `/api/opportunities` backend endpoint that merges cold leads and direct leads into one ranked feed with `$`-value estimates, and ship a working **Inbox** page (three-pane: filters · list · detail) the user can triage opportunities in. After this plan ships, the tool is usable in its new form for daily prospecting work.

**Architecture:**
- **Frontend, incremental:** add new routes (`/hub`, `/inbox`, etc.) alongside the old `/cold/*` and `/direct/*` routes. The new shell mounts on the new routes only. Old routes still work during transition. Old routes are removed in Plan 5.
- **Backend, additive:** add new endpoints (`/api/opportunities`, `/api/opportunities/{id}`, `/api/opportunities/{id}/stage`) without modifying existing cold/direct endpoints. The new endpoints are read-aggregators on top of the existing storage layer (Excel files).
- **Design system:** Geist font + a Tailwind v4 `@theme` block defining dark tokens. A small set of primitives (Button, Card, Pill, StatusDot, KbdHint, MoneyValue, Sparkline) used across all pages.
- **Inbox first** because it's the daily-use page. Hub, Pipeline, Sources come in subsequent plans.

**Tech Stack:** React 18, react-router-dom 6, Tailwind v4, @tanstack/react-query 5, lucide-react, Geist (fonts), FastAPI, Python 3.12, pytest.

---

## Scope decision

This is the **first of five plans** required for the full revamp. Each plan ships a usable increment:

| # | Plan | What ships |
|---|---|---|
| **1 (this)** | **Foundation & Inbox** | New design system, new shell, unified `/api/opportunities` endpoint, working Inbox page |
| 2 | Hub & Pulse Bar | Money-first hero dashboard + live scraper status bar (WebSocket) |
| 3 | Pipeline Kanban | Drag-drop kanban with stage transitions, `$`-value totals per lane |
| 4 | Sources & scheduler upgrades | Unified Sources view, Run Now / Pause / Edit / Toggle endpoints, scheduler frequency fixes |
| 5 | Outreach + Settings round-trip + cleanup | Outreach revamp, settings persistence, bug fixes (cold runs data shape, scans auto-refresh, biweekly/monthly), removal of `/cold/*` and `/direct/*` |

Plans 2–5 are written after Plan 1 ships and we validate the foundation works with real data.

---

## File structure (this plan)

**New backend files:**
- `backend/services/__init__.py`
- `backend/services/opportunity_aggregator.py` — merges `ProcessedLead` (cold) + `DirectLead` (direct) into a unified `Opportunity` shape, computes `$`-value estimate, sorts by score, filters
- `backend/routers/opportunities.py` — three endpoints: `GET /api/opportunities`, `GET /api/opportunities/{id}`, `PATCH /api/opportunities/{id}/stage`

**Modified backend files:**
- `backend/app.py:25,42` — register the new router
- `src/core/models.py` — add `Opportunity` and `Stage` enum + `OpportunityType` enum

**New backend tests:**
- `tests/backend/test_opportunity_aggregator.py`
- `tests/backend/test_opportunities_router.py`

**New frontend directories:**
- `frontend/src/design/` — tokens + primitives
- `frontend/src/components/shell/` — AppShell, Sidebar, TopBar
- `frontend/src/pages/inbox/` — Inbox page + sub-components
- `frontend/src/types/` — TS types

**New frontend files:**
- `frontend/src/design/primitives/Button.tsx`
- `frontend/src/design/primitives/Card.tsx`
- `frontend/src/design/primitives/Pill.tsx`
- `frontend/src/design/primitives/StatusDot.tsx`
- `frontend/src/design/primitives/KbdHint.tsx`
- `frontend/src/design/primitives/MoneyValue.tsx`
- `frontend/src/design/primitives/Sparkline.tsx`
- `frontend/src/design/primitives/index.ts` — barrel export
- `frontend/src/components/shell/AppShell.tsx`
- `frontend/src/components/shell/Sidebar.tsx`
- `frontend/src/components/shell/TopBar.tsx`
- `frontend/src/api/opportunities.ts` — react-query hooks
- `frontend/src/types/opportunity.ts` — TS types matching backend
- `frontend/src/pages/inbox/InboxPage.tsx`
- `frontend/src/pages/inbox/FilterPanel.tsx`
- `frontend/src/pages/inbox/OpportunityList.tsx`
- `frontend/src/pages/inbox/OpportunityListItem.tsx`
- `frontend/src/pages/inbox/OpportunityDetail.tsx`
- `frontend/src/pages/PlaceholderPage.tsx` — used for routes not yet built (Hub, Pipeline, Sources, Outreach, Templates)

**Modified frontend files:**
- `frontend/src/index.css` — full replacement with new dark theme + Geist font import
- `frontend/src/App.tsx` — add new routes alongside old ones
- `frontend/package.json` — add `geist` package

**Untouched (preserved):**
- `frontend/src/pages/cold/**`, `frontend/src/pages/direct/**` — old pages still mounted at `/cold/*`, `/direct/*`
- `frontend/src/layouts/AppLayout.tsx` — old shell, still used by old routes
- `backend/routers/cold_outreach.py`, `backend/routers/direct_leads.py`, `backend/scheduler.py` — unchanged
- `src/cold_outreach/**`, `src/direct_leads/**`, `src/core/storage.py` — pipelines unchanged

---

## Conventions

- **Money formatting:** US dollar with no decimal for whole values (`$1,400`), one decimal for thousands at scale (`$47.2K` only on Hub hero — Inbox always shows full).
- **Stage enum (string-equal across backend/frontend):** `new`, `researching`, `contacted`, `replied`, `meeting`, `won`, `lost`. These map 1:1 to `outreach_status` values already in storage (`storage.py:ALLOWED_STATUS`); we add `researching`, `lost` and treat `passed` → `lost`, `converted` → `won`, `queued` → `new`.
- **Opportunity type enum:** `direct` (job/gig from Reddit/LinkedIn/Indeed/Twitter/Clutch/GoodFirms) or `cold` (local business prospect from Google Maps/Yelp/BBB/YellowPages/Manta).
- **All new commits use Conventional Commits:** `feat:`, `fix:`, `chore:`, `test:`, `style:`.

---

## Pre-flight

- [ ] **Step 0.1: Confirm dev environment is running**

Run from repo root:
```powershell
.venv\Scripts\python.exe -c "from backend.app import app; print('backend OK')"
cd frontend; npm run dev
```
Expected: backend imports clean; vite serves on `http://localhost:5173`.

- [ ] **Step 0.2: Create a branch for the work**

```bash
git checkout -b pulse-foundation
git status
```
Expected: clean working tree on new branch.

---

## Task 1: Backend — `Opportunity` model + `Stage` enum

**Why:** A single shape both pipelines collapse into. Frontend talks to one type.

**Files:**
- Modify: `src/core/models.py` (append at end)

- [ ] **Step 1.1: Read the bottom of `src/core/models.py` to find insertion point**

Run:
```bash
wc -l src/core/models.py
```
Expected: line count, e.g. 248. We'll append after the last line.

- [ ] **Step 1.2: Append `Opportunity`, `Stage`, `OpportunityType`**

Add to bottom of `src/core/models.py`:

```python


# ---------------------------------------------------------------------------
# Opportunity (unified shape for the Pulse UI)
# ---------------------------------------------------------------------------

from enum import Enum


class Stage(str, Enum):
    NEW = "new"
    RESEARCHING = "researching"
    CONTACTED = "contacted"
    REPLIED = "replied"
    MEETING = "meeting"
    WON = "won"
    LOST = "lost"


class OpportunityType(str, Enum):
    DIRECT = "direct"  # job/gig from Reddit/LinkedIn/Indeed/Twitter/Clutch/GoodFirms
    COLD = "cold"      # local business prospect from Google Maps/Yelp/BBB/YellowPages/Manta


@dataclass
class Opportunity:
    """Unified opportunity used by the new Pulse UI. Read-only projection
    over ProcessedLead (cold) and DirectLead (direct)."""

    id: str
    type: str          # OpportunityType value
    source: str        # "reddit" | "linkedin" | "google_maps" | ...
    title: str
    description: str
    url: str
    posted_date: Optional[str] = None  # ISO date string
    company_name: str = ""
    location: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    score: int = 0                  # 0-100, normalized
    priority: str = "cold"          # "hot" | "warm" | "cold"
    stage: str = Stage.NEW.value
    estimated_value_usd: int = 0    # heuristic dollar estimate
    matched_skills: List[str] = field(default_factory=list)
    budget_signal: str = ""
    urgency_signal: str = ""
    pain_tags: List[str] = field(default_factory=list)
    notes: str = ""
    source_file: str = ""           # which Excel file this came from (for write-back)
    raw_lead_id: str = ""           # original Lead_ID in the source file
```

- [ ] **Step 1.3: Verify it imports cleanly**

```powershell
.venv\Scripts\python.exe -c "from src.core.models import Opportunity, Stage, OpportunityType; print(Stage.NEW.value, OpportunityType.DIRECT.value)"
```
Expected: `new direct`

- [ ] **Step 1.4: Commit**

```bash
git add src/core/models.py
git commit -m "feat(models): add Opportunity, Stage, OpportunityType for unified UI"
```

---

## Task 2: Backend — `OpportunityAggregator` service (TDD)

**Why:** This is the only place that knows how to convert cold leads and direct leads into the unified `Opportunity` shape, including the `$`-value heuristic. Tested in isolation.

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/opportunity_aggregator.py`
- Test: `tests/backend/test_opportunity_aggregator.py`

- [ ] **Step 2.1: Create empty package marker**

```bash
mkdir -p backend/services
echo "" > backend/services/__init__.py
```

- [ ] **Step 2.2: Write the failing test for `direct_lead_to_opportunity`**

Create `tests/backend/test_opportunity_aggregator.py`:

```python
"""Tests for backend.services.opportunity_aggregator."""
from __future__ import annotations

import pytest

from src.core.models import DirectLead, Stage, OpportunityType
from backend.services.opportunity_aggregator import (
    direct_lead_to_opportunity,
    cold_row_to_opportunity,
    estimate_value_usd,
)


def test_direct_lead_to_opportunity_minimal():
    lead = DirectLead(
        source="reddit",
        title="Need a Webflow dev",
        description="Build me a landing page",
        url="https://reddit.com/r/forhire/abc",
        company_name="Acme",
        location="Remote",
        contact_email="hi@acme.io",
        relevance_score=72,
        budget_signal="$3000",
        matched_skills=["webflow", "landing-page"],
        outreach_status="new",
    )
    opp = direct_lead_to_opportunity(lead, source_file="direct_x.xlsx")

    assert opp.type == OpportunityType.DIRECT.value
    assert opp.id == lead.lead_id
    assert opp.source == "reddit"
    assert opp.title == "Need a Webflow dev"
    assert opp.score == 72
    assert opp.priority == "hot"  # >= 60
    assert opp.stage == Stage.NEW.value
    assert opp.estimated_value_usd == 3000
    assert opp.matched_skills == ["webflow", "landing-page"]
    assert opp.source_file == "direct_x.xlsx"
    assert opp.raw_lead_id == lead.lead_id


def test_priority_thresholds():
    cold_lead = DirectLead(source="reddit", url="u1", relevance_score=20)
    warm_lead = DirectLead(source="reddit", url="u2", relevance_score=40)
    hot_lead = DirectLead(source="reddit", url="u3", relevance_score=80)
    assert direct_lead_to_opportunity(cold_lead, "f").priority == "cold"
    assert direct_lead_to_opportunity(warm_lead, "f").priority == "warm"
    assert direct_lead_to_opportunity(hot_lead, "f").priority == "hot"


def test_stage_normalization_from_legacy_status():
    """Old ProcessedLead used 'queued', 'passed', 'converted' — normalize them."""
    lead = DirectLead(source="reddit", url="u", outreach_status="passed")
    assert direct_lead_to_opportunity(lead, "f").stage == Stage.LOST.value

    lead = DirectLead(source="reddit", url="u", outreach_status="converted")
    assert direct_lead_to_opportunity(lead, "f").stage == Stage.WON.value

    lead = DirectLead(source="reddit", url="u", outreach_status="queued")
    assert direct_lead_to_opportunity(lead, "f").stage == Stage.NEW.value


def test_estimate_value_from_budget_signal_with_dollar_amount():
    assert estimate_value_usd(budget_signal="$3,000", source="reddit", priority="hot") == 3000
    assert estimate_value_usd(budget_signal="around $1500", source="reddit", priority="warm") == 1500
    assert estimate_value_usd(budget_signal="2000 USD", source="reddit", priority="hot") == 2000


def test_estimate_value_fallback_by_source_and_priority():
    # No explicit dollar amount → fall back to heuristic by source + priority
    # direct sources (reddit/linkedin/etc) baseline
    assert estimate_value_usd("", "reddit", "hot") == 2500
    assert estimate_value_usd("", "reddit", "warm") == 1500
    assert estimate_value_usd("", "reddit", "cold") == 800
    # cold sources (google_maps/yelp/etc) baseline (longer sales cycle, bigger deals)
    assert estimate_value_usd("", "google_maps", "hot") == 4000
    assert estimate_value_usd("", "google_maps", "warm") == 2000
    assert estimate_value_usd("", "google_maps", "cold") == 1000


def test_cold_row_to_opportunity_minimal():
    row = {
        "Lead_ID": "abc123",
        "Business_Name": "Joe's Plumbing",
        "Niche": "plumbing",
        "City": "Austin",
        "State": "TX",
        "Phone": "555-1234",
        "Website": "https://joesplumbing.com",
        "Email": "joe@joesplumbing.com",
        "Total_Score": 65,
        "Priority": "hot",
        "Pain_Tags_Str": "no_booking_cta, slow_page",
        "Outreach_Status": "contacted",
    }
    opp = cold_row_to_opportunity(row, source_file="cold_x.xlsx")

    assert opp.type == OpportunityType.COLD.value
    assert opp.id == "abc123"
    assert opp.title == "Joe's Plumbing"
    assert opp.location == "Austin, TX"
    assert opp.contact_email == "joe@joesplumbing.com"
    assert opp.contact_phone == "555-1234"
    assert opp.url == "https://joesplumbing.com"
    assert opp.score == 65
    assert opp.priority == "hot"
    assert opp.stage == Stage.CONTACTED.value
    assert opp.pain_tags == ["no_booking_cta", "slow_page"]
    assert opp.estimated_value_usd > 0  # heuristic — should set something
```

- [ ] **Step 2.3: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_opportunity_aggregator.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.services.opportunity_aggregator'`

- [ ] **Step 2.4: Implement the aggregator**

Create `backend/services/opportunity_aggregator.py`:

```python
"""Convert ProcessedLead (cold) and DirectLead (direct) rows into a unified
Opportunity shape for the Pulse UI."""
from __future__ import annotations

import re
from typing import Any

from src.core.models import DirectLead, Opportunity, Stage, OpportunityType


# Map legacy outreach_status values to canonical Stage values.
_STAGE_ALIASES: dict[str, str] = {
    "new": Stage.NEW.value,
    "queued": Stage.NEW.value,
    "researching": Stage.RESEARCHING.value,
    "contacted": Stage.CONTACTED.value,
    "replied": Stage.REPLIED.value,
    "meeting": Stage.MEETING.value,
    "won": Stage.WON.value,
    "converted": Stage.WON.value,
    "lost": Stage.LOST.value,
    "passed": Stage.LOST.value,
}


def _normalize_stage(raw: str | None) -> str:
    if not raw:
        return Stage.NEW.value
    return _STAGE_ALIASES.get(raw.lower().strip(), Stage.NEW.value)


def _priority_from_score(score: int) -> str:
    if score >= 60:
        return "hot"
    if score >= 35:
        return "warm"
    return "cold"


# Sources we consider "direct leads" (jobs/gigs) vs "cold prospects" (local biz).
# Used by estimate_value_usd as a baseline.
_DIRECT_SOURCES = {"reddit", "linkedin", "linkedin_posts", "indeed", "twitter", "clutch", "goodfirms", "tanit"}

# Baseline $ value when no budget signal is available.
_BASELINE_VALUE: dict[tuple[str, str], int] = {
    # (kind, priority): usd
    ("direct", "hot"): 2500,
    ("direct", "warm"): 1500,
    ("direct", "cold"): 800,
    ("cold", "hot"): 4000,
    ("cold", "warm"): 2000,
    ("cold", "cold"): 1000,
}


_DOLLAR_PATTERN = re.compile(
    r"(?:\$\s?|usd\s?|us\$\s?)?(\d{1,3}(?:[,.]?\d{3})*|\d+)\s?(?:k\b|usd\b|\$)?",
    re.IGNORECASE,
)


def estimate_value_usd(budget_signal: str, source: str, priority: str) -> int:
    """Best-effort dollar estimate for an opportunity.

    1. If `budget_signal` contains a recognizable dollar amount, parse it.
    2. Otherwise fall back to a baseline keyed by source-kind and priority.
    """
    if budget_signal:
        # Try to find the largest reasonable number in the string.
        candidates: list[int] = []
        for m in _DOLLAR_PATTERN.finditer(budget_signal):
            raw = m.group(1).replace(",", "").replace(".", "")
            try:
                n = int(raw)
            except ValueError:
                continue
            # Apply 'k' suffix if present
            tail = budget_signal[m.end(): m.end() + 2].lower()
            if tail.startswith("k"):
                n *= 1000
            if 100 <= n <= 500_000:
                candidates.append(n)
        if candidates:
            return max(candidates)

    kind = "direct" if source.lower() in _DIRECT_SOURCES else "cold"
    return _BASELINE_VALUE.get((kind, priority), 1000)


def direct_lead_to_opportunity(lead: DirectLead, source_file: str) -> Opportunity:
    """Convert a DirectLead dataclass into an Opportunity."""
    priority = _priority_from_score(lead.relevance_score)
    return Opportunity(
        id=lead.lead_id,
        type=OpportunityType.DIRECT.value,
        source=lead.source,
        title=lead.title,
        description=lead.description or "",
        url=lead.url,
        posted_date=lead.posted_date.isoformat() if lead.posted_date else None,
        company_name=lead.company_name or "",
        location=lead.location or "",
        contact_email=lead.contact_email or "",
        contact_phone=lead.contact_phone or "",
        score=int(lead.relevance_score or 0),
        priority=priority,
        stage=_normalize_stage(lead.outreach_status),
        estimated_value_usd=estimate_value_usd(lead.budget_signal, lead.source, priority),
        matched_skills=list(lead.matched_skills or []),
        budget_signal=lead.budget_signal or "",
        urgency_signal=lead.urgency_signal or "",
        pain_tags=[],
        notes=lead.notes or "",
        source_file=source_file,
        raw_lead_id=lead.lead_id,
    )


def cold_row_to_opportunity(row: dict[str, Any], source_file: str) -> Opportunity:
    """Convert a row dict (as read from the cold outreach Excel files) into an Opportunity."""
    score = int(row.get("Total_Score") or 0)
    priority = (row.get("Priority") or _priority_from_score(score)).lower()
    pain_tags_str = row.get("Pain_Tags_Str") or ""
    pain_tags = [t.strip() for t in pain_tags_str.split(",") if t.strip()]
    city = row.get("City") or ""
    state = row.get("State") or ""
    location = ", ".join(p for p in [city, state] if p)

    return Opportunity(
        id=str(row.get("Lead_ID") or ""),
        type=OpportunityType.COLD.value,
        source=row.get("Source") or "directory",
        title=row.get("Business_Name") or "",
        description=row.get("Offer_Reasoning") or "",
        url=row.get("Website") or "",
        posted_date=None,
        company_name=row.get("Business_Name") or "",
        location=location,
        contact_email=row.get("Email") or "",
        contact_phone=row.get("Phone") or "",
        score=score,
        priority=priority,
        stage=_normalize_stage(row.get("Outreach_Status")),
        estimated_value_usd=estimate_value_usd("", row.get("Source") or "google_maps", priority),
        matched_skills=[],
        budget_signal="",
        urgency_signal="",
        pain_tags=pain_tags,
        notes=row.get("Notes") or "",
        source_file=source_file,
        raw_lead_id=str(row.get("Lead_ID") or ""),
    )
```

- [ ] **Step 2.5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_opportunity_aggregator.py -v
```
Expected: 6 passed.

- [ ] **Step 2.6: Commit**

```bash
git add backend/services/__init__.py backend/services/opportunity_aggregator.py tests/backend/test_opportunity_aggregator.py
git commit -m "feat(services): add OpportunityAggregator with $ value heuristic"
```

---

## Task 3: Backend — `/api/opportunities` router (TDD)

**Why:** Single endpoint for the Inbox feed. Lists, filters, returns one. Patches the `stage` field (writes back to the Excel store via `update_lead`).

**Files:**
- Create: `backend/routers/opportunities.py`
- Modify: `backend/app.py`
- Test: `tests/backend/test_opportunities_router.py`

- [ ] **Step 3.1: Write the failing test for the list endpoint**

Create `tests/backend/test_opportunities_router.py`:

```python
"""Tests for backend.routers.opportunities."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_opportunities_returns_envelope(client):
    """Endpoint always returns {opportunities, total, filters_applied}."""
    res = client.get("/api/opportunities")
    assert res.status_code == 200
    body = res.json()
    assert "opportunities" in body
    assert "total" in body
    assert isinstance(body["opportunities"], list)


def test_list_opportunities_supports_type_filter(client):
    res = client.get("/api/opportunities?type=direct")
    assert res.status_code == 200
    for opp in res.json()["opportunities"]:
        assert opp["type"] == "direct"

    res = client.get("/api/opportunities?type=cold")
    assert res.status_code == 200
    for opp in res.json()["opportunities"]:
        assert opp["type"] == "cold"


def test_list_opportunities_supports_priority_filter(client):
    res = client.get("/api/opportunities?priority=hot")
    assert res.status_code == 200
    for opp in res.json()["opportunities"]:
        assert opp["priority"] == "hot"


def test_list_opportunities_supports_search(client):
    """Search matches title, company_name, source, location case-insensitively."""
    res = client.get("/api/opportunities?q=webflow")
    assert res.status_code == 200
    # Don't assert results exist (depends on test data) — only that the call succeeds.


def test_list_opportunities_default_sort_is_score_desc(client):
    res = client.get("/api/opportunities?limit=10")
    body = res.json()
    opps = body["opportunities"]
    if len(opps) >= 2:
        for a, b in zip(opps, opps[1:]):
            assert a["score"] >= b["score"]


def test_get_single_opportunity_404_for_unknown(client):
    res = client.get("/api/opportunities/__no_such_id__")
    assert res.status_code == 404


def test_patch_stage_validates_enum(client):
    res = client.patch("/api/opportunities/__some_id__/stage", json={"stage": "made_up_stage"})
    assert res.status_code == 422  # pydantic validation error
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_opportunities_router.py -v
```
Expected: FAIL — likely 404 on every endpoint because the router isn't registered yet.

- [ ] **Step 3.3: Implement the router**

Create `backend/routers/opportunities.py`:

```python
"""Unified opportunities router — read-aggregator across cold + direct stores."""
from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.core.storage import list_files, read_leads, update_lead
from src.core.models import DirectLead, Stage
from backend.services.opportunity_aggregator import (
    cold_row_to_opportunity,
    direct_lead_to_opportunity,
)

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


class StagePatch(BaseModel):
    stage: Stage


def _load_all_opportunities() -> list[dict]:
    """Read every cold + direct + legacy file and project to Opportunity dicts."""
    out: list[dict] = []

    # Cold (and legacy) files — rows are dicts already.
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

    # Direct files — rows are dicts mapped from DirectLead columns.
    for f in list_files("direct"):
        try:
            _, rows = read_leads(f["name"], "direct")
        except Exception:
            continue
        for row in rows:
            # Re-hydrate enough of a DirectLead to reuse the converter.
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
                matched_skills=[
                    s.strip()
                    for s in (row.get("Matched_Skills") or "").split(",")
                    if s.strip()
                ],
                outreach_status=row.get("Outreach_Status") or "new",
                notes=row.get("Notes") or "",
            )
            # DirectLead.__post_init__ recomputes lead_id from source|url; if we
            # have an explicit Lead_ID in the row, prefer it (handles legacy data).
            if row.get("Lead_ID"):
                lead.lead_id = str(row["Lead_ID"])
            opp = direct_lead_to_opportunity(lead, source_file=f["name"])
            if opp.id:
                out.append(asdict(opp))

    return out


@router.get("")
async def list_opportunities(
    type: Optional[str] = Query(None, regex="^(direct|cold)$"),
    priority: Optional[str] = Query(None, regex="^(hot|warm|cold)$"),
    stage: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    sort: str = Query("score", regex="^(score|value|recent)$"),
    limit: int = Query(200, ge=1, le=2000),
):
    items = _load_all_opportunities()

    # Filter
    if type:
        items = [o for o in items if o["type"] == type]
    if priority:
        items = [o for o in items if o["priority"] == priority]
    if stage:
        items = [o for o in items if o["stage"] == stage]
    if source:
        items = [o for o in items if o["source"] == source]
    if q:
        ql = q.lower()
        items = [
            o
            for o in items
            if ql in (o["title"] or "").lower()
            or ql in (o["company_name"] or "").lower()
            or ql in (o["source"] or "").lower()
            or ql in (o["location"] or "").lower()
            or ql in (o["description"] or "").lower()
        ]

    # Sort
    if sort == "score":
        items.sort(key=lambda o: o["score"], reverse=True)
    elif sort == "value":
        items.sort(key=lambda o: o["estimated_value_usd"], reverse=True)
    elif sort == "recent":
        items.sort(key=lambda o: o["posted_date"] or "", reverse=True)

    total = len(items)
    items = items[:limit]
    return {"opportunities": items, "total": total}


@router.get("/{opp_id}")
async def get_opportunity(opp_id: str):
    for opp in _load_all_opportunities():
        if opp["id"] == opp_id:
            return opp
    raise HTTPException(status_code=404, detail="Opportunity not found")


@router.patch("/{opp_id}/stage")
async def update_opportunity_stage(opp_id: str, patch: StagePatch):
    """Persist stage change to the underlying Excel file via storage.update_lead.

    storage.update_lead writes to the `Outreach_Status` column."""
    for opp in _load_all_opportunities():
        if opp["id"] != opp_id:
            continue
        section = "cold" if opp["type"] == "cold" else "direct"
        try:
            update_lead(
                opp["source_file"],
                opp["raw_lead_id"],
                {"Outreach_Status": patch.stage.value},
                section,
            )
        except (KeyError, FileNotFoundError) as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"ok": True, "id": opp_id, "stage": patch.stage.value}
    raise HTTPException(status_code=404, detail="Opportunity not found")
```

- [ ] **Step 3.4: Register the router**

Edit `backend/app.py`. Replace line 25:

```python
from backend.routers import cold_outreach, direct_leads, shared
```

with:

```python
from backend.routers import cold_outreach, direct_leads, opportunities, shared
```

And after line 44 (`app.include_router(shared.router)`), add:

```python
app.include_router(opportunities.router)
```

- [ ] **Step 3.5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/backend/test_opportunities_router.py -v
```
Expected: 7 passed.

- [ ] **Step 3.6: Manual smoke test**

Restart backend and curl the new endpoint:
```powershell
# In a separate terminal: python run_server.py
curl http://localhost:8000/api/opportunities?limit=3
```
Expected: JSON envelope with `opportunities`, `total`. If you have any leads in `output/`, you'll see them in the unified shape.

- [ ] **Step 3.7: Commit**

```bash
git add backend/routers/opportunities.py backend/app.py tests/backend/test_opportunities_router.py
git commit -m "feat(api): add /api/opportunities unified endpoint with filter/sort/patch"
```

---

## Task 4: Frontend — install Geist + replace `index.css` with dark Pulse theme

**Files:**
- Modify: `frontend/package.json` (add `geist`)
- Modify: `frontend/src/index.css` (full replacement)

- [ ] **Step 4.1: Install Geist**

```powershell
cd frontend
npm install geist
```
Expected: `geist@^1.x.x` added to dependencies.

- [ ] **Step 4.2: Replace `frontend/src/index.css` with the dark Pulse theme**

Full replacement:

```css
@import "tailwindcss";
@import "geist/font/sans";
@import "geist/font/mono";

@theme {
  /* Pulse — dark operator palette */
  --color-bg: #0A0A0B;
  --color-surface: #131316;
  --color-surface-raised: #1A1A1F;
  --color-surface-hover: #1F1F25;

  --color-border: #26262C;
  --color-border-strong: #3A3A42;

  /* Volt accent — only for money, wins, primary CTAs */
  --color-accent: #C7F950;
  --color-accent-hover: #B4F03A;
  --color-accent-soft: rgba(199, 249, 80, 0.12);

  /* Semantic */
  --color-hot: #FF5C5C;
  --color-hot-soft: rgba(255, 92, 92, 0.12);
  --color-warm: #FFB627;
  --color-warm-soft: rgba(255, 182, 39, 0.12);
  --color-cool: #4DA8FF;
  --color-cool-soft: rgba(77, 168, 255, 0.12);

  /* Text */
  --color-text-primary: #F4F4F5;
  --color-text-secondary: #9CA3AF;
  --color-text-tertiary: #52525B;
  --color-text-quaternary: #3F3F46;

  /* Typography */
  --font-sans: "Geist", system-ui, -apple-system, sans-serif;
  --font-mono: "Geist Mono", "SF Mono", Menlo, monospace;

  /* Radii */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
}

* {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

html, body, #root {
  height: 100%;
  background-color: var(--color-bg);
  color: var(--color-text-primary);
}

body {
  font-family: var(--font-sans);
  font-feature-settings: "cv11", "ss01", "ss03";
}

/* Tabular numbers everywhere a number/$ appears */
.tabular-nums {
  font-variant-numeric: tabular-nums;
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover { background: var(--color-text-tertiary); }

/* Focus */
*:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* Selection */
::selection {
  background-color: var(--color-accent-soft);
  color: var(--color-accent);
}

/* Pulse animation for live status dots */
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.5; transform: scale(0.85); }
}
.animate-pulse-dot {
  animation: pulse-dot 2s cubic-bezier(0.16, 1, 0.3, 1) infinite;
}
```

- [ ] **Step 4.3: Verify the theme loads in the browser**

Reload the dev server at `http://localhost:5173`. Expected: existing `/cold/*` pages now have a dark background, Geist font, and probably look broken (because they were styled for the light theme). **This is intentional** — they're being deprecated. The new pages will look right.

- [ ] **Step 4.4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/index.css
git commit -m "feat(design): install Geist + Pulse dark theme tokens"
```

---

## Task 5: Frontend — design primitives

Build the small set of reusable primitives. Each is < 60 lines, no internal state, fully styled with the new tokens.

**Files (all created):**
- `frontend/src/design/primitives/Button.tsx`
- `frontend/src/design/primitives/Card.tsx`
- `frontend/src/design/primitives/Pill.tsx`
- `frontend/src/design/primitives/StatusDot.tsx`
- `frontend/src/design/primitives/KbdHint.tsx`
- `frontend/src/design/primitives/MoneyValue.tsx`
- `frontend/src/design/primitives/Sparkline.tsx`
- `frontend/src/design/primitives/index.ts`

- [ ] **Step 5.1: Create `Button.tsx`**

```tsx
import { ButtonHTMLAttributes, forwardRef } from "react";
import clsx from "clsx";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variantClass: Record<Variant, string> = {
  primary:
    "bg-[--color-accent] text-[#0A0A0B] hover:bg-[--color-accent-hover] font-medium",
  secondary:
    "bg-[--color-surface-raised] text-[--color-text-primary] hover:bg-[--color-surface-hover] border border-[--color-border]",
  ghost:
    "bg-transparent text-[--color-text-secondary] hover:bg-[--color-surface-raised] hover:text-[--color-text-primary]",
  danger:
    "bg-[--color-hot-soft] text-[--color-hot] hover:bg-[--color-hot] hover:text-white",
};

const sizeClass: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs rounded-[--radius-sm]",
  md: "h-9 px-3.5 text-sm rounded-[--radius-md]",
  lg: "h-11 px-5 text-sm rounded-[--radius-md]",
};

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = "secondary", size = "md", className, ...rest }, ref) => (
    <button
      ref={ref}
      className={clsx(
        "inline-flex items-center justify-center gap-1.5 transition-colors duration-150 disabled:opacity-50 disabled:pointer-events-none",
        variantClass[variant],
        sizeClass[size],
        className,
      )}
      {...rest}
    />
  ),
);
Button.displayName = "Button";
```

- [ ] **Step 5.2: Create `Card.tsx`**

```tsx
import { HTMLAttributes } from "react";
import clsx from "clsx";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "bg-[--color-surface] border border-[--color-border] rounded-[--radius-lg]",
        className,
      )}
      {...rest}
    />
  );
}
```

- [ ] **Step 5.3: Create `Pill.tsx`**

```tsx
import { HTMLAttributes } from "react";
import clsx from "clsx";

type Tone = "neutral" | "hot" | "warm" | "cool" | "accent";

interface Props extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

const toneClass: Record<Tone, string> = {
  neutral:
    "bg-[--color-surface-raised] text-[--color-text-secondary] border border-[--color-border]",
  hot: "bg-[--color-hot-soft] text-[--color-hot]",
  warm: "bg-[--color-warm-soft] text-[--color-warm]",
  cool: "bg-[--color-cool-soft] text-[--color-cool]",
  accent: "bg-[--color-accent-soft] text-[--color-accent]",
};

export function Pill({ tone = "neutral", className, ...rest }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 text-[11px] font-medium rounded-[--radius-sm] tabular-nums",
        toneClass[tone],
        className,
      )}
      {...rest}
    />
  );
}
```

- [ ] **Step 5.4: Create `StatusDot.tsx`**

```tsx
import clsx from "clsx";

type Status = "live" | "idle" | "error" | "hot" | "warm" | "cold";

interface Props {
  status: Status;
  className?: string;
}

const colorClass: Record<Status, string> = {
  live: "bg-[--color-accent]",
  idle: "bg-[--color-text-tertiary]",
  error: "bg-[--color-hot]",
  hot: "bg-[--color-hot]",
  warm: "bg-[--color-warm]",
  cold: "bg-[--color-cool]",
};

export function StatusDot({ status, className }: Props) {
  const animate = status === "live" || status === "hot";
  return (
    <span
      className={clsx(
        "inline-block w-1.5 h-1.5 rounded-full",
        colorClass[status],
        animate && "animate-pulse-dot",
        className,
      )}
    />
  );
}
```

- [ ] **Step 5.5: Create `KbdHint.tsx`**

```tsx
import { HTMLAttributes } from "react";
import clsx from "clsx";

export function KbdHint({ className, children, ...rest }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <kbd
      className={clsx(
        "inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-mono",
        "bg-[--color-surface-raised] text-[--color-text-tertiary]",
        "border border-[--color-border] rounded-[4px]",
        className,
      )}
      {...rest}
    >
      {children}
    </kbd>
  );
}
```

- [ ] **Step 5.6: Create `MoneyValue.tsx`**

```tsx
import clsx from "clsx";

interface Props {
  usd: number;
  size?: "sm" | "md" | "lg" | "xl";
  tone?: "default" | "accent" | "muted";
  abbreviate?: boolean;
  className?: string;
}

const sizeClass: Record<NonNullable<Props["size"]>, string> = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-lg",
  xl: "text-3xl",
};

const toneClass: Record<NonNullable<Props["tone"]>, string> = {
  default: "text-[--color-text-primary]",
  accent: "text-[--color-accent]",
  muted: "text-[--color-text-secondary]",
};

function format(usd: number, abbreviate: boolean): string {
  if (abbreviate && usd >= 10_000) {
    return `$${(usd / 1000).toFixed(usd >= 100_000 ? 0 : 1)}K`;
  }
  return `$${usd.toLocaleString("en-US")}`;
}

export function MoneyValue({
  usd,
  size = "md",
  tone = "default",
  abbreviate = false,
  className,
}: Props) {
  return (
    <span
      className={clsx(
        "font-mono tabular-nums font-medium",
        sizeClass[size],
        toneClass[tone],
        className,
      )}
    >
      {format(usd, abbreviate)}
    </span>
  );
}
```

- [ ] **Step 5.7: Create `Sparkline.tsx` (no deps — simple SVG)**

```tsx
interface Props {
  data: number[];
  width?: number;
  height?: number;
  stroke?: string;
  className?: string;
}

export function Sparkline({
  data,
  width = 80,
  height = 22,
  stroke = "var(--color-accent)",
  className,
}: Props) {
  if (data.length < 2) return <svg width={width} height={height} className={className} />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1);
  const points = data
    .map((v, i) => `${i * stepX},${height - ((v - min) / range) * height}`)
    .join(" ");
  return (
    <svg width={width} height={height} className={className} aria-hidden>
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}
```

- [ ] **Step 5.8: Create barrel `index.ts`**

```ts
export { Button } from "./Button";
export { Card } from "./Card";
export { Pill } from "./Pill";
export { StatusDot } from "./StatusDot";
export { KbdHint } from "./KbdHint";
export { MoneyValue } from "./MoneyValue";
export { Sparkline } from "./Sparkline";
```

- [ ] **Step 5.9: Verify build**

```powershell
cd frontend
npm run build
```
Expected: `vite build` succeeds. Type errors here will be from primitives — fix them inline before committing.

- [ ] **Step 5.10: Commit**

```bash
git add frontend/src/design
git commit -m "feat(design): add Button, Card, Pill, StatusDot, KbdHint, MoneyValue, Sparkline primitives"
```

---

## Task 6: Frontend — `AppShell`, `Sidebar`, `TopBar`

**Why:** The new chrome that wraps every Pulse page. No top section toggle. Sidebar lists all 7 sections. TopBar has a global search trigger (⌘K hint, no functionality yet — that ships in Plan 2).

**Files:**
- Create: `frontend/src/components/shell/Sidebar.tsx`
- Create: `frontend/src/components/shell/TopBar.tsx`
- Create: `frontend/src/components/shell/AppShell.tsx`

- [ ] **Step 6.1: Create `Sidebar.tsx`**

```tsx
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Inbox,
  Columns3,
  Radio,
  Send,
  FileText,
  Settings,
} from "lucide-react";
import clsx from "clsx";

const NAV = [
  { to: "/hub", label: "Hub", icon: LayoutDashboard },
  { to: "/inbox", label: "Inbox", icon: Inbox },
  { to: "/pipeline", label: "Pipeline", icon: Columns3 },
  { to: "/sources", label: "Sources", icon: Radio },
  { to: "/outreach", label: "Outreach", icon: Send },
  { to: "/templates", label: "Templates", icon: FileText },
];

export function Sidebar() {
  return (
    <aside className="w-[200px] shrink-0 bg-[--color-surface] border-r border-[--color-border] flex flex-col">
      <div className="px-4 py-4 flex items-center gap-2">
        <div className="w-6 h-6 rounded-md bg-[--color-accent] flex items-center justify-center">
          <span className="text-[10px] font-bold text-[#0A0A0B]">P</span>
        </div>
        <span className="font-semibold tracking-tight text-[--color-text-primary]">
          PULSE
        </span>
      </div>

      <nav className="flex-1 px-2 py-2 flex flex-col gap-0.5">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-2.5 px-2.5 h-8 text-[13px] rounded-[--radius-sm] transition-colors",
                isActive
                  ? "bg-[--color-accent-soft] text-[--color-accent]"
                  : "text-[--color-text-secondary] hover:bg-[--color-surface-raised] hover:text-[--color-text-primary]",
              )
            }
          >
            <Icon className="w-3.5 h-3.5" strokeWidth={1.75} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="px-2 py-2 border-t border-[--color-border]">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-2.5 px-2.5 h-8 text-[13px] rounded-[--radius-sm] transition-colors",
              isActive
                ? "bg-[--color-accent-soft] text-[--color-accent]"
                : "text-[--color-text-secondary] hover:bg-[--color-surface-raised] hover:text-[--color-text-primary]",
            )
          }
        >
          <Settings className="w-3.5 h-3.5" strokeWidth={1.75} />
          <span>Settings</span>
        </NavLink>
      </div>
    </aside>
  );
}
```

- [ ] **Step 6.2: Create `TopBar.tsx`**

```tsx
import { Search } from "lucide-react";
import { KbdHint } from "../../design/primitives";

export function TopBar() {
  return (
    <header className="h-11 shrink-0 border-b border-[--color-border] flex items-center px-4 gap-3 bg-[--color-bg]">
      <button
        type="button"
        className="flex-1 max-w-[480px] h-7 flex items-center gap-2 px-2.5 rounded-[--radius-sm] bg-[--color-surface-raised] border border-[--color-border] text-[--color-text-tertiary] hover:border-[--color-border-strong] transition-colors"
        // ⌘K opens command palette in a later plan; for now this is a no-op visual.
      >
        <Search className="w-3.5 h-3.5" strokeWidth={1.75} />
        <span className="text-[12px]">Search opportunities, sources, commands…</span>
        <span className="ml-auto flex items-center gap-1">
          <KbdHint>⌘</KbdHint>
          <KbdHint>K</KbdHint>
        </span>
      </button>
      <div className="ml-auto text-[12px] text-[--color-text-tertiary]">
        Aether Agency
      </div>
    </header>
  );
}
```

- [ ] **Step 6.3: Create `AppShell.tsx`**

```tsx
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell() {
  return (
    <div className="flex h-screen bg-[--color-bg] text-[--color-text-primary]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
        {/* Pulse Bar mounts here in Plan 2 */}
      </div>
    </div>
  );
}
```

- [ ] **Step 6.4: Commit**

```bash
git add frontend/src/components/shell
git commit -m "feat(shell): add Pulse AppShell, Sidebar, TopBar"
```

---

## Task 7: Frontend — TS types + react-query hooks

**Files:**
- Create: `frontend/src/types/opportunity.ts`
- Create: `frontend/src/api/opportunities.ts`

- [ ] **Step 7.1: Create the TS types**

`frontend/src/types/opportunity.ts`:

```ts
export type Stage =
  | "new"
  | "researching"
  | "contacted"
  | "replied"
  | "meeting"
  | "won"
  | "lost";

export type OpportunityType = "direct" | "cold";
export type Priority = "hot" | "warm" | "cold";

export interface Opportunity {
  id: string;
  type: OpportunityType;
  source: string;
  title: string;
  description: string;
  url: string;
  posted_date: string | null;
  company_name: string;
  location: string;
  contact_email: string;
  contact_phone: string;
  score: number;
  priority: Priority;
  stage: Stage;
  estimated_value_usd: number;
  matched_skills: string[];
  budget_signal: string;
  urgency_signal: string;
  pain_tags: string[];
  notes: string;
  source_file: string;
  raw_lead_id: string;
}

export interface OpportunityListResponse {
  opportunities: Opportunity[];
  total: number;
}

export interface OpportunityFilters {
  type?: OpportunityType;
  priority?: Priority;
  stage?: Stage;
  source?: string;
  q?: string;
  sort?: "score" | "value" | "recent";
  limit?: number;
}
```

- [ ] **Step 7.2: Create the react-query hooks**

`frontend/src/api/opportunities.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  Opportunity,
  OpportunityFilters,
  OpportunityListResponse,
  Stage,
} from "../types/opportunity";

function toQS(filters: OpportunityFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const s = params.toString();
  return s ? `?${s}` : "";
}

export function useOpportunities(filters: OpportunityFilters = {}) {
  return useQuery<OpportunityListResponse>({
    queryKey: ["opportunities", filters],
    queryFn: () => apiFetch(`/opportunities${toQS(filters)}`),
    staleTime: 15_000,
  });
}

export function useOpportunity(id: string | null) {
  return useQuery<Opportunity>({
    queryKey: ["opportunity", id],
    queryFn: () => apiFetch(`/opportunities/${id}`),
    enabled: !!id,
  });
}

export function useUpdateStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: Stage }) =>
      apiFetch(`/opportunities/${id}/stage`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage }),
      }),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["opportunity", id] });
    },
  });
}
```

- [ ] **Step 7.3: Commit**

```bash
git add frontend/src/types/opportunity.ts frontend/src/api/opportunities.ts
git commit -m "feat(api): add Opportunity types + react-query hooks"
```

---

## Task 8: Frontend — `OpportunityListItem` component

**File:** `frontend/src/pages/inbox/OpportunityListItem.tsx`

- [ ] **Step 8.1: Create the component**

```tsx
import clsx from "clsx";
import { Opportunity } from "../../types/opportunity";
import { StatusDot, Pill, MoneyValue } from "../../design/primitives";

interface Props {
  opp: Opportunity;
  active: boolean;
  onClick: () => void;
}

function formatAge(iso: string | null): string {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export function OpportunityListItem({ opp, active, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "w-full text-left px-3 py-2.5 border-b border-[--color-border]",
        "transition-colors flex flex-col gap-1.5",
        active
          ? "bg-[--color-surface-raised]"
          : "hover:bg-[--color-surface]",
      )}
    >
      <div className="flex items-center gap-2 min-w-0">
        <StatusDot status={opp.priority === "hot" ? "hot" : opp.priority === "warm" ? "warm" : "cold"} />
        <span className="text-[13px] font-medium text-[--color-text-primary] truncate flex-1">
          {opp.title || "(no title)"}
        </span>
        <MoneyValue
          usd={opp.estimated_value_usd}
          size="sm"
          tone="accent"
        />
      </div>
      <div className="flex items-center gap-1.5 text-[11px] text-[--color-text-tertiary]">
        <Pill tone="neutral">{opp.source}</Pill>
        {opp.location && <span className="truncate">{opp.location}</span>}
        <span className="ml-auto tabular-nums">{formatAge(opp.posted_date)}</span>
      </div>
    </button>
  );
}
```

- [ ] **Step 8.2: Commit**

```bash
git add frontend/src/pages/inbox/OpportunityListItem.tsx
git commit -m "feat(inbox): add OpportunityListItem"
```

---

## Task 9: Frontend — `FilterPanel` component

**File:** `frontend/src/pages/inbox/FilterPanel.tsx`

- [ ] **Step 9.1: Create the component**

```tsx
import clsx from "clsx";
import type { OpportunityFilters, Priority, OpportunityType } from "../../types/opportunity";

interface Props {
  value: OpportunityFilters;
  onChange: (next: OpportunityFilters) => void;
  totalsByPriority: Record<Priority | "all", number>;
  totalsByType: Record<OpportunityType | "all", number>;
}

function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-wider text-[--color-text-tertiary] font-medium">
        {label}
      </span>
      {children}
    </div>
  );
}

function FilterPill({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count?: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "w-full flex items-center justify-between px-2.5 h-7 rounded-[--radius-sm] text-[12px] transition-colors",
        active
          ? "bg-[--color-accent-soft] text-[--color-accent]"
          : "text-[--color-text-secondary] hover:bg-[--color-surface-raised]",
      )}
    >
      <span>{label}</span>
      {count !== undefined && (
        <span className="text-[11px] tabular-nums opacity-70">{count}</span>
      )}
    </button>
  );
}

export function FilterPanel({ value, onChange, totalsByPriority, totalsByType }: Props) {
  return (
    <div className="w-[200px] shrink-0 bg-[--color-surface] border-r border-[--color-border] p-3 flex flex-col gap-4 overflow-auto">
      <FilterRow label="Type">
        <FilterPill
          label="All"
          count={totalsByType.all}
          active={!value.type}
          onClick={() => onChange({ ...value, type: undefined })}
        />
        <FilterPill
          label="Direct (jobs)"
          count={totalsByType.direct}
          active={value.type === "direct"}
          onClick={() => onChange({ ...value, type: "direct" })}
        />
        <FilterPill
          label="Cold (prospects)"
          count={totalsByType.cold}
          active={value.type === "cold"}
          onClick={() => onChange({ ...value, type: "cold" })}
        />
      </FilterRow>

      <FilterRow label="Priority">
        <FilterPill
          label="All"
          count={totalsByPriority.all}
          active={!value.priority}
          onClick={() => onChange({ ...value, priority: undefined })}
        />
        <FilterPill
          label="Hot"
          count={totalsByPriority.hot}
          active={value.priority === "hot"}
          onClick={() => onChange({ ...value, priority: "hot" })}
        />
        <FilterPill
          label="Warm"
          count={totalsByPriority.warm}
          active={value.priority === "warm"}
          onClick={() => onChange({ ...value, priority: "warm" })}
        />
        <FilterPill
          label="Cold"
          count={totalsByPriority.cold}
          active={value.priority === "cold"}
          onClick={() => onChange({ ...value, priority: "cold" })}
        />
      </FilterRow>

      <FilterRow label="Sort by">
        <FilterPill
          label="Score"
          active={!value.sort || value.sort === "score"}
          onClick={() => onChange({ ...value, sort: "score" })}
        />
        <FilterPill
          label="Value"
          active={value.sort === "value"}
          onClick={() => onChange({ ...value, sort: "value" })}
        />
        <FilterPill
          label="Recent"
          active={value.sort === "recent"}
          onClick={() => onChange({ ...value, sort: "recent" })}
        />
      </FilterRow>
    </div>
  );
}
```

- [ ] **Step 9.2: Commit**

```bash
git add frontend/src/pages/inbox/FilterPanel.tsx
git commit -m "feat(inbox): add FilterPanel"
```

---

## Task 10: Frontend — `OpportunityDetail` component

**File:** `frontend/src/pages/inbox/OpportunityDetail.tsx`

- [ ] **Step 10.1: Create the component**

```tsx
import { ExternalLink, Mail, Phone, MapPin, Calendar } from "lucide-react";
import { Opportunity, Stage } from "../../types/opportunity";
import { Button, Pill, MoneyValue, StatusDot, Card } from "../../design/primitives";
import { useUpdateStage } from "../../api/opportunities";

const STAGES: Stage[] = ["new", "researching", "contacted", "replied", "meeting", "won", "lost"];

interface Props {
  opp: Opportunity;
}

export function OpportunityDetail({ opp }: Props) {
  const updateStage = useUpdateStage();

  return (
    <div className="flex-1 overflow-auto p-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <StatusDot
            status={opp.priority === "hot" ? "hot" : opp.priority === "warm" ? "warm" : "cold"}
            className="mt-2"
          />
          <h1 className="text-xl font-semibold text-[--color-text-primary] leading-tight flex-1">
            {opp.title || "(no title)"}
          </h1>
          <MoneyValue usd={opp.estimated_value_usd} size="xl" tone="accent" />
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[12px] text-[--color-text-secondary]">
          <Pill tone="neutral">{opp.source}</Pill>
          {opp.company_name && <span>{opp.company_name}</span>}
          {opp.location && (
            <span className="flex items-center gap-1">
              <MapPin className="w-3 h-3" /> {opp.location}
            </span>
          )}
          {opp.posted_date && (
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {new Date(opp.posted_date).toLocaleDateString()}
            </span>
          )}
          {opp.url && (
            <a
              href={opp.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-[--color-accent] hover:underline"
            >
              Open original <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>

      {/* Stage selector */}
      <Card className="p-3">
        <div className="text-[10px] uppercase tracking-wider text-[--color-text-tertiary] font-medium mb-2">
          Stage
        </div>
        <div className="flex flex-wrap gap-1">
          {STAGES.map((s) => (
            <button
              key={s}
              type="button"
              disabled={updateStage.isPending}
              onClick={() => updateStage.mutate({ id: opp.id, stage: s })}
              className={
                opp.stage === s
                  ? "px-2.5 h-7 text-[12px] rounded-[--radius-sm] bg-[--color-accent] text-[#0A0A0B] font-medium"
                  : "px-2.5 h-7 text-[12px] rounded-[--radius-sm] text-[--color-text-secondary] hover:bg-[--color-surface-raised]"
              }
            >
              {s}
            </button>
          ))}
        </div>
      </Card>

      {/* Description */}
      {opp.description && (
        <Card className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[--color-text-tertiary] font-medium mb-2">
            Description
          </div>
          <p className="text-[13px] text-[--color-text-primary] whitespace-pre-wrap leading-relaxed">
            {opp.description}
          </p>
        </Card>
      )}

      {/* Signals */}
      {(opp.matched_skills.length > 0 || opp.budget_signal || opp.urgency_signal || opp.pain_tags.length > 0) && (
        <Card className="p-4 flex flex-col gap-3">
          {opp.matched_skills.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[--color-text-tertiary] font-medium mb-1.5">
                Matched skills
              </div>
              <div className="flex flex-wrap gap-1">
                {opp.matched_skills.map((s) => (
                  <Pill key={s} tone="accent">{s}</Pill>
                ))}
              </div>
            </div>
          )}
          {opp.budget_signal && (
            <div className="text-[12px]">
              <span className="text-[--color-text-tertiary]">Budget signal: </span>
              <span className="text-[--color-text-primary]">{opp.budget_signal}</span>
            </div>
          )}
          {opp.urgency_signal && (
            <div className="text-[12px]">
              <span className="text-[--color-text-tertiary]">Urgency: </span>
              <span className="text-[--color-text-primary]">{opp.urgency_signal}</span>
            </div>
          )}
          {opp.pain_tags.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[--color-text-tertiary] font-medium mb-1.5">
                Pain tags
              </div>
              <div className="flex flex-wrap gap-1">
                {opp.pain_tags.map((t) => (
                  <Pill key={t} tone="warm">{t}</Pill>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Contact */}
      {(opp.contact_email || opp.contact_phone) && (
        <Card className="p-4 flex flex-col gap-2">
          <div className="text-[10px] uppercase tracking-wider text-[--color-text-tertiary] font-medium">
            Contact
          </div>
          {opp.contact_email && (
            <a
              href={`mailto:${opp.contact_email}`}
              className="text-[13px] text-[--color-accent] hover:underline flex items-center gap-2"
            >
              <Mail className="w-3.5 h-3.5" /> {opp.contact_email}
            </a>
          )}
          {opp.contact_phone && (
            <a
              href={`tel:${opp.contact_phone}`}
              className="text-[13px] text-[--color-text-primary] flex items-center gap-2"
            >
              <Phone className="w-3.5 h-3.5" /> {opp.contact_phone}
            </a>
          )}
        </Card>
      )}

      {/* Quick actions */}
      <div className="flex gap-2 pt-2">
        {opp.url && (
          <Button variant="primary" onClick={() => window.open(opp.url, "_blank")}>
            Reply now
          </Button>
        )}
        <Button variant="secondary">Send template</Button>
        <Button
          variant="ghost"
          onClick={() => updateStage.mutate({ id: opp.id, stage: "lost" })}
        >
          Dismiss
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 10.2: Commit**

```bash
git add frontend/src/pages/inbox/OpportunityDetail.tsx
git commit -m "feat(inbox): add OpportunityDetail panel with stage selector + quick actions"
```

---

## Task 11: Frontend — `OpportunityList` (middle pane)

**File:** `frontend/src/pages/inbox/OpportunityList.tsx`

- [ ] **Step 11.1: Create the component**

```tsx
import { Opportunity } from "../../types/opportunity";
import { OpportunityListItem } from "./OpportunityListItem";

interface Props {
  items: Opportunity[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}

export function OpportunityList({ items, selectedId, onSelect, loading }: Props) {
  return (
    <div className="w-[380px] shrink-0 bg-[--color-bg] border-r border-[--color-border] flex flex-col">
      <div className="h-9 px-3 flex items-center justify-between border-b border-[--color-border]">
        <span className="text-[11px] uppercase tracking-wider text-[--color-text-tertiary] font-medium">
          {loading ? "Loading…" : `${items.length} opportunities`}
        </span>
      </div>
      <div className="flex-1 overflow-auto">
        {items.length === 0 && !loading && (
          <div className="p-6 text-center text-[12px] text-[--color-text-tertiary]">
            No fresh prey. Run a scan from Sources to catch some.
          </div>
        )}
        {items.map((opp) => (
          <OpportunityListItem
            key={opp.id}
            opp={opp}
            active={opp.id === selectedId}
            onClick={() => onSelect(opp.id)}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 11.2: Commit**

```bash
git add frontend/src/pages/inbox/OpportunityList.tsx
git commit -m "feat(inbox): add OpportunityList middle pane"
```

---

## Task 12: Frontend — `InboxPage` (composes the three panes)

**File:** `frontend/src/pages/inbox/InboxPage.tsx`

- [ ] **Step 12.1: Create the page**

```tsx
import { useEffect, useMemo, useState } from "react";
import { useOpportunities } from "../../api/opportunities";
import type { OpportunityFilters, Priority, OpportunityType } from "../../types/opportunity";
import { FilterPanel } from "./FilterPanel";
import { OpportunityList } from "./OpportunityList";
import { OpportunityDetail } from "./OpportunityDetail";

export function InboxPage() {
  const [filters, setFilters] = useState<OpportunityFilters>({ sort: "score", limit: 200 });
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useOpportunities(filters);
  const items = data?.opportunities ?? [];
  const selected = items.find((o) => o.id === selectedId) ?? items[0] ?? null;

  // Auto-select first item when list changes and nothing is selected
  useEffect(() => {
    if (!selectedId && items.length > 0) setSelectedId(items[0].id);
  }, [items, selectedId]);

  // Compute counts for the filter panel against the current (post-filter) list.
  // For accurate global counts we'd need a separate query — keep it cheap for now.
  const totalsByPriority = useMemo(() => {
    const counts: Record<Priority | "all", number> = { all: items.length, hot: 0, warm: 0, cold: 0 };
    items.forEach((o) => { counts[o.priority] = (counts[o.priority] ?? 0) + 1; });
    return counts;
  }, [items]);

  const totalsByType = useMemo(() => {
    const counts: Record<OpportunityType | "all", number> = { all: items.length, direct: 0, cold: 0 };
    items.forEach((o) => { counts[o.type] = (counts[o.type] ?? 0) + 1; });
    return counts;
  }, [items]);

  return (
    <div className="flex h-full">
      <FilterPanel
        value={filters}
        onChange={setFilters}
        totalsByPriority={totalsByPriority}
        totalsByType={totalsByType}
      />
      <OpportunityList
        items={items}
        selectedId={selected?.id ?? null}
        onSelect={setSelectedId}
        loading={isLoading}
      />
      {selected ? (
        <OpportunityDetail opp={selected} />
      ) : (
        <div className="flex-1 flex items-center justify-center text-[12px] text-[--color-text-tertiary]">
          {isLoading ? "Loading…" : "Select an opportunity to see details."}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 12.2: Commit**

```bash
git add frontend/src/pages/inbox/InboxPage.tsx
git commit -m "feat(inbox): compose three-pane InboxPage"
```

---

## Task 13: Frontend — placeholder page + new routes in `App.tsx`

**Why:** Wire up the new shell + Inbox without breaking the old `/cold/*` and `/direct/*` routes. Hub/Pipeline/Sources/Outreach/Templates show a placeholder until their plans ship.

**Files:**
- Create: `frontend/src/pages/PlaceholderPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 13.1: Create `PlaceholderPage.tsx`**

```tsx
interface Props {
  title: string;
  shipping: string;
}

export function PlaceholderPage({ title, shipping }: Props) {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center max-w-md">
        <h1 className="text-2xl font-semibold text-[--color-text-primary] mb-2">{title}</h1>
        <p className="text-[13px] text-[--color-text-secondary]">
          Coming next plan — {shipping}.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 13.2: Read current `App.tsx` to see exact structure**

```bash
cat frontend/src/App.tsx
```
Take note of the existing route tree — we're adding new routes alongside it.

- [ ] **Step 13.3: Update `App.tsx`**

Add imports at the top (alongside existing imports):

```tsx
import { AppShell } from "./components/shell/AppShell";
import { InboxPage } from "./pages/inbox/InboxPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
```

In the route tree, change the root redirect from `/cold/dashboard` to `/inbox`:

```tsx
<Route path="/" element={<Navigate to="/inbox" replace />} />
```

Add a new route group above the existing `<Route element={<AppLayout />}>`:

```tsx
<Route element={<AppShell />}>
  <Route path="/inbox" element={<InboxPage />} />
  <Route path="/hub" element={<PlaceholderPage title="Hub" shipping="Plan 2 — Hub & Pulse Bar" />} />
  <Route path="/pipeline" element={<PlaceholderPage title="Pipeline" shipping="Plan 3 — Pipeline Kanban" />} />
  <Route path="/sources" element={<PlaceholderPage title="Sources" shipping="Plan 4 — Sources page" />} />
  <Route path="/outreach" element={<PlaceholderPage title="Outreach" shipping="Plan 5 — Outreach revamp" />} />
  <Route path="/templates" element={<PlaceholderPage title="Templates" shipping="Plan 5 — Templates" />} />
  <Route path="/settings" element={<PlaceholderPage title="Settings" shipping="Plan 5 — Settings round-trip" />} />
</Route>
```

Keep the existing `<Route element={<AppLayout />}>` block with all `/cold/*` and `/direct/*` routes intact below this — old pages still work for now.

- [ ] **Step 13.4: Verify in browser**

Restart the dev server, open `http://localhost:5173`. Expected:
- Auto-redirect to `/inbox`
- New dark Pulse shell with PULSE wordmark, sidebar, top bar
- Inbox renders with whatever data is in `output/` — three panes (filter / list / detail)
- Click an item → detail loads with stage selector
- Click a stage → it persists (verify by reloading)
- `/cold/dashboard`, `/direct/leads` etc still load (in the old shell, looking ugly because of theme inversion — that's expected, they get removed in Plan 5)

- [ ] **Step 13.5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/PlaceholderPage.tsx
git commit -m "feat(routes): wire AppShell + Inbox at /inbox; placeholder pages for Hub/Pipeline/Sources/Outreach/Templates/Settings"
```

---

## Task 14: End-to-end smoke + cleanup

- [ ] **Step 14.1: Run all tests**

```bash
.venv/Scripts/python.exe -m pytest tests/backend -v
```
Expected: all tests pass (the new `test_opportunity_aggregator.py` and `test_opportunities_router.py` plus any pre-existing backend tests).

- [ ] **Step 14.2: Build the frontend**

```powershell
cd frontend
npm run build
```
Expected: `vite build` succeeds with no type errors.

- [ ] **Step 14.3: Manual end-to-end check**

With backend + frontend running:

1. Visit `http://localhost:5173` → auto-redirects to `/inbox`.
2. If the `output/` folder is empty: kick off a scan from the old UI (`/direct/scans/new`) using a keyword like `webflow` and the Reddit source. Wait for it to complete.
3. Reload Inbox → opportunities appear, sorted by score.
4. Click a "hot" item → detail panel populates with title, `$` value, source pill, stage selector.
5. Change stage to "Contacted" → verify the page state updates and (in another terminal) the underlying Excel file's `Outreach_Status` column changed.
6. Apply Type / Priority / Sort filters → list updates accordingly.

- [ ] **Step 14.4: Final commit**

```bash
git add -A
git status
# If anything is uncommitted (e.g. lockfile updates), commit it:
git commit -m "chore: wrap Pulse foundation + Inbox plan"
```

- [ ] **Step 14.5: Push the branch**

```bash
git push -u origin pulse-foundation
```

---

## Self-review notes (already addressed inline)

- **Spec coverage:** Identity prompt's hard rules are covered: dark-only ✓, no emojis in chrome ✓, tabular monospace `$` ✓, volt-green accent reserved for money/CTAs ✓. Inbox = first of the 5 mocked screens. Hub, Pipeline, Sources, Command Palette deferred to Plan 2-5 explicitly.
- **Placeholders:** None. All "coming soon" pages are explicit `PlaceholderPage` components, not TODOs in code.
- **Type consistency:** `Stage` enum identical between Python (`src/core/models.py`) and TypeScript (`frontend/src/types/opportunity.ts`). `Opportunity` field names match across backend dataclass and frontend interface.
- **Backwards compat:** Old `/cold/*` and `/direct/*` routes are preserved untouched. Old data files (`output/*.xlsx`) are read by the new endpoint as legacy. No migrations needed.
- **Risk:** The unified endpoint reads ALL Excel files on every request — fine for <1000 leads, slow above that. Pagination + caching are left to Plan 5 cleanup. Acceptable trade-off for first ship.
