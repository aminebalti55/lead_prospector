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
        """Search clutch.co for project listings matching keywords."""
        leads: list[DirectLead] = []
        for kw in keywords[:5]:
            try:
                url = f"{BASE_URL}/developers?query={quote_plus(kw)}"
                response = self.engine.fetch(url, self.SOURCE_NAME)
                if not response:
                    continue

                # Parse company/project cards from the listing page
                cards = response.css("li.provider-row") or response.css("div.provider-row")
                if not cards:
                    cards = response.css("ul.providers-list li") or []

                for card in cards:
                    try:
                        # Company name
                        name_el = card.css("h3.company_info a") or card.css("a.company_name")
                        company_name = ""
                        detail_url = ""
                        if name_el:
                            company_name = name_el[0].text.strip() if name_el[0].text else ""
                            href = name_el[0].attrib.get("href", "")
                            detail_url = href if href.startswith("http") else f"{BASE_URL}{href}"

                        # Tagline / description
                        tagline_el = card.css("p.company_info__wrap") or card.css("div.provider-info__description")
                        description = ""
                        if tagline_el:
                            description = tagline_el[0].text.strip() if tagline_el[0].text else ""

                        # Location
                        loc_el = card.css("span.locality") or card.css("span.provider-info__location")
                        location = ""
                        if loc_el:
                            location = loc_el[0].text.strip() if loc_el[0].text else ""

                        if not company_name:
                            continue

                        lead = DirectLead(
                            source="clutch",
                            title=f"{company_name} - {kw}",
                            description=description[:2000],
                            url=detail_url,
                            company_name=company_name,
                            location=location,
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
