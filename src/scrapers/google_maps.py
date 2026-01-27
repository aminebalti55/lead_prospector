"""
Google Maps scraper implementation.

Scrapes business listings from Google Maps search results.
Uses sync Playwright API in a thread pool to avoid Windows asyncio issues.
Reference: docs/scraping/GOOGLE_MAPS.md
"""

import asyncio
import random
import re
import time
import logging
from typing import List, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, BusinessLead
from .windows_compat import get_playwright_executor

logger = logging.getLogger(__name__)


class GoogleMapsScraper(BaseScraper):
    """
    Scraper for Google Maps business listings.

    Difficulty: HIGH (aggressive anti-bot measures)
    Rate limiting: 5-10s between requests, 100/hour
    """

    SOURCE_NAME = "google_maps"
    BASE_URL = "https://www.google.com/maps/search"

    async def search(
        self, business_type: str, city: str, state: str, max_results: int = 20
    ) -> List[BusinessLead]:
        """
        Search Google Maps for businesses.

        Args:
            business_type: Type of business (plumber, dentist, etc.)
            city: City name
            state: State abbreviation
            max_results: Maximum results to return

        Returns:
            List of BusinessLead objects
        """
        from urllib.parse import quote_plus
        
        query = f"{business_type} in {city} {state}"
        url = f"{self.BASE_URL}/{quote_plus(query)}?hl=en"

        logger.info(f"Searching Google Maps: {query}")
        await self.wait_and_record()

        def _do_search(context):
            return self._search_sync(context, url, city, state, max_results)
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        return await loop.run_in_executor(
            executor,
            lambda: _do_search(self._context)
        )

    def _search_sync(
        self, context, url: str, city: str, state: str, max_results: int
    ) -> List[BusinessLead]:
        """Synchronous search implementation (runs in thread pool)."""
        page = context.new_page()
        leads: List[BusinessLead] = []

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Handle Google cookie consent dialog
            self._handle_cookie_consent_sync(page)

            # Wait for results feed to load
            try:
                page.wait_for_selector('div[role="feed"]', timeout=15000)
            except PlaywrightTimeout:
                logger.warning("No results feed found - may be blocked or no results")
                return leads

            # Scroll to load more results
            self._scroll_for_results_sync(page, max_results)

            # Extract listings
            articles = page.query_selector_all('div[role="feed"] > div')

            for article in articles:
                if len(leads) >= max_results:
                    break

                try:
                    lead = self._extract_listing_sync(article, city, state)
                    if lead and not lead.is_sponsored:
                        leads.append(lead)
                except Exception as e:
                    logger.debug(f"Error extracting listing: {e}")
                    continue

            logger.info(f"Found {len(leads)} leads from Google Maps")

        except Exception as e:
            logger.error(f"Google Maps search failed: {e}")
        finally:
            page.close()

        return leads

    def _scroll_for_results_sync(self, page: Page, target_count: int) -> None:
        """Scroll the results feed to load more listings."""
        feed = page.query_selector('div[role="feed"]')
        if not feed:
            return

        previous_count = 0
        max_scrolls = min(target_count // 5 + 3, 15)

        for i in range(max_scrolls):
            feed.evaluate("el => el.scrollTop = el.scrollHeight")
            time.sleep(random.uniform(1.0, 2.0))

            articles = page.query_selector_all('div[role="feed"] > div')
            current_count = len(articles)

            if current_count >= target_count:
                break
            if current_count == previous_count:
                time.sleep(1)
                articles = page.query_selector_all('div[role="feed"] > div')
                if len(articles) == current_count:
                    break

            previous_count = current_count

    def _extract_listing_sync(
        self, element, city: str, state: str
    ) -> Optional[BusinessLead]:
        """Extract business data from a listing element (sync)."""

        # Check if this is a valid listing (has a link)
        link = element.query_selector("a.hfpxzc")
        if not link:
            return None

        # Get detail URL
        detail_url = link.get_attribute("href")

        # Check for sponsored content
        text_content = element.inner_text()
        is_sponsored = self._is_sponsored_text(text_content) or self._is_sponsored_url(
            detail_url
        )

        if is_sponsored:
            return BusinessLead(
                source=self.SOURCE_NAME,
                name="",
                city=city,
                state=state,
                is_sponsored=True,
            )

        # Extract name
        name_el = element.query_selector(".qBF1Pd.fontHeadlineSmall")
        name = name_el.inner_text() if name_el else None

        if not name:
            aria_label = link.get_attribute("aria-label")
            name = aria_label

        if not name:
            return None

        # Extract rating
        rating_el = element.query_selector(".MW4etd")
        rating_text = rating_el.inner_text() if rating_el else None
        rating = self.clean_rating(rating_text)

        # Extract review count
        review_el = element.query_selector(".UY7F9")
        review_text = review_el.inner_text() if review_el else None
        review_count = self.clean_review_count(review_text)

        # Extract website if available
        website = None
        website_selectors = [
            'a[href]:has-text("Website")',
            'a[aria-label*="website"]',
            "a.lcr4fd",
        ]
        for selector in website_selectors:
            try:
                website_el = element.query_selector(selector)
                if website_el:
                    href = website_el.get_attribute("href")
                    if href and not href.startswith("/aclk") and "google.com" not in href:
                        website = href
                        break
            except Exception:
                continue

        # Extract phone
        phone = self._extract_phone_from_text(text_content)

        # Extract address
        address = self._extract_address_from_text(text_content)

        # Extract categories
        categories = self._extract_categories_from_text(text_content)

        return BusinessLead(
            source=self.SOURCE_NAME,
            name=name.strip(),
            phone=self.clean_phone(phone),
            website=website,
            address=address,
            city=city,
            state=state,
            rating=rating,
            review_count=review_count,
            categories=categories,
            is_claimed=False,
            is_sponsored=is_sponsored,
            detail_url=detail_url,
        )

    def _is_sponsored_text(self, text: str) -> bool:
        """Check if text contains sponsored indicators."""
        sponsored_terms = ["Sponsored", "Sponsorisé", "Ad", "Annonce"]
        return any(term in text for term in sponsored_terms)

    def _is_sponsored_url(self, url: Optional[str]) -> bool:
        """Check if URL is an ad tracking URL."""
        if not url:
            return False
        return "/aclk?" in url or "adurl=" in url

    def _extract_phone_from_text(self, text: str) -> Optional[str]:
        """Extract phone number from text content."""
        patterns = [
            r"\+1[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
            r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()
        return None

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        """Extract address from text content."""
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if re.match(r"^\d+\s+\w+", line):
                return line
        return None

    def _extract_categories_from_text(self, text: str) -> List[str]:
        """Extract business categories from text."""
        common_categories = [
            "Plumber", "Plumbing", "Dentist", "Dental",
            "Pest Control", "HVAC", "Electrician", "Roofing",
            "Contractor", "Locksmith",
        ]
        found = []
        for cat in common_categories:
            if cat.lower() in text.lower():
                found.append(cat)
        return found

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Get detailed information from a business detail page."""
        if not lead.detail_url:
            return lead

        await self.wait_and_record()

        def _do_get_details(context):
            return self._get_details_sync(context, lead)
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        return await loop.run_in_executor(
            executor,
            lambda: _do_get_details(self._context)
        )

    def _get_details_sync(self, context, lead: BusinessLead) -> BusinessLead:
        """Synchronous get_details implementation."""
        page = context.new_page()

        try:
            page.goto(lead.detail_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("h1", timeout=10000)
            time.sleep(random.uniform(1.0, 2.0))

            # Extract phone
            phone_button = page.query_selector(
                'button[aria-label*="phone"], button[aria-label*="Phone"]'
            )
            if phone_button:
                phone_text = phone_button.inner_text()
                lead.phone = self.clean_phone(phone_text)

            # Extract website
            website_link = page.query_selector(
                'a[aria-label*="Website"], a[aria-label*="Site"]'
            )
            if website_link:
                lead.website = website_link.get_attribute("href")

            # Extract full address
            address_button = page.query_selector(
                'button[aria-label*="Address"], button[aria-label*="Adresse"]'
            )
            if address_button:
                lead.address = address_button.inner_text()

            # Check claimed status
            claim_button = page.query_selector(
                'button:has-text("Claim this business")'
            )
            lead.is_claimed = claim_button is None

            logger.debug(f"Got details for: {lead.name}")

        except Exception as e:
            logger.warning(f"Failed to get details for {lead.name}: {e}")
        finally:
            page.close()

        return lead

    def _handle_cookie_consent_sync(self, page: Page) -> None:
        """Handle Google cookie consent dialog if present."""
        try:
            consent_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("Tout accepter")',
                'button:has-text("Akzeptieren")',
                'button:has-text("Aceptar todo")',
                'button[aria-label*="Accept"]',
                "button.VfPpkd-LgbsSe-OWXEXe-k8QpJ",
            ]

            for selector in consent_selectors:
                try:
                    consent_btn = page.query_selector(selector)
                    if consent_btn:
                        consent_btn.click()
                        logger.debug("Clicked cookie consent button")
                        time.sleep(2)
                        return
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Cookie consent handling: {e}")
