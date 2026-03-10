import re
import logging
from datetime import datetime, timedelta

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


class IndeedScraper:
    SOURCE_NAME = "indeed"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        leads = []
        for kw in keywords[:5]:
            query = f"{kw} freelance OR contract"
            url = f"https://www.indeed.com/jobs?q={query.replace(' ', '+')}&sort=date&limit=25"
            try:
                response = self.engine.fetch_with_retry(url, self.SOURCE_NAME)
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
        # Indeed uses div.job_seen_beacon or div.resultContent for job cards
        job_cards = (
            page.css("div.job_seen_beacon")
            or page.css("div.resultContent")
            or page.css("td.resultContent")
        )

        for card in job_cards:
            try:
                # Title from h2 > a or a.jcs-JobTitle
                title_el = (
                    card.css_first("h2.jobTitle a")
                    or card.css_first("a.jcs-JobTitle")
                    or card.css_first("h2 a")
                )
                if not title_el:
                    continue
                title = title_el.get_all_text().strip()
                href = title_el.attrib.get("href", "")
                job_url = f"https://www.indeed.com{href}" if href.startswith("/") else href

                # Company
                company_el = (
                    card.css_first("span.css-1h7lukg")
                    or card.css_first("span.companyName")
                    or card.css_first("[data-testid='company-name']")
                )
                company = company_el.get_all_text().strip() if company_el else None

                # Location
                loc_el = (
                    card.css_first("div.css-1restlb")
                    or card.css_first("div.companyLocation")
                    or card.css_first("[data-testid='text-location']")
                )
                location = loc_el.get_all_text().strip() if loc_el else None

                # Description snippet
                desc_el = (
                    card.css_first("div.css-9446fg")
                    or card.css_first("div.job-snippet")
                    or card.css_first("table.jobCardShelfContainer")
                )
                description = desc_el.get_all_text().strip() if desc_el else title

                # Date - extract from span.date or similar
                date_el = card.css_first("span.date") or card.css_first("span.css-qvloho")
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
        """Parse Indeed's relative date (e.g., '3 days ago', 'Today', 'Just posted')."""
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
