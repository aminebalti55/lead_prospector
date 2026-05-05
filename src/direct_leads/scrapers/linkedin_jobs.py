import logging
from datetime import datetime
from urllib.parse import quote, urlparse

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


def _strip_linkedin_session_params(url: str | None) -> str:
    """Strip query string + fragment from a LinkedIn URL so the same job
    yields a stable lead_id across sessions (sha1 dedup key is source|url).

    Mirrors src/direct_leads/scrapers/tanit.py:_strip_session_params.
    """
    if not url:
        return ""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


# LinkedIn geoId mapping for country-based filtering
LINKEDIN_GEO_IDS = {
    "TN": "102134353",   # Tunisia
    "US": "103644278",   # United States
    "GB": "101165590",   # United Kingdom
    "FR": "105015875",   # France
    "DE": "101282230",   # Germany
    "CA": "101174742",   # Canada
    "AU": "101452733",   # Australia
    "AE": "104305776",   # UAE
    "SA": "100459316",   # Saudi Arabia
    "MA": "102787409",   # Morocco
    "DZ": "104029862",   # Algeria
}


class LinkedInJobsScraper:
    SOURCE_NAME = "linkedin"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20, country: str = "") -> list[DirectLead]:
        leads = []
        for kw in keywords[:3]:
            # Use the keyword as-is — don't append "freelance contract" as it
            # makes the query too narrow for small markets like Tunisia.
            url = f"https://www.linkedin.com/jobs/search/?keywords={quote(kw)}&sortBy=DD"
            # Add country/location filter if specified
            geo_id = LINKEDIN_GEO_IDS.get(country.upper()) if country else None
            if geo_id:
                url += f"&location={quote(country)}&geoId={geo_id}"
                logger.info(f"LinkedIn filtering by country: {country} (geoId={geo_id})")
            try:
                response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                if response:
                    text = response.get_all_text().lower() if response else ""
                    # Check for blocking or no results
                    no_results = "couldn't find a match" in text or "couldn\u2019t find a match" in text
                    if no_results:
                        logger.info(f"LinkedIn: no results for '{kw}' — skipping")
                        continue
                    if "sign in" in text and "join now" in text and len(text) < 5000:
                        logger.warning("LinkedIn blocked - trying Google fallback")
                        leads.extend(
                            await self._google_fallback(kw, max_results - len(leads))
                        )
                        continue
                    new_leads = self._parse_results(response)
                    leads.extend(new_leads)
            except Exception as e:
                logger.warning(f"LinkedIn search failed for '{kw}': {e}")
                leads.extend(await self._google_fallback(kw, max_results - len(leads)))
            if len(leads) >= max_results:
                break
        return leads[:max_results]

    @staticmethod
    def _first(elements):
        """Get first element from css() result list, or None."""
        return elements[0] if elements else None

    def _parse_results(self, page) -> list[DirectLead]:
        leads = []
        cards = (
            page.css("div.base-card")
            or page.css("li.result-card")
            or page.css("div.job-search-card")
        )
        for card in (cards or []):
            try:
                title_el = self._first(card.css("h3.base-search-card__title")) or self._first(card.css("h3"))
                if not title_el:
                    continue
                link_el = self._first(card.css("a.base-card__full-link")) or self._first(card.css("a"))
                company_el = self._first(card.css("h4.base-search-card__subtitle")) or self._first(card.css("a.hidden-nested-link"))
                loc_el = self._first(card.css("span.job-search-card__location"))
                date_el = self._first(card.css("time"))

                lead = DirectLead(
                    source="linkedin",
                    title=title_el.get_all_text().strip(),
                    description=title_el.get_all_text().strip(),
                    url=_strip_linkedin_session_params(link_el.attrib.get("href", "") if link_el else ""),
                    company_name=company_el.get_all_text().strip() if company_el else None,
                    location=loc_el.get_all_text().strip() if loc_el else None,
                    posted_date=self._parse_time(date_el) if date_el else None,
                )
                leads.append(lead)
            except Exception as e:
                logger.debug(f"Failed to parse LinkedIn card: {e}")
                continue
        return leads

    async def _google_fallback(self, keyword: str, max_results: int) -> list[DirectLead]:
        """Fallback: search Google for LinkedIn job listings."""
        query = f'site:linkedin.com/jobs "{keyword}" "freelance" OR "contract"'
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        try:
            response = await self.engine.async_fetch_with_retry(
                url, "google_maps"
            )  # use stealth for Google
            if not response:
                return []
            leads = []
            for link in response.css("a"):
                href = link.attrib.get("href", "")
                if "linkedin.com/jobs" in href:
                    title = link.get_all_text().strip()
                    if title:
                        leads.append(
                            DirectLead(
                                source="linkedin",
                                title=title,
                                description=title,
                                url=_strip_linkedin_session_params(href),
                                location="Unknown",
                            )
                        )
            return leads[:max_results]
        except Exception:
            return []

    def _parse_time(self, time_el) -> datetime | None:
        dt = time_el.attrib.get("datetime", "")
        if dt:
            try:
                return datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except Exception:
                pass
        return None
