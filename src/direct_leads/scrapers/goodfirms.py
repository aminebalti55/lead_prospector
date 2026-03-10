import logging
from urllib.parse import quote_plus

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)

BASE_URL = "https://www.goodfirms.co"


class GoodFirmsScraper:
    SOURCE_NAME = "goodfirms"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        """Search goodfirms.co for project listings matching keywords."""
        leads: list[DirectLead] = []
        for kw in keywords[:5]:
            try:
                url = f"{BASE_URL}/projects?q={quote_plus(kw)}"
                response = self.engine.fetch(url, self.SOURCE_NAME)
                if not response:
                    continue

                # Parse project/company cards from the listing page
                cards = response.css("div.firm-card") or response.css("div.company-card")
                if not cards:
                    cards = response.css("div.listing-row") or []

                for card in cards:
                    try:
                        # Company name
                        name_el = card.css("a.firm-name") or card.css("h3 a") or card.css("a.company-name")
                        company_name = ""
                        detail_url = ""
                        if name_el:
                            company_name = name_el[0].text.strip() if name_el[0].text else ""
                            href = name_el[0].attrib.get("href", "")
                            detail_url = href if href.startswith("http") else f"{BASE_URL}{href}"

                        # Description / tagline
                        desc_el = card.css("p.firm-desc") or card.css("div.company-description")
                        description = ""
                        if desc_el:
                            description = desc_el[0].text.strip() if desc_el[0].text else ""

                        # Location
                        loc_el = card.css("span.firm-location") or card.css("span.location")
                        location = ""
                        if loc_el:
                            location = loc_el[0].text.strip() if loc_el[0].text else ""

                        if not company_name:
                            continue

                        lead = DirectLead(
                            source="goodfirms",
                            title=f"{company_name} - {kw}",
                            description=description[:2000],
                            url=detail_url,
                            company_name=company_name,
                            location=location,
                        )
                        leads.append(lead)
                    except Exception as e:
                        logger.debug(f"GoodFirms card parse error: {e}")
                        continue

                if len(leads) >= max_results:
                    break
            except Exception as e:
                logger.warning(f"GoodFirms search failed for '{kw}': {e}")
        return leads[:max_results]
