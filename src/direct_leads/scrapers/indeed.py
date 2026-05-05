"""Indeed scraper — heavy Cloudflare/anti-bot.

Indeed's bot wall is stricter than the engine's default stealth fetch — needs
`solve_cloudflare=True` plus a wait_selector on the result cards. Same pattern
as Tanit: bypass engine.async_fetch and call StealthyFetcher directly with
tuned kwargs, while still honoring the engine's rate limiter.

Selectors are stable attributes (data-jk, data-testid) instead of obfuscated
.css-XXX classes, which Indeed regenerates on every redesign.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from scrapling import StealthyFetcher

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


def _clean_text(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def _parse_date(text: str) -> datetime | None:
    text = text.lower().strip()
    if not text:
        return None
    if "just" in text or "today" in text:
        return datetime.now()
    match = re.search(r"(\d+)\s*day", text)
    if match:
        return datetime.now() - timedelta(days=int(match.group(1)))
    match = re.search(r"(\d+)\s*hour", text)
    if match:
        return datetime.now() - timedelta(hours=int(match.group(1)))
    return None


def parse_listing_html(html: str) -> list[DirectLead]:
    """Parse an Indeed search-results page into DirectLead objects.

    Selectors verified live (May 2026): cards live under div.job_seen_beacon,
    every job exposes data-jk for a stable URL, and field bodies hang off
    data-testid attributes that survive redesigns."""
    soup = BeautifulSoup(html, "html.parser")
    leads: list[DirectLead] = []
    seen_jk: set[str] = set()

    cards = soup.select("div.job_seen_beacon")
    if not cards:
        # Fallback: any element containing a data-jk anchor
        anchors = soup.select("a[data-jk]")
        cards = [a.find_parent("div") for a in anchors]
        cards = [c for c in cards if c is not None]

    for card in cards:
        jk_anchor = card.select_one("a[data-jk]")
        if not jk_anchor:
            continue
        jk = jk_anchor.get("data-jk", "")
        if not jk or jk in seen_jk:
            continue
        seen_jk.add(jk)

        title_el = card.select_one("h2.jobTitle a") or card.select_one("h2.jobTitle")
        title = _clean_text(title_el.get_text() if title_el else "")
        if not title:
            continue

        url = f"https://www.indeed.com/viewjob?jk={jk}"

        company_el = card.select_one('[data-testid="company-name"]')
        company = _clean_text(company_el.get_text() if company_el else "")

        loc_el = card.select_one('[data-testid="text-location"]')
        location = _clean_text(loc_el.get_text() if loc_el else "")

        snippet_el = card.select_one('[data-testid="job-snippet-renderer"]')
        description = _clean_text(snippet_el.get_text() if snippet_el else "")[:2000] or title

        date_el = card.select_one("span.date")
        posted_date = _parse_date(_clean_text(date_el.get_text() if date_el else ""))

        leads.append(DirectLead(
            source="indeed",
            title=title,
            description=description,
            url=url,
            posted_date=posted_date,
            company_name=company,
            location=location,
        ))

    return leads


class IndeedScraper:
    SOURCE_NAME = "indeed"

    COUNTRY_DOMAINS = {
        "US": "www.indeed.com",
        "GB": "uk.indeed.com",
        "CA": "ca.indeed.com",
        "AU": "au.indeed.com",
        "FR": "fr.indeed.com",
        "DE": "de.indeed.com",
        "TN": "tn.indeed.com",
        "MA": "ma.indeed.com",
        "AE": "ae.indeed.com",
        "SA": "sa.indeed.com",
    }

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self,
        keywords: list[str],
        max_results: int = 20,
        country: str = "",
    ) -> list[DirectLead]:
        if not keywords:
            return []

        domain = self.COUNTRY_DOMAINS.get(country.upper(), "www.indeed.com") if country else "www.indeed.com"
        all_leads: list[DirectLead] = []

        for kw in keywords[:5]:
            query = f"{kw} freelance OR contract"
            url = f"https://{domain}/jobs?q={query.replace(' ', '+')}&sort=date&limit=25"
            try:
                await self.engine.rate_limiter.wait_async(self.SOURCE_NAME)
                self.engine.rate_limiter.record_request(self.SOURCE_NAME)
                response = await StealthyFetcher.async_fetch(
                    url,
                    solve_cloudflare=True,
                    wait_selector="div.job_seen_beacon",
                    wait=3000,
                    network_idle=True,
                    google_search=True,
                )
                if not response:
                    continue
                html = (
                    response.html_content
                    if getattr(response, "html_content", None)
                    else (response.body or b"").decode("utf-8", errors="replace")
                )
                page_leads = parse_listing_html(str(html))
                all_leads.extend(page_leads)
            except Exception as e:
                logger.warning(f"[indeed] search failed for '{kw}': {e}")
                continue
            if len(all_leads) >= max_results:
                break

        return all_leads[:max_results]
