# Lead Prospector v2 — Full Rewrite Design

**Date:** 2026-03-10
**Status:** Approved

## Overview

Full rewrite of Lead Prospector: replace undetected-chromedriver with Scrapling, add a direct lead generation pipeline (job boards), and rebuild the frontend as a Stripe-like SaaS dashboard. Single-user tool (no auth, no multi-tenancy).

## Goals

1. Replace undetected-chromedriver with Scrapling for all scraping (speed, reliability, maintainability)
2. Add direct lead gen pipeline: Indeed, LinkedIn Jobs, Clutch, GoodFirms, Twitter/X, Reddit
3. Rebuild frontend: Tailwind CSS, Stripe-inspired design, two-section layout (cold outreach + direct leads)
4. Unified outreach tracking across both pipelines

## Architecture

```
lead_prospector/
├── src/
│   ├── core/
│   │   ├── scraper_engine.py    # Scrapling wrapper (Fetcher/StealthyFetcher/DynamicFetcher factory)
│   │   ├── models.py            # All dataclasses (BusinessLead, DirectLead, ProcessedLead)
│   │   ├── config.py            # Pydantic-Settings config (extends existing Settings classes)
│   │   └── storage.py           # Replaces backend/excel_store.py — handles both lead types
│   │
│   ├── cold_outreach/
│   │   ├── scrapers/            # 5 directory scrapers (Google Maps, Yelp, YellowPages, BBB, Manta)
│   │   ├── auditor.py           # Website auditor (Scrapling Fetcher)
│   │   ├── scorer.py            # Lead scoring (same pain-signal logic, same weights)
│   │   ├── email_extractor.py   # Email extraction (Scrapling-powered)
│   │   └── pipeline.py          # Orchestrator: scrape -> audit -> score -> export
│   │
│   ├── direct_leads/
│   │   ├── scrapers/            # 6 job board scrapers
│   │   │   ├── indeed.py
│   │   │   ├── linkedin_jobs.py
│   │   │   ├── clutch.py
│   │   │   ├── goodfirms.py
│   │   │   ├── twitter.py
│   │   │   └── reddit.py
│   │   ├── matcher.py           # Relevance scoring against user skill profile
│   │   ├── enricher.py          # Company info, contact extraction
│   │   └── pipeline.py          # Orchestrator: scrape -> match -> enrich -> export
│   │
│   └── export/
│       └── exporter.py          # Shared XLSX/CSV export (fixes column letter bug for >26 cols)
│
├── backend/
│   ├── app.py                   # FastAPI app
│   ├── routers/
│   │   ├── cold_outreach.py     # /api/cold/* endpoints
│   │   ├── direct_leads.py      # /api/direct/* endpoints
│   │   └── shared.py            # /api/stats, /api/files, /api/email
│   ├── models.py                # Pydantic request/response models
│   └── scheduler.py             # Background asyncio scheduler for recurring scans
│
├── frontend/                    # React + Tailwind full redesign
└── output/
    ├── cold/                    # Cold outreach XLSX files
    └── direct/                  # Direct lead XLSX files
```

## Scraper Engine

Single abstraction replacing browser_manager.py + ThreadPoolExecutor. Three fetcher tiers:

### Fetcher Selection

| Tier | Scrapling Class | Used For | Why |
|------|----------------|----------|-----|
| HTTP-only | `Fetcher` | YellowPages, Manta, Clutch, GoodFirms, Reddit | Simple HTML, minimal protection. Fastest. |
| Browser automation | `DynamicFetcher` | Google Maps | Requires scrolling, clicking, waiting for JS-rendered content. Uses Playwright under the hood. |
| Stealth browser | `StealthyFetcher` | Yelp, BBB, Indeed, LinkedIn Jobs, Twitter/X | Anti-bot detection but no complex interaction needed. Uses Patchright with fingerprint spoofing. |

**Key distinction:** Google Maps is the only scraper that requires live DOM interaction (scrolling the results panel, clicking "Next"). `DynamicFetcher` provides this via Playwright. All other scrapers work with single page fetches — they don't need scrolling or clicking.

### Engine Responsibilities

```python
class ScraperEngine:
    """Replaces browser_manager.py entirely."""

    FETCHER_MAP = {
        # Cold outreach
        "google_maps": "dynamic",      # Needs scrolling/clicking
        "yelp": "stealth",
        "bbb": "stealth",
        "yellowpages": "http",
        "manta": "http",
        # Direct leads
        "indeed": "stealth",
        "linkedin": "stealth",
        "clutch": "http",
        "goodfirms": "http",
        "twitter": "stealth",
        "reddit": "http",
    }

    # Proxy rotation (optional, configured in .env)
    # User-agent management (handled by Scrapling internally)
    # Cookie persistence per source
    # Rate limiting: per-source delays + hourly caps (migrated from existing RateLimiter)
```

### Error Handling & Retry Strategy

| Scenario | Behavior |
|----------|----------|
| HTTP error (4xx/5xx) | Retry up to 3 times with exponential backoff (2s, 4s, 8s) |
| Anti-bot block detected | Switch to next proxy if available, retry once. Log and skip if still blocked. |
| Timeout (30s default) | Retry once, then skip and log |
| Partial batch failure | Continue with successful results, report skipped URLs in run progress |
| Rate limit hit | Pause until rate limit window resets (honor existing hourly caps) |
| Scrapling crash/exception | Catch, log full traceback, skip source, continue pipeline with other sources |

No silent failures. Every skip is logged and visible in run progress.

## Data Models

### BusinessLead (cold outreach — all existing fields preserved)

Fields: source, name, city, state, phone, website, address, email, email_source, rating, review_count, categories, is_claimed, is_sponsored, detail_url, extra_data (dict for BBB rating, years, SIC code, etc.), scraped_at

### ProcessedLead (cold outreach — all existing fields preserved)

Standalone dataclass (not inheritance). All existing fields preserved including:
- Source-specific: google_place_id, yelp_id, yelp_url, google_rating, yelp_rating, google_review_count, yelp_review_count
- Audit: has_ssl, has_booking_cta, has_contact_form, is_mobile_friendly, page_load_time_ms
- Scoring: total_score, priority, recommended_offer, offer_reasoning, pain_tags, website_score, conversion_score, ops_score, reputation_score
- CRM: outreach_status, notes, owner, last_contacted, follow_up_date
- Identity: lead_id (SHA-1 of name+address+phone+website via existing lead_id.py logic)

### DirectLead (new)

Fields: lead_id (SHA-1 of source+url), source, title, description, url, posted_date, company_name, company_website, company_size, location, contact_name, contact_email, contact_phone, relevance_score, budget_signal, urgency_signal, matched_skills, outreach_status, notes, scraped_at

## Scoring Systems

The two pipelines use **different scoring models** because they measure different things. The frontend treats them as separate sections with their own dashboards — no normalization needed.

### Cold Outreach Scoring (unchanged)

Pain-signal-based, component scores:
- website_score, conversion_score, ops_score, reputation_score
- Weights: no website (25), no booking CTA (20), ops pain (20), no contact form (15), not mobile (15), etc.
- Priority: Hot >= 35, Warm >= 25, Cold < 25

### Direct Lead Scoring (new)

Relevance-based, additive 0-100:
- Skill keyword match: +10 each (capped at 40)
- Service match: +15 each (capped at 30)
- Budget mentioned: +10
- Urgency words: +10
- Remote/flexible: +5
- Direct contact available: +10
- Posted < 24h: +10, Posted < 72h: +5
- Priority: Hot >= 60, Warm >= 35, Cold < 35

## Outreach Status

### Enum definition (replaces free-text field)

```python
class OutreachStatus(str, Enum):
    NEW = "new"
    QUEUED = "queued"
    CONTACTED = "contacted"
    REPLIED = "replied"
    MEETING = "meeting"
    CONVERTED = "converted"
    PASSED = "passed"
```

Used by both pipelines. Same status flow, same tracking.

### Migration from existing data

Existing Excel files have a free-text `Outreach_Status` column. Migration logic:
- Empty / missing → `new`
- "Contacted" (existing hardcoded value) → `contacted`
- Any unrecognized value → preserve as-is in `notes`, set status to `new`

## Data Migration Strategy

### Existing Excel files (output/*.xlsx)

1. Existing files are **read-only legacy**. They stay in `output/` root and are still viewable in the UI under a "Legacy" section.
2. New cold outreach runs write to `output/cold/` with the same column schema (Lead_ID preserved, computed identically via lead_id.py).
3. New direct lead runs write to `output/direct/` with DirectLead column schema.
4. `storage.py` can read both old and new formats. Old files are detected by the absence of `output/cold/` or `output/direct/` path prefix.
5. Cross-run deduplication still works: `get_existing_businesses()` scans both `output/*.xlsx` and `output/cold/*.xlsx`.

### Lead_ID preservation

Lead_ID computation is unchanged: `SHA-1(normalize(name) | normalize(address) | last10digits(phone) | normalize(website))`. Existing IDs remain valid. The `lead_id.py` utility moves to `src/core/` but logic is identical.

## Source Strategy

| Source | Fetcher | Frequency | What we scrape | Risk Level |
|--------|---------|-----------|---------------|------------|
| Google Maps | DynamicFetcher | On demand | Business listings by niche + location | Medium — needs scrolling |
| Yelp | StealthyFetcher | On demand | Business listings by niche + location | Medium — detection possible |
| BBB | StealthyFetcher | On demand | Business listings + accreditation | Low |
| YellowPages | Fetcher | On demand | Business listings | Low |
| Manta | Fetcher | On demand | Business listings + company details | Low |
| Indeed | StealthyFetcher | Daily | Jobs matching tech stack keywords | Medium — rate limits |
| LinkedIn Jobs | StealthyFetcher | Daily | Public job listings (no login) | High — aggressive anti-bot |
| Clutch | Fetcher | Weekly | Project listings / RFPs | Low |
| GoodFirms | Fetcher | Weekly | Project boards | Low |
| Twitter/X | StealthyFetcher | Every few hours | "looking for developer" + tech keywords | High — auth wall possible |
| Reddit | Fetcher | Every few hours | r/forhire, r/freelance [Hiring] posts | Low — public JSON API |

### High-Risk Source Fallbacks

**LinkedIn Jobs:** Primary: StealthyFetcher on public job listings (no login required). Fallback: Google search `site:linkedin.com/jobs "python developer" "remote"` via StealthyFetcher. If both fail, source is marked as unavailable in that scan and user is notified.

**Twitter/X:** Primary: StealthyFetcher on search results. Fallback: Nitter instances (public Twitter mirrors). If both fail, source is skipped. Future option: Twitter API v2 free tier (limited but legitimate).

## API Endpoints

### Cold Outreach (`/api/cold/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/cold/runs` | Start a new scraping run |
| GET | `/api/cold/runs/{run_id}` | Get run status + progress |
| GET | `/api/cold/runs` | List all runs |
| GET | `/api/cold/files` | List all cold outreach XLSX files |
| GET | `/api/cold/files/{filename}/leads` | Read leads from XLSX as JSON |
| GET | `/api/cold/files/{filename}/download` | Download XLSX |
| PATCH | `/api/cold/leads/{lead_id}` | Update CRM fields (status, notes, owner, dates) |

### Direct Leads (`/api/direct/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/direct/scans` | Start a new scan |
| GET | `/api/direct/scans/{scan_id}` | Get scan status + progress |
| GET | `/api/direct/scans` | List all scans |
| GET | `/api/direct/leads` | List all direct leads (paginated, filterable) |
| GET | `/api/direct/leads/{lead_id}` | Get full lead detail (job description, company info) |
| PATCH | `/api/direct/leads/{lead_id}` | Update outreach status, notes |
| POST | `/api/direct/saved-searches` | Create a saved search config |
| GET | `/api/direct/saved-searches` | List saved searches |
| PUT | `/api/direct/saved-searches/{id}` | Update saved search |
| DELETE | `/api/direct/saved-searches/{id}` | Delete saved search |

### Shared (`/api/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/stats` | Aggregate stats across both pipelines |
| GET | `/api/stats/cold` | Cold outreach stats only |
| GET | `/api/stats/direct` | Direct lead stats only |
| GET | `/api/email/templates` | List email templates |
| POST | `/api/email/send` | Send single email |
| POST | `/api/email/batch` | Send batch emails |
| POST | `/api/email/preview` | Preview email with variable substitution |

## Frontend Design

### Design System
- Background: #FAFAFA
- Surface: #FFFFFF with subtle shadow (0 1px 3px rgba(0,0,0,0.08))
- Primary: #635BFF (indigo)
- Success: #0CAF60, Warning: #F5A623, Hot: #E25C3D
- Text: #1A1F36 / #697386
- Borders: #E3E8EE
- Font: Inter
- No gradients, no glows, no decorative noise

### Tech Stack
- React 18 + TypeScript
- Tailwind CSS (replaces MUI entirely)
- TanStack Table (replaces MUI DataGrid) + TanStack Query (kept)
- React Router (kept)
- Recharts (kept — for dashboard charts)
- Lucide icons (replaces MUI icons)

### Layout
- Top nav with section toggle: [Cold Outreach | Direct Leads]
- Left sidebar: Dashboard, Leads, Runs/Scans, Email, Settings
- Main content: stat cards + data tables

### Pages — Cold Outreach
- Dashboard: stats by priority, source, conversion funnel (Recharts)
- Leads: filterable table, inline CRM, expandable audit details
- New Run: locations, niches, sources, options
- Run History: past runs, progress, re-run
- Email Outreach: templates, batch send, history

### Pages — Direct Leads
- Dashboard: new leads today, hot opportunities, skill match distribution (Recharts)
- Leads: table with relevance score, skill tags, budget/urgency badges
- New Scan: sources, keywords, skill filters, frequency
- Saved Searches: recurring scan configs
- Lead Detail: full description, company info, suggested outreach

### Pages — Shared
- Settings: skills, services, rates, SMTP config, proxy config (editable, saves to .env)

## Email & Outreach

### Email Extraction (Scrapling-powered)
1. Fetcher.get(homepage) — fast HTTP
2. Fetcher.get(/contact, /about) — common pages
3. StealthyFetcher fallback — only for JS-heavy sites

### Outreach Templates
Cold outreach: existing 4 templates (kept).
Direct leads: contextual templates auto-filled from job posting (title, matched_skills, service_match). Pre-written snippet bank, not AI-generated.

## Scheduling

### Implementation
- `scheduler.py`: background `asyncio.Task` started alongside FastAPI in `run_server.py`
- Checks saved searches every 60 seconds, triggers scans when due
- Saved searches stored as JSON in `output/direct/saved_searches.json`
- Persists across restarts (reads from file on startup)

### Notifications
- **In-app**: badge count on Direct Leads nav item (polled via `GET /api/stats/direct`)
- **Desktop**: browser Notification API (frontend checks for new hot leads on each poll)
- **Email digest**: optional, configurable in Settings. Scheduler sends daily summary of new hot leads via SMTP.

No WebSockets. Frontend polls `/api/stats/direct` every 30 seconds when active.

## Configuration

Extends existing Pydantic-Settings classes in config.py:

```python
class DirectLeadSettings(BaseSettings):
    your_skills: list[str] = ["python", "react", "nextjs", "fastapi"]
    your_services: list[str] = ["web app", "saas", "api", "automation"]
    your_hourly_rate: int = 75
    your_min_budget: int = 500

class ScrapingSettings(BaseSettings):
    proxy_url: str | None = None
    max_concurrent_scrapers: int = 3

# Existing settings kept: APISettings, SearchSettings, AuditSettings, ScoringSettings, SMTPSettings
```

All editable from Settings page in UI. Settings page writes to `.env` file.
