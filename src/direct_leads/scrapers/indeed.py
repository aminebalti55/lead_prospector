import re
import logging
from datetime import datetime, timedelta

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


def _first(elements):
    """Get first element from css() result list, or None."""
    return elements[0] if elements else None


class IndeedScraper:
    SOURCE_NAME = "indeed"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    # Indeed country domain mapping
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

    async def search(self, keywords: list[str], max_results: int = 20, country: str = "") -> list[DirectLead]:
        leads = []
        domain = self.COUNTRY_DOMAINS.get(country.upper(), "www.indeed.com") if country else "www.indeed.com"
        for kw in keywords[:5]:
            query = f"{kw} freelance OR contract"
            url = f"https://{domain}/jobs?q={query.replace(' ', '+')}&sort=date&limit=25"
            try:
                response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                if response:
                    new_leads = self._parse_results(response)
                    leads.extend(new_leads)
            except Exception as e:
                logger.warning(f"Indeed search failed for '{kw}': {e}")
            if len(leads) >= max_results:
                break
        return leads[:max_results]

    def _parse_results(self, page) -> list[DirectLead]:
        leads = []
        job_cards = (
            page.css("div.job_seen_beacon")
            or page.css("div.resultContent")
            or page.css("td.resultContent")
        )

        for card in (job_cards or []):
            try:
                title_el = (
                    _first(card.css("h2.jobTitle a"))
                    or _first(card.css("a.jcs-JobTitle"))
                    or _first(card.css("h2 a"))
                )
                if not title_el:
                    continue
                title = title_el.get_all_text().strip()
                href = title_el.attrib.get("href", "")
                job_url = f"https://www.indeed.com{href}" if href.startswith("/") else href

                company_el = (
                    _first(card.css("span.css-1h7lukg"))
                    or _first(card.css("span.companyName"))
                    or _first(card.css("[data-testid='company-name']"))
                )
                company = company_el.get_all_text().strip() if company_el else None

                loc_el = (
                    _first(card.css("div.css-1restlb"))
                    or _first(card.css("div.companyLocation"))
                    or _first(card.css("[data-testid='text-location']"))
                )
                location = loc_el.get_all_text().strip() if loc_el else None

                desc_el = (
                    _first(card.css("div.css-9446fg"))
                    or _first(card.css("div.job-snippet"))
                    or _first(card.css("table.jobCardShelfContainer"))
                )
                description = desc_el.get_all_text().strip() if desc_el else title

                date_el = _first(card.css("span.date")) or _first(card.css("span.css-qvloho"))
                posted_date = self._parse_date(
                    date_el.get_all_text().strip() if date_el else ""
                )

                lead = DirectLead(
                    source="indeed",
                    title=title,
                    description=description[:2000],
                    url=job_url,
                    posted_date=posted_date,
                    company_name=company,
                    location=location,
                )
                leads.append(lead)
            except Exception as e:
                logger.debug(f"Failed to parse Indeed card: {e}")
                continue
        return leads

    def _parse_date(self, text: str) -> datetime | None:
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
