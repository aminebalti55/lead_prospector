# Lead Prospector v2 — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite Lead Prospector with Scrapling engine, add direct lead gen pipeline (job boards), and rebuild frontend as Stripe-like SaaS dashboard.

**Architecture:** Two parallel pipelines (cold outreach + direct leads) sharing a core infrastructure layer (scraper engine, storage, config, export). FastAPI backend with routers. React + Tailwind frontend.

**Tech Stack:** Python 3.13, Scrapling (Fetcher/StealthyFetcher/DynamicFetcher), FastAPI, React 18, TypeScript, Tailwind CSS, TanStack Table/Query, Recharts, Lucide icons.

**Spec:** `docs/superpowers/specs/2026-03-10-lead-prospector-rewrite-design.md`

---

## Chunk 1: Core Infrastructure

### Task 1: Project Structure & Dependencies

**Files:**
- Modify: `requirements.txt`
- Create: `src/core/__init__.py`
- Create: `src/core/models.py`
- Create: `src/core/config.py`
- Create: `src/cold_outreach/__init__.py`
- Create: `src/direct_leads/__init__.py`
- Create: `src/direct_leads/scrapers/__init__.py`
- Create: `output/cold/.gitkeep`
- Create: `output/direct/.gitkeep`

- [ ] **Step 1: Update requirements.txt**

Replace undetected-chromedriver/selenium with scrapling:

```
# Lead Prospector v2 - Dependencies
# Python 3.11+

# Web scraping (Scrapling)
scrapling[all]>=0.4.2

# HTTP clients
httpx>=0.27.0

# Data handling
pandas>=2.2.0
openpyxl>=3.1.0

# Environment & configuration
python-dotenv>=1.0.0
pydantic>=2.6.0
pydantic-settings>=2.1.0

# Async utilities
tenacity>=8.2.0

# Logging & progress
rich>=13.7.0

# URL & text processing
tldextract>=5.1.0

# Web app backend
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
```

- [ ] **Step 2: Create directory structure**

```bash
mkdir -p src/core src/cold_outreach/scrapers src/direct_leads/scrapers src/export output/cold output/direct
touch src/core/__init__.py src/cold_outreach/__init__.py src/cold_outreach/scrapers/__init__.py src/direct_leads/__init__.py src/direct_leads/scrapers/__init__.py
touch output/cold/.gitkeep output/direct/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: scaffold v2 directory structure and update dependencies"
```

---

### Task 2: Core Models

**Files:**
- Create: `src/core/models.py`
- Test: `tests/core/test_models.py`

- [ ] **Step 1: Write tests for models**

```python
# tests/core/test_models.py
import pytest
from datetime import datetime
from src.core.models import BusinessLead, DirectLead, OutreachStatus

def test_business_lead_to_dict():
    lead = BusinessLead(source="google_maps", name="Test Plumber", city="Miami", state="FL")
    d = lead.to_dict()
    assert d["source"] == "google_maps"
    assert d["name"] == "Test Plumber"
    assert "scraped_at" in d

def test_direct_lead_id_computed():
    lead = DirectLead(
        source="indeed", title="Python Dev", description="Need dev",
        url="https://indeed.com/job/123", location="Remote"
    )
    assert lead.lead_id  # auto-computed from source+url
    assert len(lead.lead_id) == 40  # SHA-1 hex

def test_direct_lead_id_deterministic():
    kwargs = dict(source="indeed", title="X", description="Y", url="https://indeed.com/1", location="Remote")
    a = DirectLead(**kwargs)
    b = DirectLead(**kwargs)
    assert a.lead_id == b.lead_id

def test_outreach_status_values():
    assert OutreachStatus.NEW.value == "new"
    assert OutreachStatus.CONVERTED.value == "converted"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/amine.balti/lead_prospector && python -m pytest tests/core/test_models.py -v
```

- [ ] **Step 3: Implement models**

Create `src/core/models.py` — migrate `BusinessLead` from `src/scrapers/base.py` (all fields preserved), add `DirectLead` with auto-computed lead_id, add `OutreachStatus` enum, keep `ProcessedLead` from `src/scoring/scorer.py` (all fields preserved).

Key: `BusinessLead.to_dict()` preserved. `DirectLead.__post_init__` computes `lead_id = sha1(source + "|" + url)`. Import `compute_lead_id` from existing `src/utils/lead_id.py` for BusinessLead compatibility.

- [ ] **Step 4: Run tests to verify they pass**
- [ ] **Step 5: Commit**

```bash
git add src/core/models.py tests/core/test_models.py && git commit -m "feat: add core data models with BusinessLead, DirectLead, OutreachStatus"
```

---

### Task 3: Core Config

**Files:**
- Create: `src/core/config.py`
- Test: `tests/core/test_config.py`

- [ ] **Step 1: Write tests**

```python
# tests/core/test_config.py
from src.core.config import Settings, settings

def test_settings_has_all_sections():
    assert hasattr(settings, 'api')
    assert hasattr(settings, 'search')
    assert hasattr(settings, 'audit')
    assert hasattr(settings, 'scoring')
    assert hasattr(settings, 'direct_leads')
    assert hasattr(settings, 'scraping')

def test_direct_lead_settings_defaults():
    assert len(settings.direct_leads.your_skills) > 0
    assert settings.direct_leads.your_min_budget == 500

def test_scraping_settings_defaults():
    assert settings.scraping.max_concurrent_scrapers == 3

def test_output_dirs_exist():
    from src.core.config import OUTPUT_DIR, COLD_OUTPUT_DIR, DIRECT_OUTPUT_DIR
    assert OUTPUT_DIR.exists()
    assert COLD_OUTPUT_DIR.exists()
    assert DIRECT_OUTPUT_DIR.exists()
```

- [ ] **Step 2: Run tests — expect fail**
- [ ] **Step 3: Implement config**

Copy existing `src/config.py` to `src/core/config.py`. Add `DirectLeadSettings` and `ScrapingSettings` classes. Add `COLD_OUTPUT_DIR = OUTPUT_DIR / "cold"` and `DIRECT_OUTPUT_DIR = OUTPUT_DIR / "direct"`. Ensure dirs created at import.

- [ ] **Step 4: Run tests — expect pass**
- [ ] **Step 5: Commit**

---

### Task 4: Scraper Engine

**Files:**
- Create: `src/core/scraper_engine.py`
- Test: `tests/core/test_scraper_engine.py`

- [ ] **Step 1: Write tests**

```python
# tests/core/test_scraper_engine.py
import pytest
from src.core.scraper_engine import ScraperEngine

def test_fetcher_map_completeness():
    engine = ScraperEngine()
    expected = {"google_maps", "yelp", "bbb", "yellowpages", "manta",
                "indeed", "linkedin", "clutch", "goodfirms", "twitter", "reddit"}
    assert set(engine.FETCHER_MAP.keys()) == expected

def test_google_maps_uses_dynamic():
    engine = ScraperEngine()
    assert engine.FETCHER_MAP["google_maps"] == "dynamic"

def test_yellowpages_uses_http():
    engine = ScraperEngine()
    assert engine.FETCHER_MAP["yellowpages"] == "http"

def test_yelp_uses_stealth():
    engine = ScraperEngine()
    assert engine.FETCHER_MAP["yelp"] == "stealth"

def test_rate_limiter_integration():
    engine = ScraperEngine()
    assert engine.rate_limiter.can_make_request("google_maps")
```

- [ ] **Step 2: Run tests — expect fail**
- [ ] **Step 3: Implement scraper engine**

`ScraperEngine` class:
- `FETCHER_MAP` dict mapping source -> "http"|"stealth"|"dynamic"
- `fetch(url, source)` — creates appropriate Scrapling fetcher, returns response
- `fetch_with_retry(url, source, max_retries=3)` — exponential backoff wrapper
- `fetch_many(urls, source, delay=(2,5))` — batch with rate limiting
- Integrates `RateLimiter` (migrated from `src/scrapers/base.py`, remove browser_executor dependency)
- For "dynamic" sources: uses `DynamicFetcher` with Playwright
- For "stealth" sources: uses `StealthyFetcher` with Patchright
- For "http" sources: uses `Fetcher` (fast curl_cffi)

- [ ] **Step 4: Run tests — expect pass**
- [ ] **Step 5: Commit**

---

### Task 5: Core Storage

**Files:**
- Create: `src/core/storage.py`
- Test: `tests/core/test_storage.py`

- [ ] **Step 1: Write tests**

Test: `list_files("cold")` returns files from `output/cold/`. `list_files("direct")` from `output/direct/`. `list_files("legacy")` from `output/*.xlsx`. `read_leads` works for both schemas. `update_lead` migrates outreach_status from free-text to enum.

- [ ] **Step 2: Run tests — expect fail**
- [ ] **Step 3: Implement storage**

Migrate logic from `backend/excel_store.py`. Add:
- `list_files(section: "cold"|"direct"|"legacy")` — scans appropriate directory
- `read_leads(filename, section)` — reads with correct path resolution
- `update_lead(filename, lead_id, patch, section)` — same update logic, status migration
- `get_existing_businesses()` — scans both `output/*.xlsx` and `output/cold/*.xlsx`
- `get_existing_direct_lead_urls()` — scans `output/direct/*.xlsx` for dedup

- [ ] **Step 4: Run tests — expect pass**
- [ ] **Step 5: Commit**

---

## Chunk 2: Cold Outreach Pipeline (Scrapling Migration)

### Task 6: Migrate YellowPages Scraper (simplest, uses Fetcher)

**Files:**
- Create: `src/cold_outreach/scrapers/yellowpages.py`
- Test: `tests/cold_outreach/scrapers/test_yellowpages.py`

- [ ] **Step 1: Write test with mock HTML**

```python
# tests/cold_outreach/scrapers/test_yellowpages.py
import pytest
from unittest.mock import patch, MagicMock
from src.cold_outreach.scrapers.yellowpages import YellowPagesScraper

MOCK_HTML = """<div class="search-results">
  <div class="result" data-listing-id="123">
    <a class="business-name"><span>Joe's Plumbing</span></a>
    <div class="phones phone primary">(305) 555-1234</div>
    <div class="adr"><div class="street-address">123 Main St</div>
      <div class="locality">Miami</div>, <div class="region">FL</div></div>
    <a class="track-visit-website" href="http://joesplumbing.com">Website</a>
  </div>
</div>"""

def test_parse_results():
    scraper = YellowPagesScraper()
    leads = scraper._parse_search_results(MOCK_HTML, "Miami", "FL")
    assert len(leads) == 1
    assert leads[0].name == "Joe's Plumbing"
    assert leads[0].phone == "(305) 555-1234"
    assert leads[0].source == "yellowpages"
```

- [ ] **Step 2: Run test — expect fail**
- [ ] **Step 3: Implement**

Rewrite `src/scrapers/yellowpages.py` using `ScraperEngine.fetch()` instead of `run_in_browser`. CSS selectors stay the same. The scraper becomes ~80 lines of pure parsing logic.

- [ ] **Step 4: Run test — expect pass**
- [ ] **Step 5: Commit**

---

### Task 7: Migrate Manta Scraper

**Files:**
- Create: `src/cold_outreach/scrapers/manta.py`
- Test: `tests/cold_outreach/scrapers/test_manta.py`

Same pattern as Task 6. Uses `Fetcher` (HTTP-only). Migrate parsing logic from `src/scrapers/manta.py`.

- [ ] Steps 1-5: Same TDD cycle as Task 6.

---

### Task 8: Migrate BBB Scraper

**Files:**
- Create: `src/cold_outreach/scrapers/bbb.py`
- Test: `tests/cold_outreach/scrapers/test_bbb.py`

Uses `StealthyFetcher`. Migrate parsing logic from `src/scrapers/bbb.py`. Cookie consent handling now automatic via Scrapling's stealth mode.

- [ ] Steps 1-5: Same TDD cycle.

---

### Task 9: Migrate Yelp Scraper

**Files:**
- Create: `src/cold_outreach/scrapers/yelp.py`
- Test: `tests/cold_outreach/scrapers/test_yelp.py`

Uses `StealthyFetcher`. Handle blocking detection ("Device verification" page). If detected, log warning and return partial results.

- [ ] Steps 1-5: Same TDD cycle.

---

### Task 10: Migrate Google Maps Scraper

**Files:**
- Create: `src/cold_outreach/scrapers/google_maps.py`
- Test: `tests/cold_outreach/scrapers/test_google_maps.py`

Uses `DynamicFetcher` (needs scrolling/clicking). This is the only scraper that requires live browser interaction. DynamicFetcher provides Playwright page object for scroll/click operations.

- [ ] Steps 1-5: Same TDD cycle.

---

### Task 11: Migrate Website Auditor

**Files:**
- Create: `src/cold_outreach/auditor.py`
- Test: `tests/cold_outreach/test_auditor.py`

Replace `httpx` calls with `Fetcher.get()` for faster HTTP. Same audit logic (SSL, booking CTA, contact form, mobile, page load time). Same `WebsiteAuditResult` structure.

- [ ] Steps 1-5: Same TDD cycle.

---

### Task 12: Migrate Scorer (copy, no changes)

**Files:**
- Create: `src/cold_outreach/scorer.py`
- Test: `tests/cold_outreach/test_scorer.py`

Copy `src/scoring/scorer.py` as-is. Update imports to use `src.core.config`. All scoring logic identical.

- [ ] Steps 1-5: Same TDD cycle.

---

### Task 13: Migrate Email Extractor

**Files:**
- Create: `src/cold_outreach/email_extractor.py`
- Test: `tests/cold_outreach/test_email_extractor.py`

Replace httpx+browser fallback with:
1. `Fetcher.get(homepage)` — fast HTTP
2. `Fetcher.get(/contact)`, `Fetcher.get(/about)` — common pages
3. `StealthyFetcher.get(homepage)` — JS fallback only if steps 1-2 found nothing

Same regex extraction logic. Same email validation.

- [ ] Steps 1-5: Same TDD cycle.

---

### Task 14: Cold Outreach Pipeline Orchestrator

**Files:**
- Create: `src/cold_outreach/pipeline.py`
- Test: `tests/cold_outreach/test_pipeline.py`

Replaces the orchestration logic in `main.py`. Steps:
1. Load existing businesses for dedup
2. For each (location, niche): run selected scrapers via ScraperEngine
3. Merge and deduplicate results
4. Audit websites
5. Score leads
6. Extract emails (optional)
7. Export to `output/cold/`

Same flow as current `LeadProspector.run()` but cleaner, using new scraper classes.

- [ ] Steps 1-5: Same TDD cycle.

---

## Chunk 3: Direct Leads Pipeline (New)

### Task 15: Direct Lead Matcher

**Files:**
- Create: `src/direct_leads/matcher.py`
- Test: `tests/direct_leads/test_matcher.py`

- [ ] **Step 1: Write tests**

```python
# tests/direct_leads/test_matcher.py
from src.direct_leads.matcher import RelevanceMatcher

def test_skill_match_scoring():
    matcher = RelevanceMatcher(skills=["python", "react"], services=["web app"])
    score = matcher.score("Looking for Python and React developer to build web app",
                          posted_hours_ago=2, has_budget=True, has_contact=True, is_remote=True)
    assert score >= 60  # Hot: 2 skills(20) + 1 service(15) + budget(10) + contact(10) + remote(5) + recency(10)

def test_no_match_low_score():
    matcher = RelevanceMatcher(skills=["python", "react"], services=["web app"])
    score = matcher.score("Looking for plumber in Miami", posted_hours_ago=100)
    assert score < 35  # Cold

def test_priority_hot():
    matcher = RelevanceMatcher(skills=["python"], services=[])
    assert matcher.get_priority(60) == "hot"

def test_priority_warm():
    matcher = RelevanceMatcher(skills=["python"], services=[])
    assert matcher.get_priority(40) == "warm"

def test_priority_cold():
    matcher = RelevanceMatcher(skills=["python"], services=[])
    assert matcher.get_priority(20) == "cold"

def test_skill_cap_at_40():
    matcher = RelevanceMatcher(skills=["python","react","next","fast","ts","pg","docker","rust"], services=[])
    score = matcher.score("python react next fast ts pg docker rust developer")
    assert score <= 40 + 10 + 5  # skill_cap + recency + other possible bonuses
```

- [ ] **Step 2: Run tests — expect fail**
- [ ] **Step 3: Implement matcher**

`RelevanceMatcher` class with `score(description, posted_hours_ago, has_budget, has_contact, is_remote)` method. Skill matching via case-insensitive word boundary search. Caps: skills at 40, services at 30.

- [ ] **Step 4: Run tests — expect pass**
- [ ] **Step 5: Commit**

---

### Task 16: Reddit Scraper (simplest direct lead source)

**Files:**
- Create: `src/direct_leads/scrapers/reddit.py`
- Test: `tests/direct_leads/scrapers/test_reddit.py`

- [ ] **Step 1: Write tests with mock data**

Uses Reddit's public JSON API (`reddit.com/r/forhire/search.json?q=...&restrict_sr=1&sort=new`). Returns `DirectLead` objects. Test parsing of Reddit JSON response structure.

- [ ] Steps 2-5: TDD cycle.

---

### Task 17: Indeed Scraper

**Files:**
- Create: `src/direct_leads/scrapers/indeed.py`
- Test: `tests/direct_leads/scrapers/test_indeed.py`

Uses `StealthyFetcher`. Scrapes Indeed search results for freelance/contract software jobs. Extracts title, company, location, description snippet, posted date, URL.

- [ ] Steps 1-5: TDD cycle.

---

### Task 18: LinkedIn Jobs Scraper

**Files:**
- Create: `src/direct_leads/scrapers/linkedin_jobs.py`
- Test: `tests/direct_leads/scrapers/test_linkedin_jobs.py`

Uses `StealthyFetcher` on public LinkedIn job listings (no login). Fallback: Google search `site:linkedin.com/jobs`. High-risk source — graceful degradation if blocked.

- [ ] Steps 1-5: TDD cycle.

---

### Task 19: Clutch Scraper

**Files:**
- Create: `src/direct_leads/scrapers/clutch.py`
- Test: `tests/direct_leads/scrapers/test_clutch.py`

Uses `Fetcher` (simple HTML). Scrapes Clutch project listings / RFP board.

- [ ] Steps 1-5: TDD cycle.

---

### Task 20: GoodFirms Scraper

**Files:**
- Create: `src/direct_leads/scrapers/goodfirms.py`
- Test: `tests/direct_leads/scrapers/test_goodfirms.py`

Uses `Fetcher`. Similar to Clutch.

- [ ] Steps 1-5: TDD cycle.

---

### Task 21: Twitter/X Scraper

**Files:**
- Create: `src/direct_leads/scrapers/twitter.py`
- Test: `tests/direct_leads/scrapers/test_twitter.py`

Uses `StealthyFetcher`. Searches for "looking for developer", "need a dev", "hiring freelance" + tech keywords. Fallback: Nitter instances. High-risk source.

- [ ] Steps 1-5: TDD cycle.

---

### Task 22: Direct Lead Enricher

**Files:**
- Create: `src/direct_leads/enricher.py`
- Test: `tests/direct_leads/test_enricher.py`

Visits company website (if available) to extract: contact email, phone, company size indicators, tech stack mentions. Uses `Fetcher` for fast HTTP.

- [ ] Steps 1-5: TDD cycle.

---

### Task 23: Direct Leads Pipeline Orchestrator

**Files:**
- Create: `src/direct_leads/pipeline.py`
- Test: `tests/direct_leads/test_pipeline.py`

Steps:
1. Load existing direct lead URLs for dedup
2. Run selected source scrapers
3. Score each lead via `RelevanceMatcher`
4. Enrich (extract company contact info)
5. Export to `output/direct/`

- [ ] Steps 1-5: TDD cycle.

---

## Chunk 4: Backend API

### Task 24: Cold Outreach Router

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/cold_outreach.py`
- Test: `tests/backend/test_cold_outreach_router.py`

Migrate endpoints from `backend/app.py`:
- `POST /api/cold/runs` — start scraping run
- `GET /api/cold/runs/{run_id}` — run status
- `GET /api/cold/runs` — list runs
- `GET /api/cold/files` — list XLSX files from `output/cold/` + legacy `output/*.xlsx`
- `GET /api/cold/files/{filename}/leads` — read leads
- `GET /api/cold/files/{filename}/download` — download
- `PATCH /api/cold/leads/{lead_id}` — update CRM fields

Uses `src.core.storage` instead of `backend.excel_store`.

- [ ] Steps 1-5: TDD cycle.

---

### Task 25: Direct Leads Router

**Files:**
- Create: `backend/routers/direct_leads.py`
- Test: `tests/backend/test_direct_leads_router.py`

New endpoints:
- `POST /api/direct/scans` — start scan
- `GET /api/direct/scans/{scan_id}` — scan status
- `GET /api/direct/scans` — list scans
- `GET /api/direct/leads` — list leads (paginated, filterable by source/priority/skill)
- `GET /api/direct/leads/{lead_id}` — full detail
- `PATCH /api/direct/leads/{lead_id}` — update status/notes
- CRUD for saved searches (`/api/direct/saved-searches`)

Saved searches stored in `output/direct/saved_searches.json`.

- [ ] Steps 1-5: TDD cycle.

---

### Task 26: Shared Router

**Files:**
- Create: `backend/routers/shared.py`
- Test: `tests/backend/test_shared_router.py`

Endpoints:
- `GET /api/health`
- `GET /api/stats` — aggregate across both pipelines
- `GET /api/stats/cold` — cold only
- `GET /api/stats/direct` — direct only
- `GET /api/email/templates`, `POST /api/email/send`, `POST /api/email/batch`, `POST /api/email/preview`

Migrate email logic from `backend/app.py`. Add direct lead templates.

- [ ] Steps 1-5: TDD cycle.

---

### Task 27: Scheduler

**Files:**
- Create: `backend/scheduler.py`
- Test: `tests/backend/test_scheduler.py`

Background `asyncio.Task`:
- Reads `output/direct/saved_searches.json` on startup
- Every 60s checks if any saved search is due
- Triggers direct leads pipeline when due
- Updates `last_run` timestamp in saved search

- [ ] Steps 1-5: TDD cycle.

---

### Task 28: Rewire app.py & Backend Models

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/models.py`
- Modify: `run_server.py`

Strip `app.py` down to:
- FastAPI app creation
- CORS middleware
- Include 3 routers (`cold_outreach`, `direct_leads`, `shared`)
- Start scheduler on startup event
- Serve frontend static files

Update `backend/models.py` with:
- `DirectScanCreateRequest`, `DirectScanStatusResponse`
- `SavedSearchRequest`, `SavedSearchResponse`
- `DirectLeadResponse`, `DirectLeadUpdateRequest`
- Keep all existing cold outreach models

- [ ] Steps 1-5: TDD cycle.

---

## Chunk 5: Frontend Redesign

### Task 29: Frontend Scaffold

**Files:**
- Recreate: `frontend/` (fresh Vite + React + TS + Tailwind project)

- [ ] **Step 1: Create fresh frontend**

```bash
cd C:/Users/amine.balti/lead_prospector
rm -rf frontend/src frontend/public frontend/index.html
cd frontend
npm create vite@latest . -- --template react-ts
npm install tailwindcss @tailwindcss/vite
npm install @tanstack/react-query @tanstack/react-table
npm install react-router-dom recharts lucide-react
npm install clsx
```

- [ ] **Step 2: Configure Tailwind**

Add `@tailwindcss/vite` plugin to `vite.config.ts`. Add `@import "tailwindcss"` to `index.css`. Configure Inter font. Set up Vite proxy for `/api` -> `localhost:8000`.

- [ ] **Step 3: Create design system**

Create `src/lib/cn.ts` (clsx helper), `src/styles/` with color tokens matching spec (#635BFF primary, #FAFAFA bg, etc.).

- [ ] **Step 4: Commit**

---

### Task 30: Layout Shell & Routing

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/layouts/AppLayout.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/components/TopNav.tsx`

Layout: Top nav with [Cold Outreach | Direct Leads] toggle. Left sidebar with Dashboard, Leads, Runs/Scans, Email, Settings links. Main content area.

- [ ] **Step 1: Implement AppLayout with sidebar + topnav**
- [ ] **Step 2: Set up React Router routes**

```
/cold/dashboard, /cold/leads, /cold/runs, /cold/runs/new, /cold/email
/direct/dashboard, /direct/leads, /direct/scans, /direct/scans/new, /direct/saved-searches
/settings
```

- [ ] **Step 3: Commit**

---

### Task 31: Shared Components

**Files:**
- Create: `frontend/src/components/StatCard.tsx`
- Create: `frontend/src/components/DataTable.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/components/EmptyState.tsx`
- Create: `frontend/src/components/PageHeader.tsx`

- `StatCard`: Stripe-style metric card (label, value, optional trend)
- `DataTable`: TanStack Table wrapper with sorting, filtering, pagination
- `StatusBadge`: Colored pill for priority (Hot/Warm/Cold) and outreach status
- `EmptyState`: "No leads yet. Start your first scan →"
- `PageHeader`: Title + action buttons

- [ ] Steps 1-3: Implement each, commit.

---

### Task 32: API Client & Query Hooks

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/cold.ts`
- Create: `frontend/src/api/direct.ts`
- Create: `frontend/src/api/shared.ts`

TanStack Query hooks for all API endpoints. `client.ts` is a thin `fetch` wrapper.

- [ ] Step 1: Implement API client and all hooks
- [ ] Step 2: Commit

---

### Task 33: Cold Outreach Pages

**Files:**
- Create: `frontend/src/pages/cold/Dashboard.tsx`
- Create: `frontend/src/pages/cold/Leads.tsx`
- Create: `frontend/src/pages/cold/NewRun.tsx`
- Create: `frontend/src/pages/cold/RunHistory.tsx`
- Create: `frontend/src/pages/cold/EmailOutreach.tsx`

- [ ] **Step 1: Dashboard** — stat cards (total, hot, warm, cold), Recharts bar chart by source, pie chart by priority
- [ ] **Step 2: Leads** — DataTable with all columns, inline status edit, expandable row for audit details
- [ ] **Step 3: NewRun** — form with locations, niches, source toggles, max results, submit → POST /api/cold/runs
- [ ] **Step 4: RunHistory** — list of past runs with status badges, progress bars, re-run button
- [ ] **Step 5: EmailOutreach** — template selector, recipient list from leads, preview, send/batch
- [ ] **Step 6: Commit**

---

### Task 34: Direct Leads Pages

**Files:**
- Create: `frontend/src/pages/direct/Dashboard.tsx`
- Create: `frontend/src/pages/direct/Leads.tsx`
- Create: `frontend/src/pages/direct/NewScan.tsx`
- Create: `frontend/src/pages/direct/SavedSearches.tsx`
- Create: `frontend/src/pages/direct/LeadDetail.tsx`

- [ ] **Step 1: Dashboard** — new leads today, hot opportunities count, skill match distribution chart
- [ ] **Step 2: Leads** — DataTable with relevance score, matched skills as tag pills, budget/urgency badges, source icon
- [ ] **Step 3: NewScan** — source checkboxes, keyword input, skill filter, frequency selector (one-time/recurring)
- [ ] **Step 4: SavedSearches** — CRUD table for recurring scans, enable/disable toggle, last run time
- [ ] **Step 5: LeadDetail** — full job description, company info panel, suggested outreach message, status actions
- [ ] **Step 6: Commit**

---

### Task 35: Settings Page

**Files:**
- Create: `frontend/src/pages/Settings.tsx`

Sections:
- **Profile**: your_skills (tag input), your_services (tag input), hourly_rate, min_budget
- **Email**: SMTP host/port/user/password, sender name
- **Scraping**: proxy URL, max concurrent scrapers
- **API Keys**: Google Places, Yelp (optional)

All fields save via `POST /api/settings` (new endpoint to add to shared router).

- [ ] Steps 1-3: Implement, add backend endpoint, commit.

---

## Chunk 6: Integration & Cleanup

### Task 36: Update main.py CLI

**Files:**
- Modify: `main.py`

Update CLI to use new pipeline modules. Add `--mode cold|direct` flag. Keep backward compatibility with existing CLI args for cold outreach.

- [ ] Steps 1-3: Implement, test, commit.

---

### Task 37: Remove Old Code

**Files:**
- Delete: `src/scrapers/browser_manager.py`
- Delete: `src/scrapers/google_maps.py`, `yelp.py`, `yellowpages.py`, `bbb.py`, `manta.py`
- Delete: `src/scrapers/base.py` (migrated to core/models + core/scraper_engine)
- Delete: `backend/excel_store.py` (migrated to core/storage)
- Keep: `src/scrapers/email_extractor.py` only if `src/cold_outreach/email_extractor.py` is confirmed working

- [ ] **Step 1: Verify all new modules import correctly**

```bash
python -c "from src.cold_outreach.pipeline import ColdOutreachPipeline; from src.direct_leads.pipeline import DirectLeadsPipeline; print('OK')"
```

- [ ] **Step 2: Verify backend starts**

```bash
cd C:/Users/amine.balti/lead_prospector && python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 3: Delete old files**
- [ ] **Step 4: Run full test suite**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: remove legacy scraper code, complete v2 migration"
```

---

### Task 38: End-to-End Smoke Test

- [ ] **Step 1: Test cold outreach pipeline**

```bash
python main.py --mode cold --locations "Miami, FL" --niches plumbing --max-results 5
```

Verify: XLSX created in `output/cold/`, leads have scores and priorities.

- [ ] **Step 2: Test direct leads pipeline**

```bash
python main.py --mode direct --sources reddit --keywords "python developer"
```

Verify: XLSX created in `output/direct/`, leads have relevance scores.

- [ ] **Step 3: Test web app**

Start backend + frontend. Verify both sections load, data tables populated, status updates work.

- [ ] **Step 4: Final commit**

```bash
git add -A && git commit -m "feat: Lead Prospector v2 complete - Scrapling engine, direct lead gen, new UI"
```
