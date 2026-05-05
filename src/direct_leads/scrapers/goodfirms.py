"""GoodFirms scraper — Tunisian/MENA-friendly B2B-services directory.

Verified live May 2026. Uses category-based URLs (the old /projects?q= path
is 404). Parses li.firm-wrapper cards for firm name + description + profile URL.

Cloudflare-protected → routed through ScraperEngine's stealth tier.
"""
from __future__ import annotations

import logging

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)

BASE_URL = "https://www.goodfirms.co"

# Map common dev keywords → live GoodFirms category URLs.
# Unknown keywords fall back to the broad web-development-agency directory.
_KEYWORD_TO_PATH: dict[str, str] = {
    # Languages
    "python": "/directory/languages/top-software-development-companies/python",
    "java": "/directory/languages/top-software-development-companies/java",
    "php": "/directory/languages/top-software-development-companies/php",
    "javascript": "/directory/languages/top-software-development-companies/javascript",
    "typescript": "/companies/web-development-agency",
    "react": "/directory/languages/top-software-development-companies/reactjs",
    "reactjs": "/directory/languages/top-software-development-companies/reactjs",
    "angular": "/directory/languages/top-software-development-companies/angularjs",
    "angularjs": "/directory/languages/top-software-development-companies/angularjs",
    "node": "/directory/languages/top-software-development-companies/node-js",
    "nodejs": "/directory/languages/top-software-development-companies/node-js",
    "node-js": "/directory/languages/top-software-development-companies/node-js",
    "vue": "/directory/languages/top-software-development-companies/vuejs",
    # Frameworks / platforms
    "net": "/directory/frameworks/top-software-development-companies/net",
    "dotnet": "/directory/frameworks/top-software-development-companies/net",
    "wordpress": "/companies/web-development-agency/wordpress",
    "drupal": "/companies/web-development-agency/drupal",
    "laravel": "/directory/frameworks/top-software-development-companies/laravel",
    # E-commerce
    "shopify": "/ecommerce-development-companies/shopify",
    "magento": "/ecommerce-development-companies/magento",
    "woocommerce": "/ecommerce-development-companies/woocommerce",
    # Mobile
    "android": "/directory/platform/app-development/android",
    "ios": "/directory/platform/app-development/iphone",
    "iphone": "/directory/platform/app-development/iphone",
    "flutter": "/directory/frameworks/app-development/flutter",
    # Other
    "blockchain": "/companies/blockchain-development-services",
    "ai": "/companies/web-development-agency",
    "ml": "/companies/web-development-agency",
}

_DEFAULT_PATH = "/companies/web-development-agency"


def _path_for_keyword(kw: str) -> str:
    """Map a keyword to a GoodFirms category URL path. Defaults to the broad
    web-development-agency directory."""
    key = kw.lower().strip()
    return _KEYWORD_TO_PATH.get(key, _DEFAULT_PATH)


class GoodFirmsScraper:
    SOURCE_NAME = "goodfirms"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        """Search GoodFirms category pages for B2B service providers.

        Each keyword maps to a directory URL. Default → web-development-agency.
        Selectors verified live May 2026: li.firm-wrapper, .firm-name a,
        .firm-short-description.
        """
        leads: list[DirectLead] = []
        seen_urls: set[str] = set()

        for kw in keywords[:5]:
            path = _path_for_keyword(kw)
            url = f"{BASE_URL}{path}"
            try:
                response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                if not response:
                    continue

                cards = response.css("li.firm-wrapper")
                if not cards:
                    logger.debug(f"GoodFirms returned no firm-wrapper cards for '{kw}' at {url}")
                    continue

                for card in cards:
                    try:
                        name_link = card.css(".firm-name a")
                        if not name_link:
                            continue
                        company_name = name_link[0].get_all_text().strip()
                        if not company_name:
                            continue
                        href = name_link[0].attrib.get("href", "")
                        detail_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                        if detail_url in seen_urls:
                            continue
                        seen_urls.add(detail_url)

                        desc_el = card.css(".firm-short-description")
                        description = desc_el[0].get_all_text().strip() if desc_el else ""

                        lead = DirectLead(
                            source="goodfirms",
                            lead_subtype="agency",
                            title=f"{company_name} - {kw}",
                            description=description[:2000],
                            url=detail_url,
                            company_name=company_name,
                            location="",  # GoodFirms category pages don't show location per card
                        )
                        leads.append(lead)
                        if len(leads) >= max_results:
                            return leads[:max_results]
                    except Exception as e:
                        logger.debug(f"GoodFirms card parse error: {e}")
                        continue
            except Exception as e:
                logger.warning(f"GoodFirms search failed for '{kw}' at {url}: {e}")
                continue

        return leads[:max_results]
