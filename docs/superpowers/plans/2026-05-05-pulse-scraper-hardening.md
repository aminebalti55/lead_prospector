# Pulse — Scraper Hardening (GoodFirms / Indeed / LinkedIn / Nitter) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Commit message rule (project-wide):** NEVER add `Co-Authored-By: Claude`, "Generated with Claude Code", or any AI/assistant attribution to any commit message. Use the exact message in each task spec.

**Goal:** Eliminate the four remaining "silently returns zero leads" risks in the backend scraper layer — **GoodFirms** (URLs are 404 — needs rewrite to current category-based URL scheme), **Indeed** (relies on obfuscated CSS class names that break on every redesign — switch to stable `data-jk` and `data-testid` attributes), **LinkedIn** (`linkedin.com/jobs/search/` auth-walls all unauthenticated traffic — make the existing Google-search-fallback the primary path), and **Twitter** (only 2 Nitter instances; both can go down simultaneously — expand to 8+ instances with randomized rotation). After this plan, every backend scraper has a known-working code path verified live in May 2026.

**Architecture:**
- **GoodFirms rewrite:** keyword-to-service URL map. `react`/`shopify`/`wordpress`/etc map to `/companies/web-development-agency/<service>` or `/ecommerce-development-companies/<platform>`. Generic fallback `/companies/web-development-agency`. Parse `li.firm-wrapper` cards.
- **Indeed hardening:** card container = `div.job_seen_beacon` (or fallback to `[data-jk]` parent). Title = `h2.jobTitle a`. Company = `[data-testid="company-name"]`. Job ID via `data-jk` attribute (also doubles as the URL — `/viewjob?jk=<id>`). All four are stable.
- **LinkedIn flip:** make `_google_fallback` the primary `search()` implementation. The direct-LinkedIn attempt only succeeded ~30% of the time in production logs and currently returns 0 (auth wall). Remove the dead code path; rename for clarity.
- **Nitter rotation:** fixed list of 8 known-working instances + `twiiit.com` redirector. Try in randomized order; stop at first that returns valid HTML (presence of `<table class="tweet">` or `.timeline-item`).

**Tech Stack:** Python 3.12, Scrapling (StealthyFetcher / Fetcher), BeautifulSoup4, pytest. No new dependencies.

---

## Scope decision

This is **Plan 8 of 9+**. After this:

| # | Plan | Status |
|---|---|---|
| 1-7 | Foundation through Cold-outreach cleanup | ✅ |
| **8 (this)** | **Scraper hardening (GoodFirms + Indeed + LinkedIn + Nitter)** | About to ship |
| 9 | Supabase migration | Pending — final plan |

**Per user direction A:** LinkedIn MCP integration is **NOT** in this plan. The Pulse backend keeps Google-fallback as its automated LinkedIn path. The user's authenticated LinkedIn MCP is a manual chat-only premium search tool, not a backend integration.

---

## File structure (this plan)

**Modified backend files:**
- `src/direct_leads/scrapers/goodfirms.py` — full rewrite with new URL scheme + selectors
- `src/direct_leads/scrapers/indeed.py` — switch to stable selectors (`data-jk`, `h2.jobTitle a`, `data-testid`, `div.job_seen_beacon`)
- `src/direct_leads/scrapers/linkedin_jobs.py` — Google fallback becomes primary; drop dead direct-fetch code
- `src/direct_leads/scrapers/twitter.py` — expanded Nitter list (8 instances), randomized order, stop on first success

**Test files:** None added (we trust live smoke per Tanit's pattern; no false-green mocks).

**Untouched (preserved):**
- All Plan 1-7 backend code: hub, sources, settings, templates, outreach routers; Plan 7's Reddit/Yelp/BBB/Google Maps/Clutch fixes; the LinkedIn URL strip helper.
- The Tanit scraper (the reference impl).

---

## Conventions

- **GoodFirms keyword→URL map:** dictionary lookup with sensible default. Unknown keywords fall back to the generic web-development-agency directory (still useful — broad pool).
- **Indeed pagination:** `&start=N` (N = 0, 10, 20, …). Stop when a page returns < 10 cards or no new job IDs (dedup by `data-jk`).
- **LinkedIn URL path:** continue stripping session params via `_strip_linkedin_session_params()` (added in Plan 7).
- **Nitter probe order:** randomized per call. First instance that returns HTML containing `class="timeline-item"` or `class="tweet-link"` wins. All others tried only if probe fails.
- **No retry inside scrapers:** the engine already has `async_fetch_with_retry`. Don't double-retry.
- **Live smoke after each task:** run the actual scraper against the live site to confirm > 0 leads. Failure = task not done.

---

## Pre-flight

- [ ] **Step 0.1: Verify Plan 7 is committed and the branch is clean**

```bash
cd C:\Users\JIMMY\lead_prospector
git status
git log --oneline pulse-foundation -5
```
Expected: working tree clean. Latest commit is `a67afb2 feat(cli): derive --niches choices from config so all 10 are available` or later.

- [ ] **Step 0.2: Confirm 318 tests still pass**

```bash
.venv/Scripts/python.exe -m pytest tests/backend tests/cold_outreach tests/direct_leads --ignore=tests/backend/test_routers.py 2>&1 | tail -3
```
Expected: `318 passed, 0 failed`.

---

## Task 1: Rewrite GoodFirms scraper for the current URL scheme

**Why:** Live recon (May 2026) shows `https://www.goodfirms.co/projects?q=...` returns 404. The current scraper produces zero leads. The site's actual structure uses category-based URLs:
- `/companies/web-development-agency` (155 firm cards on the page)
- `/companies/web-development-agency/<framework>` (e.g. `/wordpress`, `/react`)
- `/ecommerce-development-companies/<platform>` (e.g. `/shopify`, `/woocommerce`)
- `/directory/languages/top-software-development-companies/<lang>` (e.g. `/python`, `/php`)

Each card is `li.firm-wrapper`. Inside: `.firm-name a` (title + profile URL), `.firm-short-description` (description).

**Files:**
- Modify: `src/direct_leads/scrapers/goodfirms.py` (full rewrite)

- [ ] **Step 1.1: Replace the file content**

Overwrite `src/direct_leads/scrapers/goodfirms.py` with:

```python
"""GoodFirms scraper — Tunisian/MENA-friendly B2B-services directory.

Verified live May 2026. Uses category-based URLs (the old /projects?q= path
is 404). Parses li.firm-wrapper cards for firm name + description + profile URL.

Cloudflare-protected → routed through ScraperEngine's stealth tier.
"""
from __future__ import annotations

import logging

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)

BASE_URL = "https://www.goodfirms.co"

# Map common dev keywords → live GoodFirms category URLs.
# Unknown keywords fall back to the broad web-development-agency directory.
_KEYWORD_TO_PATH: dict[str, str] = {
    # Languages
    "python": "/directory/languages/top-software-development-companies/python",
    "java": "/directory/languages/top-software-development-companies/java",
    "php": "/directory/languages/top-software-development-companies/php",
    "javascript": "/directory/languages/top-software-development-companies/javascript",
    "typescript": "/companies/web-development-agency",
    "react": "/directory/languages/top-software-development-companies/reactjs",
    "reactjs": "/directory/languages/top-software-development-companies/reactjs",
    "angular": "/directory/languages/top-software-development-companies/angularjs",
    "angularjs": "/directory/languages/top-software-development-companies/angularjs",
    "node": "/directory/languages/top-software-development-companies/node-js",
    "nodejs": "/directory/languages/top-software-development-companies/node-js",
    "node-js": "/directory/languages/top-software-development-companies/node-js",
    "vue": "/directory/languages/top-software-development-companies/vuejs",
    # Frameworks / platforms
    "net": "/directory/frameworks/top-software-development-companies/net",
    "dotnet": "/directory/frameworks/top-software-development-companies/net",
    "wordpress": "/companies/web-development-agency/wordpress",
    "drupal": "/companies/web-development-agency/drupal",
    "laravel": "/directory/frameworks/top-software-development-companies/laravel",
    # E-commerce
    "shopify": "/ecommerce-development-companies/shopify",
    "magento": "/ecommerce-development-companies/magento",
    "woocommerce": "/ecommerce-development-companies/woocommerce",
    # Mobile
    "android": "/directory/platform/app-development/android",
    "ios": "/directory/platform/app-development/iphone",
    "iphone": "/directory/platform/app-development/iphone",
    "flutter": "/directory/frameworks/app-development/flutter",
    # Other
    "blockchain": "/companies/blockchain-development-services",
    "ai": "/companies/web-development-agency",
    "ml": "/companies/web-development-agency",
}

_DEFAULT_PATH = "/companies/web-development-agency"


def _path_for_keyword(kw: str) -> str:
    """Map a keyword to a GoodFirms category URL path. Defaults to the broad
    web-development-agency directory."""
    key = kw.lower().strip()
    return _KEYWORD_TO_PATH.get(key, _DEFAULT_PATH)


class GoodFirmsScraper:
    SOURCE_NAME = "goodfirms"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        """Search GoodFirms category pages for B2B service providers.

        Each keyword maps to a directory URL. Default → web-development-agency.
        Selectors verified live May 2026: li.firm-wrapper, .firm-name a,
        .firm-short-description.
        """
        leads: list[DirectLead] = []
        seen_urls: set[str] = set()

        for kw in keywords[:5]:
            path = _path_for_keyword(kw)
            url = f"{BASE_URL}{path}"
            try:
                response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                if not response:
                    continue

                cards = response.css("li.firm-wrapper")
                if not cards:
                    logger.debug(f"GoodFirms returned no firm-wrapper cards for '{kw}' at {url}")
                    continue

                for card in cards:
                    try:
                        name_link = card.css(".firm-name a")
                        if not name_link:
                            continue
                        company_name = name_link[0].get_all_text().strip()
                        if not company_name:
                            continue
                        href = name_link[0].attrib.get("href", "")
                        detail_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                        if detail_url in seen_urls:
                            continue
                        seen_urls.add(detail_url)

                        desc_el = card.css(".firm-short-description")
                        description = desc_el[0].get_all_text().strip() if desc_el else ""

                        lead = DirectLead(
                            source="goodfirms",
                            title=f"{company_name} - {kw}",
                            description=description[:2000],
                            url=detail_url,
                            company_name=company_name,
                            location="",  # GoodFirms category pages don't show location per card
                        )
                        leads.append(lead)
                        if len(leads) >= max_results:
                            return leads[:max_results]
                    except Exception as e:
                        logger.debug(f"GoodFirms card parse error: {e}")
                        continue
            except Exception as e:
                logger.warning(f"GoodFirms search failed for '{kw}' at {url}: {e}")
                continue

        return leads[:max_results]
```

- [ ] **Step 1.2: Verify import**

```bash
.venv/Scripts/python.exe -c "from src.direct_leads.scrapers.goodfirms import GoodFirmsScraper, _path_for_keyword; print(_path_for_keyword('react')); print(_path_for_keyword('unknown'))"
```
Expected:
```
/directory/languages/top-software-development-companies/reactjs
/companies/web-development-agency
```

- [ ] **Step 1.3: Live smoke (CRITICAL — confirms the rewrite actually works)**

```bash
.venv/Scripts/python.exe -c "import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.goodfirms import GoodFirmsScraper; e = ScraperEngine(); s = GoodFirmsScraper(e); leads = asyncio.run(s.search(keywords=['react'], max_results=5)); [print(f'  {l.company_name[:40]} | {l.url[:80]}') for l in leads]; print(f'Total: {len(leads)}')" 2>&1 | tail -10
```

Expected: `Total: 1` to `Total: 5` with real GoodFirms company names. If `Total: 0`, debug — most likely cause is Cloudflare not clearing on first try (re-run; it's intermittent). The scraper-engine retries handle this.

If after 2 retries it's still zero, report DONE_WITH_CONCERNS noting the GoodFirms Cloudflare difficulty — the scraper code is structurally correct (verified by playwright recon) but live runtime may need a `solve_cloudflare=True` direct-StealthyFetcher upgrade similar to Tanit. That's a separate task.

- [ ] **Step 1.4: Commit**

```bash
git add src/direct_leads/scrapers/goodfirms.py
git commit -m "fix(goodfirms): rewrite for category URL scheme + verified May 2026 selectors"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 2: Harden Indeed scraper with stable selectors

**Why:** Indeed's CSS class names are obfuscated (e.g. `css-1h7lukg`, `jobTitle css-1abc23d`) and rotate on every redesign. The existing scraper's brittleness is a known problem from Plan 7 audit. The fix: use stable attribute selectors that Indeed has kept consistent for years:
- `div.job_seen_beacon` — card container (stable since 2019)
- `a[data-jk]` — every job listing has this attribute (the job key)
- `h2.jobTitle a` — title link (`jobTitle` class is stable, the random-suffix classes are not)
- `[data-testid="company-name"]` — company name (Indeed-internal QA hooks are stable)

**Files:**
- Modify: `src/direct_leads/scrapers/indeed.py`

- [ ] **Step 2.1: Read the current scraper**

```bash
cat src/direct_leads/scrapers/indeed.py
```

Note the existing class structure and what fields are populated.

- [ ] **Step 2.2: Replace the parse method (or full file if simpler)**

The fix is to update the selectors used in the card parse loop. Open `src/direct_leads/scrapers/indeed.py` and find where it iterates over cards and extracts fields. Replace the selectors as follows:

| Field | OLD selector (brittle) | NEW selector (stable) |
|---|---|---|
| Card container | `div.tapItem`, `div.cardOutline`, etc. | `div.job_seen_beacon` (with fallback to `[data-jk]` parent) |
| Title text | various `.css-XXX` | `h2.jobTitle a` |
| Job URL | various | construct from `data-jk`: `https://www.indeed.com/viewjob?jk=<jk>` |
| Company | various `.css-XXX` | `[data-testid="company-name"]` |
| Location | various `.css-XXX` | `[data-testid="text-location"]` |
| Snippet | various | `[data-testid="job-snippet-renderer"]` (then `.get_all_text()`) |

Concrete code: in the `_parse_results` (or equivalent) method, replace the card-iteration body with:

```python
        leads: list[DirectLead] = []
        seen_jk: set[str] = set()

        cards = response.css("div.job_seen_beacon")
        if not cards:
            # Fallback: walk up from the data-jk anchor
            jk_anchors = response.css("a[data-jk]")
            cards = [a.find_ancestor("div") for a in jk_anchors if hasattr(a, "find_ancestor")]
            cards = [c for c in cards if c is not None]

        for card in cards:
            try:
                jk_anchor = card.css("a[data-jk]")
                if not jk_anchor:
                    continue
                jk = jk_anchor[0].attrib.get("data-jk", "")
                if not jk or jk in seen_jk:
                    continue
                seen_jk.add(jk)

                title_el = card.css("h2.jobTitle a")
                title = title_el[0].get_all_text().strip() if title_el else ""
                if not title:
                    continue

                # Build a stable URL from data-jk (Indeed always exposes this path)
                url = f"https://www.indeed.com/viewjob?jk={jk}"

                company_el = card.css('[data-testid="company-name"]')
                company = company_el[0].get_all_text().strip() if company_el else ""

                loc_el = card.css('[data-testid="text-location"]')
                location = loc_el[0].get_all_text().strip() if loc_el else ""

                snippet_el = card.css('[data-testid="job-snippet-renderer"]')
                description = (
                    snippet_el[0].get_all_text().strip()[:2000]
                    if snippet_el
                    else title  # fallback: title-as-description (better than empty)
                )

                lead = DirectLead(
                    source="indeed",
                    title=title,
                    description=description,
                    url=url,
                    company_name=company,
                    location=location,
                )
                leads.append(lead)
            except Exception as e:
                logger.debug(f"Indeed card parse error: {e}")
                continue

        return leads
```

If the existing scraper has a different signature for `_parse_results` (e.g. accepts the page directly), preserve that signature. Only replace the inner card-iteration logic.

If the file uses a different parse function name, locate it via:
```bash
grep -n "def _parse\|def parse\|cards = " src/direct_leads/scrapers/indeed.py
```

- [ ] **Step 2.3: Verify import**

```bash
.venv/Scripts/python.exe -c "from src.direct_leads.scrapers.indeed import IndeedScraper; print('OK')"
```
Expected: `OK`

- [ ] **Step 2.4: Live smoke (CRITICAL)**

```bash
.venv/Scripts/python.exe -c "import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.indeed import IndeedScraper; e = ScraperEngine(); s = IndeedScraper(e); leads = asyncio.run(s.search(keywords=['react developer'], max_results=5)); [print(f'  {l.title[:60]} | {l.company_name[:30]}') for l in leads]; print(f'Total: {len(leads)}')" 2>&1 | tail -10
```

Expected: `Total: 1` to `Total: 5` with real Indeed job listings. If 0, Indeed has either fully blocked the scraper or the selectors changed AGAIN since recon. Report status accurately — don't claim success if the live test shows zero.

- [ ] **Step 2.5: Commit**

```bash
git add src/direct_leads/scrapers/indeed.py
git commit -m "fix(indeed): switch to stable selectors (data-jk, data-testid, job_seen_beacon)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 3: LinkedIn — make Google-fallback the primary path

**Why:** Live recon May 2026 confirms `https://www.linkedin.com/jobs/search/` redirects all unauthenticated traffic to `/authwall`. The existing scraper's direct fetch returns 0 results. The existing `_google_fallback()` method DOES work (uses `site:linkedin.com/jobs "<keyword>"` in Google search). Make it primary.

**Files:**
- Modify: `src/direct_leads/scrapers/linkedin_jobs.py`

- [ ] **Step 3.1: Read the current scraper**

```bash
cat src/direct_leads/scrapers/linkedin_jobs.py
```

Note the current `search()` method (which tries direct LinkedIn first, falls back to Google) and the `_google_fallback()` method.

- [ ] **Step 3.2: Make Google fallback the primary path**

In `src/direct_leads/scrapers/linkedin_jobs.py`, find the `async def search(self, keywords, max_results, country=None)` method. Replace its body to skip the direct-LinkedIn fetch entirely and call the existing fallback as the primary:

The replacement body (preserve the method signature and decorators):

```python
        # LinkedIn's public /jobs/search/ auth-walls all unauthenticated traffic
        # (verified May 2026). The Google index is the only reliable public
        # source for LinkedIn job URLs without an account.
        leads: list[DirectLead] = []
        for kw in keywords[:5]:
            try:
                batch = await self._google_fallback(kw, max_results)
                leads.extend(batch)
                if len(leads) >= max_results:
                    break
            except Exception as e:
                logger.warning(f"LinkedIn (Google) search failed for '{kw}': {e}")
                continue
        return leads[:max_results]
```

Keep the existing `_google_fallback()` method as-is — only change the `search()` body.

- [ ] **Step 3.3: Fix the source-name typo in `_google_fallback`**

Find this in `_google_fallback`:

```python
            response = await self.engine.async_fetch_with_retry(
                url, "google_maps"
            )  # use stealth for Google
```

Replace with:

```python
            response = await self.engine.async_fetch_with_retry(url, "linkedin")
```

(The `google_maps` source name was a copy-paste leftover that conflated rate-limiting buckets. LinkedIn's bucket is the right one.)

- [ ] **Step 3.4: Verify import**

```bash
.venv/Scripts/python.exe -c "from src.direct_leads.scrapers.linkedin_jobs import LinkedInJobsScraper; print('OK')"
```
Expected: `OK`

- [ ] **Step 3.5: Live smoke**

```bash
.venv/Scripts/python.exe -c "import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.linkedin_jobs import LinkedInJobsScraper; e = ScraperEngine(); s = LinkedInJobsScraper(e); leads = asyncio.run(s.search(keywords=['react developer'], max_results=5)); [print(f'  {l.title[:60]} | {l.url[:80]}') for l in leads]; print(f'Total: {len(leads)}')" 2>&1 | tail -10
```

Expected: `Total: 1` to `Total: 5` with linkedin.com/jobs/view/ URLs (Google search results). If 0, Google search may be rate-limiting — wait 30s and retry once.

- [ ] **Step 3.6: Commit**

```bash
git add src/direct_leads/scrapers/linkedin_jobs.py
git commit -m "fix(linkedin): make Google-fallback the primary path (direct auth-walls all anon)"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 4: Twitter — expanded Nitter rotation

**Why:** Existing scraper has only 2 Nitter instances hardcoded (`nitter.net`, `nitter.privacydev.net`). Both can be down simultaneously. Web-research May 2026 confirms these working alternatives:

```
xcancel.com
nitter.poast.org
nitter.privacyredirect.com
lightbrd.com
nitter.space
nitter.tiekoetter.com
nuku.trabun.org
nitter.catsarch.com
```

Plus `twiiit.com` is a redirector to whichever Nitter is up. Expand the list, randomize order per call, stop on first success.

**Files:**
- Modify: `src/direct_leads/scrapers/twitter.py`

- [ ] **Step 4.1: Read current scraper**

```bash
cat src/direct_leads/scrapers/twitter.py | head -50
```

Find where the Nitter instance list is defined (likely a module-level list called `NITTER_INSTANCES` or similar) and how `search()` iterates over them.

- [ ] **Step 4.2: Replace the instance list and iteration**

Find the existing instance list. It looks something like:

```python
NITTER_INSTANCES = ["https://nitter.net", "https://nitter.privacydev.net"]
```

Replace with:

```python
import random

# Public Nitter instances verified working May 2026.
# Source: https://gist.github.com/cmj/7dace466c983e07d4e3b13be4b786c29
# + status.d420.de tracker. Some instances rotate uptime — try in randomized
# order and stop at first success.
NITTER_INSTANCES = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.privacyredirect.com",
    "https://lightbrd.com",
    "https://nitter.space",
    "https://nitter.tiekoetter.com",
    "https://nuku.trabun.org",
    "https://nitter.catsarch.com",
]


def _shuffled_instances() -> list[str]:
    """Return Nitter instances in a randomized order so we don't always hammer the same one first."""
    pool = list(NITTER_INSTANCES)
    random.shuffle(pool)
    return pool
```

Then in the `search()` method, find the loop over instances and update it to use `_shuffled_instances()` and stop at first success. The pattern:

```python
        for kw in keywords[:5]:
            for instance in _shuffled_instances():
                url = f"{instance}/search?f=tweets&q={quote_plus(query)}"
                try:
                    response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                    if not response:
                        continue
                    html = (
                        response.html_content
                        if getattr(response, "html_content", None)
                        else (getattr(response, "body", b"") or b"").decode("utf-8", errors="replace")
                    )
                    # Probe: does the response contain Nitter tweet markup?
                    if "timeline-item" not in str(html) and "tweet-link" not in str(html):
                        continue  # this instance returned a stale/error page; try next
                    page_leads = self._parse_nitter(response, kw)
                    if page_leads:
                        leads.extend(page_leads)
                        break  # first instance with results wins for this keyword
                except Exception as e:
                    logger.debug(f"[twitter] instance {instance} failed: {e}")
                    continue
            if len(leads) >= max_results:
                break
        return leads[:max_results]
```

If the existing search method has a different shape, preserve it but apply the two key changes: (a) iterate `_shuffled_instances()` instead of `NITTER_INSTANCES` directly, and (b) probe the response for Nitter markup before treating it as a successful fetch.

- [ ] **Step 4.3: Verify import**

```bash
.venv/Scripts/python.exe -c "from src.direct_leads.scrapers.twitter import TwitterScraper, NITTER_INSTANCES; print(f'{len(NITTER_INSTANCES)} instances'); print('OK')"
```
Expected:
```
8 instances
OK
```

- [ ] **Step 4.4: Live smoke**

```bash
.venv/Scripts/python.exe -c "import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.twitter import TwitterScraper; e = ScraperEngine(); s = TwitterScraper(e); leads = asyncio.run(s.search(keywords=['hiring react'], max_results=5)); [print(f'  {l.title[:60]} | {l.url[:60]}') for l in leads]; print(f'Total: {len(leads)}')" 2>&1 | tail -10
```

Expected: `Total: 1+`. Nitter is volatile — 0 results may indicate ALL 8 instances are down at this moment. Try 30s later. If still 0 after retry, document as a known limitation (twiiit.com fallback could be added later).

- [ ] **Step 4.5: Commit**

```bash
git add src/direct_leads/scrapers/twitter.py
git commit -m "fix(twitter): rotate across 8 Nitter instances; probe for valid markup"
```

**Reminder: NO `Co-Authored-By` trailer.**

---

## Task 5: E2E smoke — full backend test + 4 live scraper smokes

- [ ] **Step 5.1: Run full backend test suite**

```bash
.venv/Scripts/python.exe -m pytest tests/backend tests/cold_outreach tests/direct_leads --ignore=tests/backend/test_routers.py 2>&1 | tail -3
```
Expected: 318 passed (same as Plan 7 baseline). 0 failed.

- [ ] **Step 5.2: Live scraper smokes (one-shot for each fixed scraper)**

Run each in turn. Each should return at least 1 lead (or report a known limitation):

```bash
echo "--- GoodFirms ---"
.venv/Scripts/python.exe -c "import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.goodfirms import GoodFirmsScraper; e = ScraperEngine(); s = GoodFirmsScraper(e); leads = asyncio.run(s.search(keywords=['react'], max_results=3)); print(f'  Total: {len(leads)}'); [print(f'  {l.company_name[:40]}') for l in leads]" 2>&1 | tail -7

echo "--- Indeed ---"
.venv/Scripts/python.exe -c "import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.indeed import IndeedScraper; e = ScraperEngine(); s = IndeedScraper(e); leads = asyncio.run(s.search(keywords=['react developer'], max_results=3)); print(f'  Total: {len(leads)}'); [print(f'  {l.title[:60]}') for l in leads]" 2>&1 | tail -7

echo "--- LinkedIn (via Google) ---"
.venv/Scripts/python.exe -c "import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.linkedin_jobs import LinkedInJobsScraper; e = ScraperEngine(); s = LinkedInJobsScraper(e); leads = asyncio.run(s.search(keywords=['react developer'], max_results=3)); print(f'  Total: {len(leads)}'); [print(f'  {l.title[:60]}') for l in leads]" 2>&1 | tail -7

echo "--- Twitter (via Nitter rotation) ---"
.venv/Scripts/python.exe -c "import asyncio; from src.core.scraper_engine import ScraperEngine; from src.direct_leads.scrapers.twitter import TwitterScraper; e = ScraperEngine(); s = TwitterScraper(e); leads = asyncio.run(s.search(keywords=['hiring react'], max_results=3)); print(f'  Total: {len(leads)}'); [print(f'  {l.title[:60]}') for l in leads]" 2>&1 | tail -7
```

Expected: all four show `Total:` > 0. Document any that show 0 with a note (likely transient — Nitter and Cloudflare can hiccup intermittently).

- [ ] **Step 5.3: No commit needed for smoke verification**

If all four scrapers return non-zero leads, the plan is fully shipped. If any return 0 due to transient site issues, retry once before reporting status.

---

## Self-review notes (already addressed inline)

- **Spec coverage:** GoodFirms rewrite ✓ (T1), Indeed stable selectors ✓ (T2), LinkedIn Google-primary ✓ (T3), Nitter rotation ✓ (T4), full smoke ✓ (T5).
- **Placeholders:** None. Every step has full code or exact replacements.
- **Type consistency:** All `async def search(keywords, max_results) -> list[DirectLead]` signatures preserved. `engine.async_fetch_with_retry(url, source)` consistent across all four fixes.
- **Risk #1 — GoodFirms Cloudflare:** the new code routes through `engine.async_fetch_with_retry` which uses `StealthyFetcher` for the `stealth` tier (Plan 7 set goodfirms tier to stealth). Should work. If Cloudflare is more aggressive than expected, T1 step 1.3 documents the fallback (use `solve_cloudflare=True` direct StealthyFetcher call like Tanit). That's a 5-line patch if needed.
- **Risk #2 — Indeed has its own anti-bot:** Indeed redesigned anti-bot in 2024-2025. The selectors I chose (data-jk, data-testid, job_seen_beacon) are the most stable but Indeed has been known to occasionally serve a "captcha" interstitial. The engine retries should handle transient issues; persistent blocking would require a `solve_cloudflare`-style upgrade.
- **Risk #3 — Google search rate limits LinkedIn fallback:** If Pulse runs many LinkedIn-via-Google searches per hour, Google can rate-limit. The engine's `linkedin` rate limit (3-6s, 100/hr) bounds this. Acceptable for solo use.
- **Risk #4 — All Nitter instances down simultaneously:** Possible. The `_shuffled_instances()` rotation maximizes coverage but if all 8 are down, the scraper returns 0. Add `twiiit.com` as a 9th fallback in a future polish task if this becomes frequent.
