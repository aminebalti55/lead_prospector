"""
Manta scraper using ScraperEngine (Scrapling HTTP fetcher).

Rewritten from the legacy Selenium-based scraper to use the new
ScraperEngine infrastructure with Scrapling for HTML parsing.
"""

import re
import logging
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, unquote

from src.core.scraper_engine import ScraperEngine
from src.core.models import BusinessLead

logger = logging.getLogger(__name__)


class MantaScraper:
    """
    Scraper for Manta business directory listings.

    Uses ScraperEngine with HTTP fetcher (Scrapling).
    Difficulty: MEDIUM
    Rate limiting: 2-5s between requests, 150/hour
    """

    SOURCE_NAME = "manta"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self,
        business_type: str,
        city: str,
        state: str,
        max_results: int = 20,
    ) -> List[BusinessLead]:
        """Search Manta for businesses."""
        logger.info(f"Searching Manta: {business_type} in {city}, {state}")
        leads: List[BusinessLead] = []
        page_num = 1

        while len(leads) < max_results:
            search_term = business_type.lower().replace(" ", "-")
            city_slug = city.lower().replace(" ", "-")
            state_slug = state.lower()
            url = (
                f"https://www.manta.com/search"
                f"?search={search_term}"
                f"&city={city_slug}"
                f"&state={state_slug}"
                f"&pg={page_num}"
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
        """Parse Manta search results page.

        Uses Scrapling's CSS selector API to extract business listings.
        """
        leads: List[BusinessLead] = []
        seen_urls: set = set()

        # Company links that point to /c/ pages (excluding category links)
        elements = page.css('a[href^="/c/"]')

        for elem in elements:
            try:
                href = elem.attrib.get("href", "")

                # Exclude category links
                if "category" in href:
                    continue

                name = elem.get_all_text().strip() if elem.get_all_text() else ""

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

                # Skip promoted listings
                if "\u2605" in container_text or "Promoted" in container_text:
                    continue

                # Extract phone
                phone = self._extract_phone(container_text)

                # Extract address
                address = self._extract_address(container_text)

                # Check claimed status
                is_claimed = "CLAIMED" in container_text

                # Extract employee count
                emp_match = re.search(
                    r"(\d+)\s*employees?", container_text, re.IGNORECASE
                )
                employee_count = (
                    int(emp_match.group(1)) if emp_match else None
                )

                # Extract years in business
                years_match = re.search(
                    r"(\d+)\s*years?\s*in\s*business",
                    container_text,
                    re.IGNORECASE,
                )
                years_in_business = (
                    int(years_match.group(1)) if years_match else None
                )

                # Build full URL
                if href.startswith("/"):
                    href = f"https://www.manta.com{href}"

                extra_data = {}
                if employee_count:
                    extra_data["employee_count"] = employee_count
                if years_in_business:
                    extra_data["years_in_business"] = years_in_business

                lead = BusinessLead(
                    source=self.SOURCE_NAME,
                    name=name,
                    phone=BusinessLead.clean_phone(phone),
                    address=address,
                    city=city,
                    state=state,
                    is_claimed=is_claimed,
                    is_sponsored=False,
                    detail_url=href,
                    extra_data=extra_data,
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
                if len(text) > 50:
                    return container
                container = container.parent
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
    def _unwrap_redirect_url(url: str) -> str:
        """Unwrap Manta's urlverify redirect URLs."""
        if "/urlverify" in url and "redirect=" in url:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if "redirect" in query_params:
                return unquote(query_params["redirect"][0])
        return url
