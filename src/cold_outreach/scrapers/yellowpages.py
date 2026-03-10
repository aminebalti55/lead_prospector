"""
YellowPages scraper using ScraperEngine (Scrapling HTTP fetcher).

Rewritten from the legacy Selenium-based scraper to use the new
ScraperEngine infrastructure with Scrapling for HTML parsing.
"""

import re
import logging
from typing import List, Optional

from src.core.scraper_engine import ScraperEngine
from src.core.models import BusinessLead

logger = logging.getLogger(__name__)


class YellowPagesScraper:
    """
    Scraper for YellowPages business listings.

    Uses ScraperEngine with HTTP fetcher (Scrapling).
    Difficulty: MEDIUM
    Rate limiting: 1-3s between requests, 300/hour
    """

    SOURCE_NAME = "yellowpages"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self,
        business_type: str,
        city: str,
        state: str,
        max_results: int = 20,
    ) -> List[BusinessLead]:
        """Search YellowPages for businesses."""
        logger.info(
            f"Searching YellowPages: {business_type} in {city}, {state}"
        )
        leads: List[BusinessLead] = []
        page_num = 1

        while len(leads) < max_results:
            url = (
                f"https://www.yellowpages.com/"
                f"{city.lower().replace(' ', '-')}-{state.lower()}/"
                f"{business_type.lower().replace(' ', '-')}"
                f"?page={page_num}"
            )
            response = self.engine.fetch_with_retry(url, self.SOURCE_NAME)
            if response is None:
                break

            new_leads = self._parse_search_results(response, city, state)
            if not new_leads:
                break

            leads.extend(new_leads)
            page_num += 1

        return leads[:max_results]

    def _parse_search_results(
        self, page, city: str, state: str
    ) -> List[BusinessLead]:
        """Parse YellowPages search results page.

        Uses Scrapling's CSS selector API to extract business listings.
        """
        leads: List[BusinessLead] = []
        seen_urls: set = set()

        # Try multiple selectors for business name links, same as old scraper
        selectors = [
            "a.business-name",
            'a[href*="/mip/"]',
            '.info-primary a[href*="/mip/"]',
        ]

        for selector in selectors:
            elements = page.css(selector)

            for elem in elements:
                try:
                    name = elem.get_all_text().strip() if elem.get_all_text() else ""
                    href = elem.attrib.get("href", "")

                    if not name or len(name) < 2:
                        continue
                    if not href:
                        continue
                    if href in seen_urls:
                        continue

                    seen_urls.add(href)

                    # Walk up to find the listing container
                    container = self._get_listing_container(elem)
                    container_text = container.get_all_text() if container else ""

                    # Skip ads
                    if container_text.strip().startswith("Ad"):
                        continue

                    # Extract phone
                    phone = self._extract_phone(container_text)

                    # Extract address
                    address = self._extract_address(container_text)

                    # Extract website from container
                    website = self._extract_website(container)

                    # Build full URL
                    if href.startswith("/"):
                        href = f"https://www.yellowpages.com{href}"

                    lead = BusinessLead(
                        source=self.SOURCE_NAME,
                        name=name,
                        phone=BusinessLead.clean_phone(phone),
                        address=address,
                        website=website,
                        city=city,
                        state=state,
                        detail_url=href,
                        is_sponsored=False,
                    )
                    leads.append(lead)

                except Exception as e:
                    logger.debug(f"Error extracting listing: {e}")
                    continue

        return leads

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_listing_container(element):
        """Walk up the DOM to find a meaningful parent container."""
        try:
            container = element.parent
            for _ in range(10):
                if container is None:
                    break
                text = container.get_all_text() if hasattr(container, "get_all_text") else ""
                if len(text) > 100:
                    return container
                container = container.parent
            # Fall back to immediate parent
            return element.parent
        except Exception:
            return None

    @staticmethod
    def _extract_phone(text: str) -> Optional[str]:
        """Extract phone number from text."""
        match = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", text)
        if match:
            return match.group()
        return None

    @staticmethod
    def _extract_address(text: str) -> Optional[str]:
        """Extract address from text."""
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if re.match(r"^\d+\s+\w+", line) and len(line) < 100:
                return line
        return None

    @staticmethod
    def _extract_website(container) -> Optional[str]:
        """Extract website URL from container element."""
        if not container:
            return None
        try:
            website_els = container.css("a.track-visit-website")
            if website_els:
                return website_els[0].attrib.get("href")
        except Exception:
            pass
        return None
