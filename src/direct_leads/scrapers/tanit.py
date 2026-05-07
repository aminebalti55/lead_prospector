"""Tanit Jobs scraper — Tunisian job board, Cloudflare-protected.

Tanit's Cloudflare config is stricter than what ScraperEngine's default
StealthyFetcher call clears — we need `solve_cloudflare=True` and a wait_selector
for the listings article to appear. So this scraper bypasses engine.async_fetch
and calls StealthyFetcher directly with tuned kwargs, while still using the
engine's rate limiter for politeness.
"""
from __future__ import annotations

import logging
import math
import re
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup
from scrapling import StealthyFetcher

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


SEARCH_URL = "https://www.tanitjobs.com/jobs/?q={q}&l={l}&page={page}"
LISTINGS_PER_PAGE = 23

# Software-related stems to keep, in addition to the user's literal keywords.
# Tanit's site search is weak — it returns "femmes de ménage" and other
# unrelated listings even when q=react. So we client-side filter every
# parsed lead against these stems plus the user's exact search terms.
# Lowercase, accent-folded comparisons.
_SOFTWARE_STEMS = (
    "developer", "developpeur", "développeur", "dev",
    "engineer", "ingenieur", "ingénieur", "engineering",
    "software", "logiciel", "informatique",
    "frontend", "front-end", "front end",
    "backend", "back-end", "back end",
    "fullstack", "full-stack", "full stack",
    "devops", "sysadmin", "site reliability", "sre",
    "data scientist", "data engineer", "data analyst",
    "machine learning", "ml", "ai", "artificial intelligence",
    "react", "next", "nextjs", "next.js",
    "vue", "angular", "svelte",
    "node", "nodejs", "node.js",
    "python", "django", "fastapi", "flask",
    "java", "spring",
    "kotlin", "scala", "rust", "golang",
    ".net", "dotnet", "c#",
    "php", "laravel", "symfony",
    "ruby", "rails",
    "typescript", "javascript", "js", "ts",
    "html", "css", "sass",
    "qa", "tester", "test automation", "testeur",
    "mobile", "android", "ios", "swift", "flutter",
    "cloud", "aws", "azure", "gcp", "kubernetes", "docker",
    "wordpress", "shopify", "magento", "drupal",
    "tech lead", "team lead", "architect", "architecte",
    "cto", "ctostartup", "founding engineer",
)


def _normalize(text: str) -> str:
    """Lowercase + strip French/Tunisian accents for keyword matching."""
    import unicodedata
    out = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in out if not unicodedata.combining(c)).lower()


def _is_software_role(title: str, description: str, user_keywords: list[str]) -> bool:
    """True if the listing is plausibly software-related.

    Match against (a) the user's literal search keywords, and (b) a fixed
    set of software-engineering stems. We deliberately keep the stem list
    broad so cross-domain dev work (game dev, data eng, mobile, devops…)
    isn't accidentally excluded.
    """
    haystack = _normalize(f"{title} {description}")
    stems = [_normalize(k) for k in user_keywords] + [_normalize(s) for s in _SOFTWARE_STEMS]
    return any(s and s in haystack for s in stems)


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
        company = _clean_text((company_el.get_text() if company_el else "")) or ""
        # Strip a trailing " -" that always follows the company on the live site
        if company.endswith(" -"):
            company = company[:-2].rstrip()
        elif company.endswith("-"):
            company = company[:-1].rstrip()

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
                # Rate-limit via the engine's limiter (don't spam Tanit), but
                # call StealthyFetcher directly to pass Cloudflare-bypass kwargs.
                await self.engine.rate_limiter.wait_async("tanit")
                self.engine.rate_limiter.record_request("tanit")
                response = await StealthyFetcher.async_fetch(
                    url,
                    solve_cloudflare=True,
                    wait_selector="article.listing-item__jobs",
                    wait=3000,
                    network_idle=True,
                    google_search=True,
                )
                if not response:
                    continue
                # Use html_content (raw HTML) not get_all_text (strips tags)
                html = (
                    response.html_content
                    if getattr(response, "html_content", None)
                    else (response.body or b"").decode("utf-8", errors="replace")
                )
                page_leads = parse_listing_html(str(html))
                # Tanit's q-param filter is too loose — cleaning, sales, and
                # admin jobs slip through. Drop anything that doesn't look
                # software-related.
                before = len(page_leads)
                page_leads = [
                    l for l in page_leads
                    if _is_software_role(l.title, l.description, keywords)
                ]
                dropped = before - len(page_leads)
                if dropped:
                    logger.info(f"[tanit] dropped {dropped} non-software listings on page {page}")
                all_leads.extend(page_leads)
                # If a page returned zero results, we've hit the end — stop early.
                if before == 0:
                    break
            except Exception as e:
                logger.warning(f"[tanit] page {page} fetch failed: {e}")
                continue

        return all_leads[:max_results]
