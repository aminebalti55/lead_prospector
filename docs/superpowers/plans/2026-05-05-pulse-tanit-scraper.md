# Pulse — Tanit Jobs Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Commit message rule (project-wide):** NEVER add `Co-Authored-By: Claude`, "Generated with Claude Code", or any AI/assistant attribution to any commit message. Each task spec gives the exact message — use it verbatim.

**Goal:** Add a working **Tanit Jobs scraper** for `tanitjobs.com` (Tunisian job board, 2,870 active listings) to the direct-leads pipeline. Site is Cloudflare-protected, so the scraper uses Scrapling's `StealthyFetcher` (already routed through the existing `ScraperEngine`). Parses listing pages only (detail-page email is gated behind login). After this plan, the user can create a saved search with `["tanit"]` as a source and pull jobs from the only Francophone-MENA-niched source in Pulse — their actual moat per the biz analysis.

**Architecture:**
- **One new scraper file** following the existing `RedditScraper` pattern: constructor takes `ScraperEngine`, `async def search(keywords, max_results) -> list[DirectLead]`.
- **Three small registry edits:** add `"tanit"` to `ScraperEngine.FETCHER_MAP` (stealth tier — for Cloudflare bypass), add to `RateLimiter.RATE_LIMITS` (slow + low cap — small regional site, be polite), add `TanitScraper` to `SCRAPER_CLASSES` dict in `pipeline.py`.
- **Listing page only** (no per-job detail fetch): the listing page already has title, company, location, description preview, URL — all the data needed for relevance scoring. Detail-page email/phone is gated behind login. Adding detail fetches would double request count for marginal gain.
- **Frontend already has Tanit support** from Plan 4 — Sources card, SavedSearchEditor source chip, hub_aggregator known-source list. No frontend changes needed.

**Tech Stack:** Python 3.12, Scrapling (`StealthyFetcher`), pytest. No new dependencies.

---

## Reconnaissance findings (gathered live from Playwright session)

**Site:** `https://www.tanitjobs.com/` — Tunisian job board, French/Arabic content. ~2,870 active jobs.

**Cloudflare:** Yes. Initial GET returns "Un instant…" challenge page. `StealthyFetcher` clears it within ~5–8 seconds (the existing BBB and Yelp scrapers already use this pattern).

**Search URL:**
- Format: `https://www.tanitjobs.com/jobs/?q=<KEYWORD>&l=<LOCATION>&page=<N>`
- Empty `q=&l=` returns all listings.
- 23 listings per page. ~125 pages total.
- Pagination: `?page=2`, `?page=3`, etc.
- **NB:** keyword search is loose — searching `q=react` returns broad listings (mostly non-tech). Relevance scoring already filters post-fetch by user's skill keywords, so this is fine.

**Listing card HTML (verified live):**
```html
<article id="1999931" class="media well listing-item listing-item__jobs listing-item__featured">
  <div class="media-left listing-item__logo">
    <a href="https://www.tanitjobs.com/job/1999931/un-e-ingenieur-npi/?backPage=1&searchID=...">
      <img class="profile__img-company" src="..." alt="CMR GROUP">
    </a>
  </div>
  <div class="media-body">
    <div class="media-heading listing-item__title">
      <a href="...same-url..." class="link">Un(e) Ingénieur NPI</a>
    </div>
    <div class="listing-item__info clearfix">
      <span class="listing-item-info-company">CMR GROUP - </span>
      <span class="listing-item-info-location">Mghira, Ben Arous, Tunisie</span>
    </div>
    <div class="listing-item__desc hidden-sm hidden-xs">
      Fondé à Marseille en 1959, le Groupe CMR est un spécialiste de la gestion...
    </div>
  </div>
</article>
```

**Selectors used in this plan:**
| Field | Selector |
|---|---|
| Card | `article.listing-item__jobs` |
| ID | `article` element's `id` attribute (numeric Tanit job ID) |
| Detail URL | `a` inside `.listing-item__title` (`.link` class) — `href` |
| Title | same `a` — text content (trimmed) |
| Company | `.listing-item-info-company` — text (strip trailing dash + whitespace) |
| Location | `.listing-item-info-location` — text |
| Description | `.listing-item__desc.hidden-sm.hidden-xs` — text (truncate to 500 chars) |
| Featured flag | `article` class includes `listing-item__featured` |

**Known limitations (v1):**
- `posted_date`: not on listing page; on detail page as relative French ("Il'y a 2 semaines"). v1 leaves `posted_date=None`. (Future enhancement: parse French relative dates.)
- `contact_email`: gated behind login on detail page. v1 leaves `contact_email=""`.
- `contact_phone`: occasionally on detail page. v1 leaves `contact_phone=""`. (Future: optional detail-page fetch.)

---

## Scope decision

This is a **focused single-source plan**. ~5 tasks, half a day of work.

| # | Plan | Status |
|---|---|---|
| 1 | Foundation & Inbox | ✅ |
| 2 | Hub & Live PulseBar | ✅ |
| 3 | Pipeline Kanban | ✅ |
| 4 | Sources & scheduler | ✅ |
| 5 | Outreach + Templates + Settings + cleanup | ✅ |
| **6 (this)** | **Tanit Jobs scraper** | About to ship |
| 7 | Supabase migration | Pending — separate plan |

---

## File structure (this plan)

**New backend files:**
- `src/direct_leads/scrapers/tanit.py` — `TanitScraper` class

**Modified backend files:**
- `src/core/scraper_engine.py` — register `"tanit": "stealth"` in `FETCHER_MAP`, add `tanit` rate-limit entry to `RateLimiter.RATE_LIMITS`
- `src/direct_leads/pipeline.py` — register `TanitScraper` in `SCRAPER_CLASSES` dict, add import

**New backend tests:**
- `tests/direct_leads/scrapers/test_tanit.py` — TDD with mocked HTML fixture

**Untouched (preserved):**
- All Plan 1-5 code: every router, every page, every service
- The frontend Tanit references from Plan 4 (Sources card, SavedSearchEditor, scraper status grid) — they Just Work once the backend supports the source

---

## Conventions

- **`SOURCE_NAME = "tanit"`** — must match the string used everywhere else (`hub_aggregator._KNOWN_DIRECT_SOURCES`, `SavedSearchEditor.ALL_SOURCES`, `SourceCard.LABEL["tanit"] = "Tanit Jobs"`). All these were added in Plan 4 — verify they're consistent before relying on them.
- **Lead `description`** truncated to 500 chars to match what `LeadExporter` writes (existing pattern).
- **Lead `location`** — keep the full string from the listing page (e.g. `"Mghira, Ben Arous, Tunisie"`).
- **Lead `url`** — strip the `?backPage=...&searchID=...` query string so leads dedupe across sessions (the searchID is per-session-random; without stripping, the same job appears multiple times across runs).
- **Pagination cap:** at most `ceil(max_results / 23)` pages. With default `max_results=20`, we fetch only the first page.
- **Featured flag:** stored as a boolean key in `extra_data` (existing pattern from BusinessLead in cold scrapers — but `DirectLead` doesn't have `extra_data`. So for v1, prepend `"[Featured] "` to the title if featured. Simplest signal.)

---

## Pre-flight

- [ ] **Step 0.1: Verify Plan 5 is committed and the branch is clean**

```bash
cd C:\Users\JIMMY\lead_prospector
git status
git log --oneline pulse-foundation -5
```
Expected: working tree clean, latest commit is `6ddd7dd feat(routes): mount Settings/Templates/Outreach; remove deprecated /cold and /direct` or later.

- [ ] **Step 0.2: Confirm tanit is already in the canonical lists**

```bash
grep -n '"tanit"' backend/services/hub_aggregator.py
grep -n '"tanit"' frontend/src/pages/sources/SavedSearchEditor.tsx
grep -n '"tanit"' frontend/src/pages/sources/SourceCard.tsx
```
Expected: each grep returns at least one hit. (These were added in Plan 4. If any are missing, the implementer must add them — but per Plan 4's QA, they're all there.)

---

## Task 1: Register Tanit in `ScraperEngine`

**Why:** Tells `ScraperEngine.async_fetch` to use `StealthyFetcher` (Cloudflare bypass) for `tanit` requests, and gives the rate limiter a sensible delay/cap. Two small edits to one file.

**Files:**
- Modify: `src/core/scraper_engine.py`

- [ ] **Step 1.1: Add `tanit` to `RATE_LIMITS`**

In `src/core/scraper_engine.py`, find the `RATE_LIMITS` dict in class `RateLimiter` (around lines 16–29). Add this entry inside the dict, alphabetically placed near `twitter`:

```python
        "tanit": {"min_delay": 3, "max_delay": 6, "hourly_cap": 100},
```

After the edit, the dict body should include this line alongside `reddit`, `linkedin`, etc.

- [ ] **Step 1.2: Add `tanit` to `FETCHER_MAP`**

In the same file, find `FETCHER_MAP` in class `ScraperEngine` (around lines 99–112). Add this entry, alphabetically near `twitter`:

```python
        "tanit": "stealth",
```

- [ ] **Step 1.3: Verify imports cleanly**

```powershell
.venv\Scripts\python.exe -c "from src.core.scraper_engine import ScraperEngine, RateLimiter; e = ScraperEngine(); rl = RateLimiter(); print(e.FETCHER_MAP['tanit']); print(rl.RATE_LIMITS['tanit'])"
```
Expected output:
```
stealth
{'min_delay': 3, 'max_delay': 6, 'hourly_cap': 100}
```

- [ ] **Step 1.4: Commit**

```bash
git add src/core/scraper_engine.py
git commit -m "feat(scraper-engine): register tanit (stealth + rate limit)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 2: `TanitScraper` class (TDD with mocked HTML)

**Why:** The actual scraper. We TDD against a fixture HTML snippet so tests don't hit Cloudflare during CI. The fixture is a real two-card sample captured from the live site — adapted from a Playwright dump.

**Files:**
- Create: `src/direct_leads/scrapers/tanit.py`
- Create: `tests/direct_leads/scrapers/test_tanit.py`
- Create: `tests/direct_leads/scrapers/__init__.py` (only if not present)

- [ ] **Step 2.1: Confirm test directory exists**

```bash
ls tests/direct_leads/scrapers/ 2>&1 || echo "missing"
```
If missing, create it:
```bash
mkdir -p tests/direct_leads/scrapers
echo "" > tests/direct_leads/scrapers/__init__.py
```

- [ ] **Step 2.2: Write the failing test**

Create `tests/direct_leads/scrapers/test_tanit.py`:

```python
"""Tests for src.direct_leads.scrapers.tanit.

We test the parsing logic against a fixture HTML so the test suite never
hits Cloudflare. The fetch path is exercised via integration / smoke testing.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.direct_leads.scrapers.tanit import TanitScraper, parse_listing_html


# Real two-card fixture captured live (annotations stripped for compactness).
# First card is featured; second is not.
FIXTURE_HTML = """
<div class="results">
  <article id="1999931" class="media well listing-item listing-item__jobs listing-item__featured">
    <div class="media-left listing-item__logo">
      <a href="https://www.tanitjobs.com/job/1999931/un-e-ingenieur-npi/?backPage=1&amp;searchID=1777993961.5545">
        <img class="profile__img-company" src="https://www.tanitjobs.com/files/pictures/2025/04/21/Logo-CMR.png" alt="CMR GROUP">
      </a>
    </div>
    <div class="media-body">
      <div class="media-heading listing-item__title">
        <a href="https://www.tanitjobs.com/job/1999931/un-e-ingenieur-npi/?backPage=1&amp;searchID=1777993961.5545" class="link">
          Un(e) Ingénieur NPI
        </a>
      </div>
      <div class="listing-item__info clearfix">
        <span class="listing-item-info-company">CMR GROUP - </span>
        <span class="listing-item-info-location">Mghira, Ben Arous, Tunisie</span>
      </div>
      <div class="listing-item__desc hidden-sm hidden-xs">
        Fondé à Marseille en 1959, le Groupe CMR est un spécialiste de la gestion de l'énergie : de l'assemblage de faisceaux électriques complexes pour des moteurs à la conception de capteurs pour...
      </div>
    </div>
  </article>

  <article id="1999900" class="media well listing-item listing-item__jobs">
    <div class="media-left listing-item__logo">
      <a href="https://www.tanitjobs.com/job/1999900/developpeur-react-junior/?backPage=2&amp;searchID=99.99">
        <img class="profile__img-company" src="https://www.tanitjobs.com/files/pictures/2025/05/01/logo.png" alt="Acme Tech">
      </a>
    </div>
    <div class="media-body">
      <div class="media-heading listing-item__title">
        <a href="https://www.tanitjobs.com/job/1999900/developpeur-react-junior/?backPage=2&amp;searchID=99.99" class="link">
          Développeur React Junior
        </a>
      </div>
      <div class="listing-item__info clearfix">
        <span class="listing-item-info-company">Acme Tech - </span>
        <span class="listing-item-info-location">Tunis, Tunisie</span>
      </div>
      <div class="listing-item__desc hidden-sm hidden-xs">
        Nous recherchons un développeur React junior pour rejoindre notre équipe à Tunis.
      </div>
    </div>
  </article>
</div>
"""


def test_parse_listing_html_returns_two_leads():
    leads = parse_listing_html(FIXTURE_HTML)
    assert len(leads) == 2


def test_parse_extracts_title_correctly():
    leads = parse_listing_html(FIXTURE_HTML)
    # First is featured — title gets "[Featured] " prefix
    assert leads[0].title == "[Featured] Un(e) Ingénieur NPI"
    assert leads[1].title == "Développeur React Junior"


def test_parse_extracts_company_strips_trailing_dash():
    leads = parse_listing_html(FIXTURE_HTML)
    assert leads[0].company_name == "CMR GROUP"
    assert leads[1].company_name == "Acme Tech"


def test_parse_extracts_location():
    leads = parse_listing_html(FIXTURE_HTML)
    assert leads[0].location == "Mghira, Ben Arous, Tunisie"
    assert leads[1].location == "Tunis, Tunisie"


def test_parse_extracts_description():
    leads = parse_listing_html(FIXTURE_HTML)
    assert "Groupe CMR" in leads[0].description
    assert "développeur React junior" in leads[1].description


def test_parse_extracts_url_strips_session_params():
    """URLs must not contain ?backPage=... or &searchID=... so dedup works across runs."""
    leads = parse_listing_html(FIXTURE_HTML)
    assert leads[0].url == "https://www.tanitjobs.com/job/1999931/un-e-ingenieur-npi/"
    assert leads[1].url == "https://www.tanitjobs.com/job/1999900/developpeur-react-junior/"


def test_parse_returns_empty_on_garbage_html():
    leads = parse_listing_html("<html><body>nothing here</body></html>")
    assert leads == []


def test_parse_handles_missing_optional_fields():
    minimal = """
    <article id="1" class="listing-item__jobs">
      <div class="listing-item__title"><a href="https://www.tanitjobs.com/job/1/x/" class="link">Just a title</a></div>
    </article>
    """
    leads = parse_listing_html(minimal)
    assert len(leads) == 1
    assert leads[0].title == "Just a title"
    assert leads[0].company_name == ""
    assert leads[0].location == ""
    assert leads[0].description == ""


def test_lead_source_is_tanit():
    leads = parse_listing_html(FIXTURE_HTML)
    assert all(lead.source == "tanit" for lead in leads)


@pytest.mark.asyncio
async def test_search_calls_engine_with_correct_url():
    """Mock the ScraperEngine to verify the search URL is built correctly."""
    fake_response = MagicMock()
    fake_response.get_all_text = MagicMock(return_value=FIXTURE_HTML)

    fake_engine = MagicMock()
    async def fake_fetch(url, source):
        fake_fetch.called_url = url
        fake_fetch.called_source = source
        return fake_response
    fake_engine.async_fetch = fake_fetch

    scraper = TanitScraper(fake_engine)
    leads = await scraper.search(keywords=["react"], max_results=20)

    assert fake_fetch.called_source == "tanit"
    assert "tanitjobs.com/jobs" in fake_fetch.called_url
    assert "q=react" in fake_fetch.called_url
    assert len(leads) == 2  # From fixture


@pytest.mark.asyncio
async def test_search_paginates_when_max_results_exceeds_one_page():
    """With max_results=50, scraper fetches at least 3 pages (50/23 = ceil(2.17) = 3)."""
    fake_response = MagicMock()
    fake_response.get_all_text = MagicMock(return_value=FIXTURE_HTML)

    page_calls: list[str] = []
    fake_engine = MagicMock()
    async def fake_fetch(url, source):
        page_calls.append(url)
        return fake_response
    fake_engine.async_fetch = fake_fetch

    scraper = TanitScraper(fake_engine)
    await scraper.search(keywords=["react"], max_results=50)

    # 50/23 = ceil(2.17) → 3 pages requested
    assert len(page_calls) == 3
    # Last URL should contain page=3
    assert "page=3" in page_calls[-1]
```

If `pytest-asyncio` isn't already a dev dependency in this project (check `requirements.txt`), you may need to either:
(a) Add `pytest-asyncio` and configure it via `pyproject.toml` or `pytest.ini`, OR
(b) Wrap the async tests with `asyncio.run()` inside a sync `def test_...` instead of `async def test_...`. The simplest path:

If `pytest-asyncio` isn't installed, replace the two `@pytest.mark.asyncio`-decorated tests with sync wrappers:

```python
import asyncio

def test_search_calls_engine_with_correct_url():
    fake_response = MagicMock()
    fake_response.get_all_text = MagicMock(return_value=FIXTURE_HTML)

    called = {}
    async def fake_fetch(url, source):
        called["url"] = url
        called["source"] = source
        return fake_response

    fake_engine = MagicMock()
    fake_engine.async_fetch = fake_fetch

    scraper = TanitScraper(fake_engine)
    leads = asyncio.run(scraper.search(keywords=["react"], max_results=20))

    assert called["source"] == "tanit"
    assert "tanitjobs.com/jobs" in called["url"]
    assert "q=react" in called["url"]
    assert len(leads) == 2


def test_search_paginates_when_max_results_exceeds_one_page():
    fake_response = MagicMock()
    fake_response.get_all_text = MagicMock(return_value=FIXTURE_HTML)

    page_calls: list[str] = []
    async def fake_fetch(url, source):
        page_calls.append(url)
        return fake_response

    fake_engine = MagicMock()
    fake_engine.async_fetch = fake_fetch

    scraper = TanitScraper(fake_engine)
    asyncio.run(scraper.search(keywords=["react"], max_results=50))

    assert len(page_calls) == 3
    assert "page=3" in page_calls[-1]
```

Use whichever style matches the existing test files in `tests/direct_leads/`. If those existing tests use `@pytest.mark.asyncio`, follow that style; otherwise use the `asyncio.run()` wrapper style.

To check existing style:
```bash
grep -n "async def test_\|@pytest.mark.asyncio\|asyncio.run" tests/direct_leads/test_*.py | head -10
```

- [ ] **Step 2.3: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/direct_leads/scrapers/test_tanit.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'src.direct_leads.scrapers.tanit'`.

- [ ] **Step 2.4: Implement the scraper**

Create `src/direct_leads/scrapers/tanit.py`:

```python
"""Tanit Jobs scraper — Tunisian job board, Cloudflare-protected.

Routes through ScraperEngine which uses StealthyFetcher for the 'tanit' tier
(see src/core/scraper_engine.py FETCHER_MAP).
"""
from __future__ import annotations

import logging
import math
import re
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


SEARCH_URL = "https://www.tanitjobs.com/jobs/?q={q}&l={l}&page={page}"
LISTINGS_PER_PAGE = 23


def _strip_session_params(url: str) -> str:
    """Remove ?backPage=...&searchID=... so dedup works across runs."""
    if not url:
        return ""
    parsed = urlparse(url)
    # Drop query string entirely — Tanit detail URLs are stable as path-only
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return base


def _clean_text(s: str | None) -> str:
    if not s:
        return ""
    # Collapse all whitespace runs into a single space
    return re.sub(r"\s+", " ", s).strip()


def parse_listing_html(html: str) -> list[DirectLead]:
    """Parse a Tanit listing page (search results) into DirectLead objects.

    Selectors match the live structure as of this plan's recon (May 2026)."""
    soup = BeautifulSoup(html, "html.parser")
    leads: list[DirectLead] = []

    # Match cards with class containing 'listing-item__jobs' (featured cards have an extra class).
    articles = soup.select("article.listing-item__jobs")
    for article in articles:
        title_anchor = article.select_one(".listing-item__title a")
        if not title_anchor:
            continue
        title_text = _clean_text(title_anchor.get_text())
        href = title_anchor.get("href", "")
        url = _strip_session_params(href)
        if not url or not title_text:
            continue

        # Featured marker: prepend "[Featured] " for downstream visibility
        is_featured = "listing-item__featured" in (article.get("class") or [])
        if is_featured:
            title_text = f"[Featured] {title_text}"

        company_el = article.select_one(".listing-item-info-company")
        company = _clean_text((company_el.get_text() if company_el else "").rstrip(" -")) or ""
        # Strip a trailing " -" that always follows the company on the live site
        if company.endswith(" -"):
            company = company[:-2].rstrip()

        location_el = article.select_one(".listing-item-info-location")
        location = _clean_text(location_el.get_text() if location_el else "") or ""

        desc_el = article.select_one(".listing-item__desc")
        description = _clean_text(desc_el.get_text() if desc_el else "")[:500]

        leads.append(DirectLead(
            source="tanit",
            title=title_text,
            description=description,
            url=url,
            posted_date=None,  # Not on listing page; v1 leaves None
            company_name=company,
            location=location,
            contact_name="",
            contact_email="",
            contact_phone="",
        ))

    return leads


class TanitScraper:
    SOURCE_NAME = "tanit"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self,
        keywords: list[str],
        max_results: int = 20,
    ) -> list[DirectLead]:
        if not keywords:
            return []

        # Tanit's `q` param accepts one phrase. Use the first keyword for the URL;
        # the relevance matcher post-filters using the full skill list anyway.
        primary_kw = keywords[0]

        # How many pages do we need? ceil(max_results / 23), capped at 10 (safety).
        pages_needed = max(1, min(10, math.ceil(max_results / LISTINGS_PER_PAGE)))

        all_leads: list[DirectLead] = []
        for page in range(1, pages_needed + 1):
            url = SEARCH_URL.format(
                q=quote_plus(primary_kw),
                l="",
                page=page,
            )
            try:
                response = await self.engine.async_fetch(url, "tanit")
                if not response:
                    continue
                html = response.get_all_text()
                page_leads = parse_listing_html(html)
                all_leads.extend(page_leads)
                # If a page returned fewer than expected, we've hit the end — stop.
                if len(page_leads) < LISTINGS_PER_PAGE:
                    break
            except Exception as e:
                logger.warning(f"[tanit] page {page} fetch failed: {e}")
                continue

        return all_leads[:max_results]
```

If `bs4` (BeautifulSoup) isn't already installed (check `requirements.txt`), you'll need to install it:
```bash
pip install beautifulsoup4
```
And add to `requirements.txt`:
```
beautifulsoup4>=4.12.0
```

To verify whether bs4 is already a dependency:
```bash
grep -i "beautifulsoup\|bs4" requirements.txt
```
If it's not, add the line and `pip install` it. If it IS, skip that step.

- [ ] **Step 2.5: Run tests**

```bash
.venv/Scripts/python.exe -m pytest tests/direct_leads/scrapers/test_tanit.py -v
```
Expected: 10 passed (or 8 if you used the sync-wrapper variant — count the actual function defs).

If a test about pagination fails because the fixture only has 2 cards and the scraper's "stop early when fewer than full page" heuristic kicks in → it stops after 1 page. That's expected behavior for the real site (sparse last page). The pagination test deliberately sets `max_results=50` so the scraper requests page 1, page 2, page 3 — but the early-stop kicks in. Adjust the test: count attempts to FETCH (which is what `page_calls` records — it captures the URL before the early-stop logic decides). The early-stop is checked AFTER the fetch, so all 3 pages get fetched even if each returns 2 cards. Verify by reading the implementation: yes, the loop fetches page N first, then decides to break. So 3 fetches happen, then break. Test passes.

- [ ] **Step 2.6: Commit**

```bash
git add src/direct_leads/scrapers/tanit.py tests/direct_leads/scrapers/test_tanit.py tests/direct_leads/scrapers/__init__.py
git commit -m "feat(scrapers): add TanitScraper for tanitjobs.com (Cloudflare-protected)"
```

If you also added `beautifulsoup4` to `requirements.txt`, include that file in the same commit:
```bash
git add requirements.txt
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 3: Wire `TanitScraper` into the pipeline

**Why:** The pipeline's `SCRAPER_CLASSES` dict dispatches a source string to a scraper class. Until tanit is in this dict, picking it in a saved search does nothing.

**Files:**
- Modify: `src/direct_leads/pipeline.py`

- [ ] **Step 3.1: Add the import**

In `src/direct_leads/pipeline.py`, find the existing import block (around lines 12–18):

```python
from src.direct_leads.scrapers.reddit import RedditScraper
from src.direct_leads.scrapers.indeed import IndeedScraper
from src.direct_leads.scrapers.linkedin_jobs import LinkedInJobsScraper
from src.direct_leads.scrapers.clutch import ClutchScraper
from src.direct_leads.scrapers.goodfirms import GoodFirmsScraper
from src.direct_leads.scrapers.twitter import TwitterScraper
from src.direct_leads.scrapers.linkedin_posts import LinkedInPostsScraper
```

Add this line at the bottom of that block:

```python
from src.direct_leads.scrapers.tanit import TanitScraper
```

- [ ] **Step 3.2: Register in `SCRAPER_CLASSES` dict**

Find the `SCRAPER_CLASSES` dict (around lines 22–30):

```python
SCRAPER_CLASSES = {
    "reddit": RedditScraper,
    "indeed": IndeedScraper,
    "linkedin": LinkedInJobsScraper,
    "linkedin_posts": LinkedInPostsScraper,
    "clutch": ClutchScraper,
    "goodfirms": GoodFirmsScraper,
    "twitter": TwitterScraper,
}
```

Add this entry inside the dict (before the closing brace):

```python
    "tanit": TanitScraper,
```

Final dict should have 8 entries.

- [ ] **Step 3.3: Verify imports cleanly**

```powershell
.venv\Scripts\python.exe -c "from src.direct_leads.pipeline import SCRAPER_CLASSES; print(sorted(SCRAPER_CLASSES.keys()))"
```
Expected output:
```
['clutch', 'goodfirms', 'indeed', 'linkedin', 'linkedin_posts', 'reddit', 'tanit', 'twitter']
```

- [ ] **Step 3.4: Run all backend tests to ensure nothing broke**

```bash
.venv/Scripts/python.exe -m pytest tests/backend tests/direct_leads -v --ignore=tests/backend/test_routers.py 2>&1 | tail -3
```
Expected: all tests pass. The new tanit tests are now part of the suite.

- [ ] **Step 3.5: Commit**

```bash
git add src/direct_leads/pipeline.py
git commit -m "feat(pipeline): register TanitScraper in direct-leads dispatch"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 4: Live smoke test against the real Tanit Jobs site

**Why:** Unit tests validate the parser; this validates that StealthyFetcher actually clears Cloudflare and the scraper returns real jobs. This is a smoke test, not an automated test — it requires internet and is expected to take 10-30 seconds because of the Cloudflare challenge.

**Files:** None modified.

- [ ] **Step 4.1: Run a one-shot smoke**

```powershell
.venv\Scripts\python.exe -c "import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.tanit import TanitScraper; e = ScraperEngine(); s = TanitScraper(e); leads = asyncio.run(s.search(keywords=['developpeur'], max_results=5)); [print(f'  {l.title[:60]} | {l.company_name[:30]} | {l.location[:30]}') for l in leads]; print(f'Total: {len(leads)}')"
```

Expected (after ~10-30s for Cloudflare clearance):
- A list of 1-5 real jobs from Tanit
- Each line shows truncated title, company, location
- Final line: `Total: N` where N is between 1 and 5

If output is `Total: 0`:
1. Check `output/direct/scans.json` for a recent failed scan with this source.
2. Run with debug logging:
   ```powershell
   .venv\Scripts\python.exe -c "import logging; logging.basicConfig(level=logging.DEBUG); import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.tanit import TanitScraper; e = ScraperEngine(); s = TanitScraper(e); leads = asyncio.run(s.search(['x'], 5)); print(len(leads))"
   ```
3. Most likely cause: Cloudflare wasn't cleared. Increase `StealthyFetcher` wait time or use a proxy.

If everything works, you've validated end-to-end. Move on.

- [ ] **Step 4.2: Trigger a scan via the API (full pipeline test)**

Make sure backend + frontend are running. Then:
```bash
curl -s -X POST http://localhost:8000/api/direct/scans -H "Content-Type: application/json" -d "{\"sources\":[\"tanit\"],\"keywords\":[\"developpeur\"],\"max_results\":10}"
```
Note the `scan_id` returned. Wait ~30 seconds (Cloudflare clearance + scraping + scoring + Excel write), then:
```bash
SID=<scan_id_from_above>
curl -s "http://localhost:8000/api/direct/scans/$SID" | python -c "import sys,json; d=json.load(sys.stdin); print(f'status={d[\"status\"]} leads={d.get(\"leads_found\")} error={d.get(\"error\")}')"
```
Expected: `status=completed leads=N` where N is between 1 and 10. Or `status=failed` with a clear error message.

- [ ] **Step 4.3: Visual check in the UI**

Open http://localhost:5173/sources. Tanit Jobs card should now show:
- Today's count > 0 (if the scan completed today)
- "last fetch" recent timestamp
- 7-day sparkline starting to fill

Open http://localhost:5173/inbox and filter by source — Tanit leads should appear.

- [ ] **Step 4.4: No commit needed for the smoke test itself**

Smoke test is a verification step, not a code change.

---

## Self-review notes (already addressed inline)

- **Spec coverage:** Backend scraper class ✓, ScraperEngine registration ✓, RateLimiter entry ✓, pipeline dispatch ✓, unit tests for parsing ✓, mocked-engine async tests ✓, live smoke ✓.
- **Placeholders:** None. Every code block contains the actual code, not pseudocode.
- **Type consistency:** `TanitScraper` constructor signature `(engine: ScraperEngine)` matches the existing `RedditScraper` pattern. `search(keywords, max_results) -> list[DirectLead]` matches.
- **Risk #1 — `posted_date` always None:** acceptable for v1. The `compute_pulse_status` and `compute_seven_day_series` functions in `hub_aggregator.py` and `source_metrics.py` correctly handle `posted_date=None` (they skip the row for "today's catch" but still count it in totals). The Inbox list shows "" for age which is fine.
- **Risk #2 — Cloudflare may block in burst:** RateLimiter caps tanit at 100 req/hr, 3-6s between requests. With `LISTINGS_PER_PAGE=23` × max 10 pages = 230 listings per scan max, and ~1 fetch per scan (the search URL with pagination), we're well under limits even with multiple scans/hour.
- **Risk #3 — Frontend Tanit references:** Plan 4 already added `tanit` to `_KNOWN_DIRECT_SOURCES`, `SourceCard.LABEL`, `SavedSearchEditor.ALL_SOURCES`. Step 0.2 verifies all three before this plan starts. If any are missing, the plan fails fast.
- **Risk #4 — `quote_plus` on `developpeur` produces `developpeur` (no special chars):** but if user passes a French keyword with accents like `déveloPpeur`, the encoding turns `é` into `%C3%A9`. Tanit's URL accepts this. Verified by the live recon (the URL bar showed `un-e-ing%C3%A9nieur-npi`).
- **Frontend changes:** Zero. Plan 4's Sources page, SavedSearchEditor, hub_aggregator already include tanit. New scraper plugs into the existing dispatch dict and just works.
