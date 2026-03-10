import logging
from datetime import datetime

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


class LinkedInJobsScraper:
    SOURCE_NAME = "linkedin"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        leads = []
        for kw in keywords[:3]:
            # Try LinkedIn public job search (no login)
            query = f"{kw} freelance contract"
            url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&sortBy=DD"
            try:
                response = self.engine.fetch_with_retry(url, self.SOURCE_NAME)
                if response:
                    text = response.get_all_text().lower() if response else ""
                    # Check for blocking
                    if "sign in" in text and "join now" in text and len(text) < 2000:
                        logger.warning("LinkedIn blocked - trying Google fallback")
                        leads.extend(
                            self._google_fallback(kw, max_results - len(leads))
                        )
                        continue
                    new_leads = self._parse_results(response)
                    leads.extend(new_leads)
            except Exception as e:
                logger.warning(f"LinkedIn search failed for '{kw}': {e}")
                leads.extend(self._google_fallback(kw, max_results - len(leads)))
            if len(leads) >= max_results:
                break
        return leads[:max_results]

    def _parse_results(self, page) -> list[DirectLead]:
        # LinkedIn public job cards: ul.jobs-search__results-list > li
        leads = []
        cards = (
            page.css("div.base-card")
            or page.css("li.result-card")
            or page.css("div.job-search-card")
        )
        for card in cards:
            try:
                title_el = card.css_first("h3.base-search-card__title") or card.css_first(
                    "h3"
                )
                if not title_el:
                    continue
                link_el = card.css_first("a.base-card__full-link") or card.css_first("a")
                company_el = card.css_first(
                    "h4.base-search-card__subtitle"
                ) or card.css_first("a.hidden-nested-link")
                loc_el = card.css_first("span.job-search-card__location")
                date_el = card.css_first("time")

                lead = DirectLead(
                    source="linkedin",
                    title=title_el.get_all_text().strip(),
                    description=title_el.get_all_text().strip(),
                    url=link_el.attrib.get("href", "") if link_el else "",
                    company_name=company_el.get_all_text().strip() if company_el else None,
                    location=loc_el.get_all_text().strip() if loc_el else None,
                    posted_date=self._parse_time(date_el) if date_el else None,
                )
                leads.append(lead)
            except Exception:
                continue
        return leads

    def _google_fallback(self, keyword: str, max_results: int) -> list[DirectLead]:
        """Fallback: search Google for LinkedIn job listings."""
        query = f'site:linkedin.com/jobs "{keyword}" "freelance" OR "contract"'
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        try:
            response = self.engine.fetch_with_retry(
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
                                url=href,
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
