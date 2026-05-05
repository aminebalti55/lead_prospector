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
                response = await self.engine.async_fetch(url, "tanit")
                if not response:
                    continue
                html = response.get_all_text()
                page_leads = parse_listing_html(html)
                all_leads.extend(page_leads)
                # If a page returned zero results, we've hit the end — stop early.
                if len(page_leads) == 0:
                    break
            except Exception as e:
                logger.warning(f"[tanit] page {page} fetch failed: {e}")
                continue

        return all_leads[:max_results]
