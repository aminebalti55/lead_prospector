"""
BBB (Better Business Bureau) scraper using ScraperEngine (Scrapling StealthyFetcher).

Rewritten from the legacy Selenium-based scraper to use the new
ScraperEngine infrastructure with Scrapling for HTML parsing.
"""

import re
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode

from src.core.scraper_engine import ScraperEngine
from src.core.models import BusinessLead

logger = logging.getLogger(__name__)


class BBBScraper:
    """
    Scraper for Better Business Bureau listings.

    Uses ScraperEngine with StealthyFetcher (Scrapling).
    Difficulty: MEDIUM
    Rate limiting: 2-4s between requests, 200/hour
    """

    SOURCE_NAME = "bbb"
    BASE_URL = "https://www.bbb.org/search"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self,
        business_type: str,
        city: str,
        state: str,
        max_results: int = 20,
    ) -> List[BusinessLead]:
        """Search BBB for businesses."""
        location = f"{city}, {state}"
        logger.info(f"Searching BBB: {business_type} in {location}")
        leads: List[BusinessLead] = []
        page_num = 1

        while len(leads) < max_results:
            params = {
                "find_country": "USA",
                "find_text": business_type,
                "find_loc": location,
                "page": page_num,
            }
            url = f"{self.BASE_URL}?{urlencode(params)}"
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
        """Parse BBB search results page.

        Uses Scrapling's CSS selector API to extract business listings.
        """
        leads: List[BusinessLead] = []
        seen_urls: set = set()

        # BBB profile links
        elements = page.css('a[href*="/profile/"]')

        for elem in elements:
            try:
                name = elem.get_all_text().strip() if elem.get_all_text() else ""
                href = elem.attrib.get("href", "")

                if not name or len(name) < 2:
                    continue
                if not href or "/profile/" not in href:
                    continue
                if "advertisement" in name.lower():
                    continue
                if href in seen_urls:
                    continue

                seen_urls.add(href)

                # Walk up to find the listing container
                container = self._get_listing_container(elem)
                container_text = container.get_all_text() if container else ""

                # Skip advertisements
                if "advertisement:" in container_text.lower():
                    continue

                # Extract phone
                phone = self._extract_phone(container_text)

                # Extract BBB rating
                bbb_rating = self._extract_bbb_rating(container_text)

                # Check accreditation
                accredited = "Accredited" in container_text

                # Extract complaints
                complaints = self._extract_complaints(container_text)

                # Extract year started
                year_started = self._extract_year_started(container_text)

                # Build full URL
                if href.startswith("/"):
                    href = f"https://www.bbb.org{href}"

                extra_data: dict = {"bbb_accredited": accredited}
                if bbb_rating:
                    extra_data["bbb_rating"] = bbb_rating
                if complaints is not None:
                    extra_data["complaints_last_3_years"] = complaints
                if year_started is not None:
                    extra_data["year_started"] = year_started
                    extra_data["years_in_business"] = datetime.now().year - year_started

                lead = BusinessLead(
                    source=self.SOURCE_NAME,
                    name=name,
                    phone=BusinessLead.clean_phone(phone),
                    city=city,
                    state=state,
                    detail_url=href,
                    is_sponsored=False,
                    extra_data=extra_data,
                )
                leads.append(lead)

            except Exception as e:
                logger.debug(f"Error extracting listing: {e}")
                continue

        return leads

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Visit BBB detail page to enrich lead with website, address, etc."""
        if not lead.detail_url:
            return lead

        try:
            response = self.engine.fetch_with_retry(
                lead.detail_url, self.SOURCE_NAME
            )
            if response is None:
                return lead

            # Extract phone
            if not lead.phone:
                phone_els = response.css('a[href^="tel:"]')
                if phone_els:
                    lead.phone = BusinessLead.clean_phone(
                        phone_els[0].get_all_text()
                    )

            # Extract website
            website_els = response.css('a[data-testid="website-link"]')
            if website_els:
                href = website_els[0].attrib.get("href", "")
                if href and "bbb.org" not in href:
                    lead.website = href

            # Extract address
            addr_els = response.css('[data-testid="business-address"]')
            if addr_els:
                lead.address = addr_els[0].get_all_text().strip()

            # Extract BBB rating from detail page text
            page_text = response.get_all_text() if response.get_all_text() else ""
            rating_match = re.search(r"BBB Rating:\s*([A-F][+-]?)", page_text)
            if rating_match:
                lead.extra_data["bbb_rating"] = rating_match.group(1)

            # Check accreditation via image alt text
            accred_imgs = response.css('img[alt*="Accredited Business"]')
            lead.extra_data["bbb_accredited"] = bool(accred_imgs)

            # Complaints
            complaint_match = re.search(
                r"(\d+)\s*complaints?\s*closed\s*in\s*last\s*3\s*years?",
                page_text,
                re.IGNORECASE,
            )
            if complaint_match:
                lead.extra_data["complaints_last_3_years"] = int(
                    complaint_match.group(1)
                )

            # Year started
            years_match = re.search(r"Business Started:\s*(\d{4})", page_text)
            if years_match:
                start_year = int(years_match.group(1))
                lead.extra_data["year_started"] = start_year
                lead.extra_data["years_in_business"] = (
                    datetime.now().year - start_year
                )

        except Exception as e:
            logger.warning(f"Error getting BBB details for {lead.name}: {e}")

        return lead

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
                text = (
                    container.get_all_text()
                    if hasattr(container, "get_all_text")
                    else ""
                )
                if len(text) > 100:
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
    def _extract_bbb_rating(text: str) -> Optional[str]:
        """Extract BBB rating from text."""
        match = re.search(r"BBB Rating:\s*([A-F][+-]?)", text)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_complaints(text: str) -> Optional[int]:
        """Extract complaints count from text."""
        match = re.search(
            r"(\d+)\s*complaints?\s*closed\s*in\s*last\s*3\s*years?",
            text,
            re.IGNORECASE,
        )
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_year_started(text: str) -> Optional[int]:
        """Extract year started from text."""
        match = re.search(r"Business Started:\s*(\d{4})", text)
        if match:
            return int(match.group(1))
        return None
