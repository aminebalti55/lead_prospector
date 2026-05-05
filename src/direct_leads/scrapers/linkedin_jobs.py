"""LinkedIn jobs scraper — guest API endpoint.

LinkedIn's signed-in jobs page is auth-walled, but the platform exposes an
unauthenticated guest endpoint for the public jobs listings:

    GET /jobs-guest/jobs/api/seeMoreJobPostings/search
        ?keywords=<kw>&location=<loc>&start=<n>

It returns raw HTML containing `<li>` cards with title, company, location,
URL, and posted-date — no auth, no Cloudflare, no captcha. This is the
backend's primary path. Premium / authenticated searches go through the
user's LinkedIn MCP in chat (results land in output/direct/ via Inbox).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import quote, urlparse

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


GUEST_SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?keywords={kw}&location={loc}&start={start}"
    # f_TPR=r1209600 → posted in the last 14 days (in seconds).
    "&f_TPR=r1209600"
)
RESULTS_PER_PAGE = 10


COUNTRY_LOCATION_HINTS = {
    "TN": "Tunisia",
    "US": "United States",
    "GB": "United Kingdom",
    "FR": "France",
    "DE": "Germany",
    "CA": "Canada",
    "AU": "Australia",
    "AE": "United Arab Emirates",
    "SA": "Saudi Arabia",
    "MA": "Morocco",
    "DZ": "Algeria",
}


def _strip_linkedin_session_params(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _job_id_from_url(url: str) -> str:
    m = re.search(r"/jobs/view/[^/?]*?(\d{6,})", url)
    return m.group(1) if m else ""


def _parse_time(time_el) -> datetime | None:
    try:
        dt = time_el.attrib.get("datetime", "")
    except Exception:
        return None
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except Exception:
        return None


class LinkedInJobsScraper:
    SOURCE_NAME = "linkedin"

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

        location = COUNTRY_LOCATION_HINTS.get(country.upper(), "") if country else ""
        all_leads: list[DirectLead] = []
        seen_ids: set[str] = set()

        for kw in keywords[:3]:
            remaining = max_results - len(all_leads)
            if remaining <= 0:
                break
            pages_needed = max(1, (remaining + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
            for page in range(pages_needed):
                start = page * RESULTS_PER_PAGE
                url = GUEST_SEARCH_URL.format(
                    kw=quote(kw),
                    loc=quote(location),
                    start=start,
                )
                try:
                    await self.engine.rate_limiter.wait_async(self.SOURCE_NAME)
                    self.engine.rate_limiter.record_request(self.SOURCE_NAME)
                    response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                    if not response:
                        break
                    page_leads = self._parse_cards(response)
                    if not page_leads:
                        break
                    new_count = 0
                    for lead in page_leads:
                        key = _job_id_from_url(lead.url) or lead.url
                        if not key or key in seen_ids:
                            continue
                        seen_ids.add(key)
                        all_leads.append(lead)
                        new_count += 1
                        if len(all_leads) >= max_results:
                            break
                    if new_count == 0:
                        break
                except Exception as e:
                    logger.warning(f"[linkedin] search failed for '{kw}' page {page}: {e}")
                    break
                if len(all_leads) >= max_results:
                    break

        return all_leads[:max_results]

    def _parse_cards(self, response) -> list[DirectLead]:
        leads: list[DirectLead] = []
        try:
            cards = response.css("li")
        except Exception:
            return []

        for card in cards:
            try:
                title_el = self._first(card.css("h3.base-search-card__title")) or self._first(card.css("h3"))
                if not title_el:
                    continue
                title = title_el.get_all_text().strip()
                if not title:
                    continue

                link_el = self._first(card.css("a.base-card__full-link")) or self._first(card.css("a"))
                href = link_el.attrib.get("href", "") if link_el else ""
                stable_url = _strip_linkedin_session_params(href)
                if not _job_id_from_url(stable_url):
                    continue  # Skip cards without a stable job id

                company_el = (
                    self._first(card.css("h4.base-search-card__subtitle"))
                    or self._first(card.css("h4"))
                )
                company = company_el.get_all_text().strip() if company_el else ""

                loc_el = self._first(card.css("span.job-search-card__location"))
                location = loc_el.get_all_text().strip() if loc_el else ""

                date_el = self._first(card.css("time"))
                posted_date = _parse_time(date_el) if date_el else None

                leads.append(DirectLead(
                    source="linkedin",
                    title=title,
                    description=title,
                    url=stable_url,
                    company_name=company,
                    location=location,
                    posted_date=posted_date,
                ))
            except Exception as e:
                logger.debug(f"[linkedin] card parse error: {e}")
                continue
        return leads

    @staticmethod
    def _first(elements):
        return elements[0] if elements else None
