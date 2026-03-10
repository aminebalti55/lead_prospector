"""
Yelp scraper using ScraperEngine (Scrapling StealthyFetcher).

Rewritten from the legacy Selenium-based scraper to use the new
ScraperEngine infrastructure with Scrapling for HTML parsing.
"""

import re
import logging
from typing import List, Optional
from urllib.parse import urlencode, urlparse, parse_qs

from src.core.scraper_engine import ScraperEngine
from src.core.models import BusinessLead

logger = logging.getLogger(__name__)


class YelpScraper:
    """
    Scraper for Yelp business listings.

    Uses ScraperEngine with StealthyFetcher (Scrapling).
    Difficulty: MEDIUM-HIGH
    Rate limiting: 2-4s between requests, 200/hour
    Pagination: start param increments by 10
    """

    SOURCE_NAME = "yelp"
    BASE_URL = "https://www.yelp.com/search"

    BLOCKING_INDICATORS = [
        "Device verification",
        "Please verify you're a human",
        "unusual traffic",
        "Access denied",
    ]

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self,
        business_type: str,
        city: str,
        state: str,
        max_results: int = 20,
    ) -> List[BusinessLead]:
        """Search Yelp for businesses."""
        location = f"{city}, {state}"
        logger.info(f"Searching Yelp: {business_type} in {location}")
        leads: List[BusinessLead] = []
        start = 0

        while len(leads) < max_results:
            params = {
                "find_desc": business_type,
                "find_loc": location,
                "start": start,
            }
            url = f"{self.BASE_URL}?{urlencode(params)}"
            response = self.engine.fetch_with_retry(url, self.SOURCE_NAME)
            if response is None:
                break

            # Check for blocking / CAPTCHA
            page_text = response.get_all_text() if response.get_all_text() else ""
            if self._is_blocked(page_text):
                logger.warning("Yelp appears to be blocking (CAPTCHA / device verification)")
                return []

            new_leads = self._parse_search_results(response, city, state)
            if not new_leads:
                break

            leads.extend(new_leads)
            start += 10

        return leads[:max_results]

    def _is_blocked(self, page_text: str) -> bool:
        """Check if Yelp is blocking us with CAPTCHA or device verification."""
        text_lower = page_text.lower()
        return any(ind.lower() in text_lower for ind in self.BLOCKING_INDICATORS)

    def _parse_search_results(
        self, page, city: str, state: str
    ) -> List[BusinessLead]:
        """Parse Yelp search results page.

        Uses Scrapling's CSS selector API to extract business listings.
        """
        leads: List[BusinessLead] = []
        seen_urls: set = set()

        # Find all business links pointing to /biz/ pages
        selectors = [
            'a[href*="/biz/"]',
            '[data-testid="serp-ia-card"] a',
        ]

        for selector in selectors:
            elements = page.css(selector)

            for elem in elements:
                try:
                    href = elem.attrib.get("href", "")
                    name = elem.get_all_text().strip() if elem.get_all_text() else ""

                    if not name or len(name) < 2:
                        continue
                    if not href or "/biz/" not in href:
                        continue
                    if "/adredir" in href or "/aclk" in href:
                        continue
                    if href in seen_urls:
                        continue

                    seen_urls.add(href)

                    # Walk up to find the listing container
                    container = self._get_listing_container(elem)
                    container_text = container.get_all_text() if container else ""

                    # Skip sponsored
                    if "Sponsored" in container_text or container_text.strip().startswith("Ad"):
                        continue

                    # Extract rating
                    rating = self._extract_rating(container_text)

                    # Extract review count
                    review_count = self._extract_review_count(container_text)

                    # Extract phone
                    phone = self._extract_phone(container_text)

                    # Build full URL
                    if href.startswith("/"):
                        href = f"https://www.yelp.com{href}"

                    lead = BusinessLead(
                        source=self.SOURCE_NAME,
                        name=name,
                        phone=BusinessLead.clean_phone(phone),
                        city=city,
                        state=state,
                        rating=rating,
                        review_count=review_count,
                        detail_url=href,
                        is_sponsored=False,
                    )
                    leads.append(lead)

                except Exception as e:
                    logger.debug(f"Error extracting listing: {e}")
                    continue

        return leads

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Visit Yelp detail page to enrich lead with website, address, etc."""
        if not lead.detail_url:
            return lead

        try:
            response = self.engine.fetch_with_retry(
                lead.detail_url, self.SOURCE_NAME
            )
            if response is None:
                return lead

            # Check for blocking on detail page
            page_text = response.get_all_text() if response.get_all_text() else ""
            if self._is_blocked(page_text):
                logger.warning("Yelp blocking on detail page")
                return lead

            # Extract phone
            phone_els = response.css('a[href^="tel:"]')
            if phone_els:
                lead.phone = BusinessLead.clean_phone(
                    phone_els[0].get_all_text()
                )

            # Extract website (Yelp uses biz_redir redirects)
            website_els = response.css('a[href*="biz_redir"]')
            if website_els:
                href = website_els[0].attrib.get("href", "")
                if href:
                    lead.website = self._unwrap_redirect_url(href)

            # Extract address
            addr_els = response.css("address")
            if addr_els:
                lead.address = addr_els[0].get_all_text().strip()

            # Check claimed status
            if "Claimed" in page_text:
                lead.is_claimed = True

            # Years in business
            years_match = re.search(
                r"(\d+)\s*years?\s*in\s*business", page_text, re.IGNORECASE
            )
            if years_match:
                lead.extra_data["years_in_business"] = int(years_match.group(1))

        except Exception as e:
            logger.warning(f"Error getting Yelp details for {lead.name}: {e}")

        return lead

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_listing_container(element):
        """Walk up the DOM to find a meaningful parent container."""
        try:
            container = element.parent
            for _ in range(15):
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
    def _extract_rating(text: str) -> Optional[float]:
        """Extract rating from text."""
        match = re.search(r"(\d+\.?\d*)\s*star", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def _extract_review_count(text: str) -> Optional[int]:
        """Extract review count from text."""
        match = re.search(r"\((\d+)\s*reviews?\)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_phone(text: str) -> Optional[str]:
        """Extract phone number from text."""
        match = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", text)
        if match:
            return match.group()
        return None

    @staticmethod
    def _unwrap_redirect_url(url: str) -> str:
        """Unwrap Yelp's biz_redir redirect URLs."""
        if "biz_redir" in url:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if "url" in query_params:
                return query_params["url"][0]
        return url
