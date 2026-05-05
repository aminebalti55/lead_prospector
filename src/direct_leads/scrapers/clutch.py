import logging
from urllib.parse import quote_plus

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)

BASE_URL = "https://clutch.co"


class ClutchScraper:
    SOURCE_NAME = "clutch"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        """Search clutch.co for software development companies matching keywords.

        Selectors verified live May 2026:
        - Card: div.provider-row (~80/page)
        - Title: .provider__title
        - Description: .provider__description
        - Profile link: a.directory_profile (href relative to BASE_URL)
        """
        leads: list[DirectLead] = []
        for kw in keywords[:5]:
            try:
                url = f"{BASE_URL}/developers?query={quote_plus(kw)}"
                response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                if not response:
                    continue

                cards = response.css("div.provider-row")
                if not cards:
                    logger.debug(f"Clutch returned no provider-row cards for '{kw}'")
                    continue

                for card in cards:
                    try:
                        title_el = card.css(".provider__title")
                        company_name = title_el[0].get_all_text().strip() if title_el else ""
                        if not company_name:
                            # Fall back to data-title attribute on the card itself
                            company_name = card.attrib.get("data-title", "").strip()
                        if not company_name:
                            continue

                        desc_el = card.css(".provider__description")
                        description = desc_el[0].get_all_text().strip() if desc_el else ""

                        profile_link = card.css("a.directory_profile")
                        href = profile_link[0].attrib.get("href", "") if profile_link else ""
                        detail_url = href if href.startswith("http") else f"{BASE_URL}{href}"

                        lead = DirectLead(
                            source="clutch",
                            title=f"{company_name} - {kw}",
                            description=description[:2000],
                            url=detail_url,
                            company_name=company_name,
                        )
                        leads.append(lead)
                    except Exception as e:
                        logger.debug(f"Clutch card parse error: {e}")
                        continue

                if len(leads) >= max_results:
                    break
            except Exception as e:
                logger.warning(f"Clutch search failed for '{kw}': {e}")
        return leads[:max_results]
