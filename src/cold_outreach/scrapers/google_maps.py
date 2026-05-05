"""
Google Maps scraper using ScraperEngine (Scrapling DynamicFetcher + StealthyFetcher).

Rewritten from the legacy Selenium-based scraper to use the new
ScraperEngine infrastructure with Scrapling for HTML parsing.

DynamicFetcher is used for the initial search (JavaScript-rendered page),
and StealthyFetcher is used for individual business detail pages.
"""

import re
import logging
from typing import List, Optional
from urllib.parse import quote_plus

from src.core.scraper_engine import ScraperEngine
from src.core.models import BusinessLead

logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    """
    Scraper for Google Maps business listings.

    Uses ScraperEngine with DynamicFetcher for search pages (JS rendering)
    and StealthyFetcher for detail pages.
    Difficulty: HIGH (aggressive anti-bot measures)
    Rate limiting: 3-6s between requests, 150/hour
    """

    SOURCE_NAME = "google_maps"
    BASE_URL = "https://www.google.com/maps/search"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self,
        business_type: str,
        city: str,
        state: str,
        max_results: int = 20,
    ) -> List[BusinessLead]:
        """Search Google Maps for businesses.

        Fetches the search URL via DynamicFetcher, then parses
        the initially visible results (typically 5-7 listings).
        """
        query = f"{business_type} in {city} {state}"
        url = f"{self.BASE_URL}/{quote_plus(query)}?hl=en"
        logger.info(f"Searching Google Maps: {query}")

        response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
        if response is None:
            return []

        leads = self._parse_search_results(response, city, state)
        return leads[:max_results]

    def _parse_search_results(
        self, page, city: str, state: str
    ) -> List[BusinessLead]:
        """Parse Google Maps search results page.

        Uses Scrapling's CSS selector API to extract business listings.
        Google Maps renders listing containers as div.Nv2PK or links to
        /maps/place/. We parse whichever is available.
        """
        leads: List[BusinessLead] = []
        seen_urls: set = set()

        # Try listing containers first, then fall back to place links
        listing_containers = page.css("div.Nv2PK")

        if listing_containers:
            for container in listing_containers:
                try:
                    lead = self._extract_from_container(
                        container, city, state, seen_urls
                    )
                    if lead and not lead.is_sponsored:
                        leads.append(lead)
                except Exception as e:
                    logger.debug(f"Error extracting listing: {e}")
                    continue
        else:
            # Fall back to place links
            elements = page.css('a[href*="/maps/place/"]')
            for elem in elements:
                try:
                    lead = self._extract_from_link(
                        elem, city, state, seen_urls
                    )
                    if lead and not lead.is_sponsored:
                        leads.append(lead)
                except Exception as e:
                    logger.debug(f"Error extracting listing: {e}")
                    continue

        return leads

    def _extract_from_container(
        self, container, city: str, state: str, seen_urls: set
    ) -> Optional[BusinessLead]:
        """Extract a lead from a div.Nv2PK container element."""
        container_text = container.get_all_text() if container.get_all_text() else ""

        # Check for sponsored
        if self._is_sponsored(container_text):
            return BusinessLead(
                source=self.SOURCE_NAME,
                name="",
                city=city,
                state=state,
                is_sponsored=True,
            )

        # Get detail URL from the link inside the container
        detail_url = None
        link_els = container.css("a.hfpxzc")
        if link_els:
            detail_url = link_els[0].attrib.get("href", "")

        if not link_els:
            link_els = container.css('a[href*="/maps/place/"]')
            if link_els:
                detail_url = link_els[0].attrib.get("href", "")

        if detail_url and detail_url in seen_urls:
            return None
        if detail_url:
            seen_urls.add(detail_url)

        # Extract name
        name = self._extract_name(container, link_els)
        if not name:
            return None

        # Extract rating
        rating = None
        rating_els = container.css(".MW4etd")
        if rating_els:
            rating = BusinessLead.clean_rating(rating_els[0].get_all_text())

        # Extract review count
        review_count = None
        review_els = container.css(".UY7F9")
        if review_els:
            review_count = BusinessLead.clean_review_count(
                review_els[0].get_all_text()
            )

        # Extract phone
        phone = self._extract_phone(container_text)

        # Extract address
        address = self._extract_address(container_text)

        # Extract categories
        categories = self._extract_categories(container_text)

        return BusinessLead(
            source=self.SOURCE_NAME,
            name=name,
            phone=BusinessLead.clean_phone(phone),
            city=city,
            state=state,
            rating=rating,
            review_count=review_count,
            address=address,
            categories=categories,
            is_sponsored=False,
            detail_url=detail_url,
        )

    def _extract_from_link(
        self, elem, city: str, state: str, seen_urls: set
    ) -> Optional[BusinessLead]:
        """Extract a lead from an <a> element linking to /maps/place/."""
        href = elem.attrib.get("href", "")

        if not href or "/maps/place/" not in href:
            return None
        if href in seen_urls:
            return None
        seen_urls.add(href)

        name = elem.attrib.get("aria-label", "")
        if not name:
            name = elem.get_all_text().strip() if elem.get_all_text() else ""
        if not name:
            return None

        # Walk up to find container text
        container = self._get_listing_container(elem)
        container_text = container.get_all_text() if container else ""

        if self._is_sponsored(container_text):
            return BusinessLead(
                source=self.SOURCE_NAME,
                name="",
                city=city,
                state=state,
                is_sponsored=True,
            )

        phone = self._extract_phone(container_text)
        address = self._extract_address(container_text)
        categories = self._extract_categories(container_text)

        return BusinessLead(
            source=self.SOURCE_NAME,
            name=name,
            phone=BusinessLead.clean_phone(phone),
            city=city,
            state=state,
            address=address,
            categories=categories,
            is_sponsored=False,
            detail_url=href,
        )

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Visit individual business page via StealthyFetcher to get website URL."""
        if not lead.detail_url:
            return lead

        try:
            # Use stealth fetcher for detail pages (lighter than dynamic)
            response = await self.engine.async_fetch_with_retry(
                lead.detail_url, self.SOURCE_NAME
            )
            if response is None:
                return lead

            page_text = response.get_all_text() if response.get_all_text() else ""

            # Extract phone
            phone_els = response.css('a[href^="tel:"]')
            if phone_els:
                phone_text = phone_els[0].get_all_text() or ""
                phone = self._extract_phone(phone_text)
                if phone:
                    lead.phone = BusinessLead.clean_phone(phone)

            # Extract website
            website_selectors = [
                'a[data-tooltip*="website"]',
                'a[aria-label*="Website"]',
            ]
            for sel in website_selectors:
                els = response.css(sel)
                if els:
                    href = els[0].attrib.get("href", "")
                    if href and "google.com" not in href:
                        lead.website = href
                        break

            # Extract address
            addr_selectors = [
                'button[data-tooltip*="address"]',
                'button[aria-label*="Address"]',
            ]
            for sel in addr_selectors:
                els = response.css(sel)
                if els:
                    lead.address = els[0].get_all_text().strip()
                    break

            # Check claimed
            if "Claim this business" in page_text:
                lead.is_claimed = False
            else:
                lead.is_claimed = True

        except Exception as e:
            logger.warning(f"Error getting details for {lead.name}: {e}")

        return lead

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_name(container, link_els) -> Optional[str]:
        """Extract business name from a container element."""
        name_selectors = [
            ".qBF1Pd.fontHeadlineSmall",
            ".fontHeadlineSmall",
            "div.NrDZNb",
        ]
        for sel in name_selectors:
            els = container.css(sel)
            if els:
                name = els[0].get_all_text().strip() if els[0].get_all_text() else ""
                if name:
                    return name

        # Fall back to aria-label on the link
        if link_els:
            aria = link_els[0].attrib.get("aria-label", "")
            if aria:
                return aria.strip()

        return None

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
    def _is_sponsored(text: str) -> bool:
        """Check if listing is sponsored/ad."""
        sponsored_terms = ["Sponsored", "Ad ", "Annonce", "Publicité"]
        text_lower = text.lower()
        if any(term.lower() in text_lower for term in sponsored_terms):
            return True
        return False

    @staticmethod
    def _extract_phone(text: str) -> Optional[str]:
        """Extract phone number from text."""
        patterns = [
            r"\+1[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
            r"\(\d{3}\)\s*\d{3}-\d{4}",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
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
    def _extract_categories(text: str) -> List[str]:
        """Extract business categories from text."""
        common_categories = [
            "Plumber", "Plumbing", "Dentist", "Dental", "Clinic",
            "Pest Control", "HVAC", "Electrician", "Roofing",
            "Contractor", "Locksmith", "Medical", "Doctor",
        ]
        found = []
        text_lower = text.lower()
        for cat in common_categories:
            if cat.lower() in text_lower:
                found.append(cat)
        return found
