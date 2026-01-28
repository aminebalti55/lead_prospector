"""
Google Maps scraper implementation using undetected-chromedriver.

Scrapes business listings from Google Maps search results.
Uses Selenium with anti-detection for reliable scraping.
Reference: docs/scraping/GOOGLE_MAPS.md
"""

import re
import time
import random
import logging
from typing import List, Optional
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base import BaseScraper, BusinessLead
from .browser_manager import (
    get_browser_executor,
    safe_get,
    safe_find_element,
    safe_find_elements,
    scroll_element,
    get_text_safe,
    get_attribute_safe,
)

logger = logging.getLogger(__name__)


class GoogleMapsScraper(BaseScraper):
    """
    Scraper for Google Maps business listings.

    Uses undetected-chromedriver for anti-bot evasion.
    Difficulty: HIGH (aggressive anti-bot measures)
    Rate limiting: 3-6s between requests, 150/hour
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
        query = f"{business_type} in {city} {state}"
        url = f"{self.BASE_URL}/{quote_plus(query)}?hl=en"

        print(f"[GOOGLE MAPS] Searching: {query}", flush=True)
        print(f"[GOOGLE MAPS] URL: {url}", flush=True)
        logger.info(f"Searching Google Maps: {query}")

        def _do_search(driver):
            print("[GOOGLE MAPS] Starting sync search...", flush=True)
            result = self._search_sync(driver, url, city, state, max_results)
            print(f"[GOOGLE MAPS] Sync search complete, found {len(result)} leads", flush=True)
            return result
        
        return await self.run_in_browser(_do_search)

    def _search_sync(self, driver, url: str, city: str, state: str, max_results: int) -> List[BusinessLead]:
        """Synchronous search implementation (runs in thread pool)."""
        leads: List[BusinessLead] = []
        
        print(f"[GMAPS_SYNC] Starting sync search...", flush=True)
        print(f"[GMAPS_SYNC] URL: {url}", flush=True)
        
        self.wait_and_record_sync()
        print(f"[GMAPS_SYNC] Rate limit wait complete", flush=True)
        
        if not safe_get(driver, url, wait_time=3.0):
            print(f"[GMAPS_SYNC] ERROR: Failed to load Google Maps page!", flush=True)
            logger.error("Failed to load Google Maps")
            return leads
        
        print(f"[GMAPS_SYNC] Page loaded successfully", flush=True)

        # Handle cookie consent
        self._handle_cookie_consent(driver)
        print(f"[GMAPS_SYNC] Cookie consent handled", flush=True)
        
        # Wait for results to load
        time.sleep(2)
        print(f"[GMAPS_SYNC] Post-load wait complete", flush=True)
        
        # Find the results container (scrollable panel)
        results_container = self._find_results_container(driver)
        if not results_container:
            print(f"[GMAPS_SYNC] WARNING: Could not find results container!", flush=True)
            logger.warning("Could not find results container")
            return leads
        
        print(f"[GMAPS_SYNC] Found results container", flush=True)

        # Scroll to load more results
        print(f"[GMAPS_SYNC] Scrolling for results (target: {max_results})...", flush=True)
        self._scroll_for_results(driver, results_container, max_results)
        print(f"[GMAPS_SYNC] Scrolling complete", flush=True)
        
        # Extract listings
        listings = self._get_listing_elements(driver)
        print(f"[GMAPS_SYNC] Found {len(listings)} listing elements", flush=True)
        logger.info(f"Found {len(listings)} listing elements")
        
        for listing in listings:
            if len(leads) >= max_results:
                break
            
            try:
                lead = self._extract_listing(driver, listing, city, state)
                if lead and not lead.is_sponsored:
                    leads.append(lead)
            except Exception as e:
                logger.debug(f"Error extracting listing: {e}")
                continue

        logger.info(f"Extracted {len(leads)} leads from Google Maps")
        return leads

    def _find_results_container(self, driver) -> Optional[any]:
        """Find the scrollable results panel."""
        selectors = [
            'div[role="feed"]',
            'div.m6QErb[aria-label]',
            'div.m6QErb.DxyBCb',
        ]
        
        for selector in selectors:
            try:
                container = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                return container
            except TimeoutException:
                continue
        
        return None

    def _scroll_for_results(self, driver, container, target_count: int, max_scrolls: int = 15):
        """Scroll the results panel to load more listings."""
        previous_count = 0
        
        for i in range(max_scrolls):
            # Scroll the container
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", 
                container
            )
            time.sleep(random.uniform(1.0, 2.0))
            
            # Check current count
            listings = self._get_listing_elements(driver)
            current_count = len(listings)
            
            if current_count >= target_count:
                logger.debug(f"Reached target count: {current_count}")
                break
            
            if current_count == previous_count:
                # No new results loaded
                time.sleep(1)
                listings = self._get_listing_elements(driver)
                if len(listings) == current_count:
                    logger.debug(f"No more results to load at {current_count}")
                    break
            
            previous_count = current_count

    def _get_listing_elements(self, driver) -> list:
        """Get all listing elements from the page."""
        selectors = [
            'div.Nv2PK',  # Main listing container
            'a[href*="/maps/place/"]',  # Place links
        ]
        
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements
        
        return []

    def _extract_listing(self, driver, element, city: str, state: str) -> Optional[BusinessLead]:
        """Extract business data from a listing element."""
        try:
            # Get the clickable link
            link = None
            try:
                link = element.find_element(By.CSS_SELECTOR, 'a.hfpxzc')
            except NoSuchElementException:
                if element.tag_name == 'a':
                    link = element
            
            if not link:
                return None
            
            detail_url = link.get_attribute('href')
            
            # Check for sponsored
            text_content = element.text
            if self._is_sponsored(text_content, detail_url):
                return BusinessLead(
                    source=self.SOURCE_NAME,
                    name="",
                    city=city,
                    state=state,
                    is_sponsored=True,
                )
            
            # Extract name
            name = None
            name_selectors = [
                '.qBF1Pd.fontHeadlineSmall',
                '.fontHeadlineSmall',
                'div.NrDZNb',
            ]
            for sel in name_selectors:
                try:
                    name_el = element.find_element(By.CSS_SELECTOR, sel)
                    name = name_el.text.strip()
                    if name:
                        break
                except NoSuchElementException:
                    continue
            
            if not name:
                aria_label = link.get_attribute('aria-label')
                name = aria_label.strip() if aria_label else None
            
            if not name:
                return None
            
            # Extract rating
            rating = None
            try:
                rating_el = element.find_element(By.CSS_SELECTOR, '.MW4etd')
                rating = self.clean_rating(rating_el.text)
            except NoSuchElementException:
                pass
            
            # Extract review count
            review_count = None
            try:
                review_el = element.find_element(By.CSS_SELECTOR, '.UY7F9')
                review_count = self.clean_review_count(review_el.text)
            except NoSuchElementException:
                pass
            
            # Extract phone from text
            phone = self._extract_phone(text_content)
            
            # Extract address
            address = self._extract_address(text_content)
            
            # Extract categories
            categories = self._extract_categories(text_content)
            
            return BusinessLead(
                source=self.SOURCE_NAME,
                name=name,
                phone=self.clean_phone(phone),
                city=city,
                state=state,
                rating=rating,
                review_count=review_count,
                address=address,
                categories=categories,
                is_sponsored=False,
                detail_url=detail_url,
            )
            
        except Exception as e:
            logger.debug(f"Error extracting listing: {e}")
            return None

    def _is_sponsored(self, text: str, url: Optional[str]) -> bool:
        """Check if listing is sponsored/ad."""
        sponsored_terms = ["Sponsored", "Sponsorisé", "Ad", "Annonce", "Publicité"]
        if any(term.lower() in text.lower() for term in sponsored_terms):
            return True
        if url and ("/aclk?" in url or "adurl=" in url):
            return True
        return False

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
        patterns = [
            r"\+1[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
            r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()
        return None

    def _extract_address(self, text: str) -> Optional[str]:
        """Extract address from text."""
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            # Look for street address pattern
            if re.match(r"^\d+\s+\w+", line) and len(line) < 100:
                return line
        return None

    def _extract_categories(self, text: str) -> List[str]:
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

    def _handle_cookie_consent(self, driver):
        """Handle Google cookie consent dialog if present."""
        consent_selectors = [
            'button[aria-label*="Accept"]',
            'button:contains("Accept all")',
            '#L2AGLb',  # Google's accept button ID
            'button.VfPpkd-LgbsSe-OWXEXe-k8QpJ',
        ]
        
        for selector in consent_selectors:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                time.sleep(1)
                logger.debug("Clicked cookie consent")
                return
            except NoSuchElementException:
                continue
            except Exception:
                continue

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Get detailed information from a business detail page."""
        if not lead.detail_url:
            return lead

        def _do_get_details(driver):
            return self._get_details_sync(driver, lead)
        
        return await self.run_in_browser(_do_get_details)

    def _get_details_sync(self, driver, lead: BusinessLead) -> BusinessLead:
        """Synchronous get_details implementation."""
        self.wait_and_record_sync()
        
        if not safe_get(driver, lead.detail_url, wait_time=2.0):
            return lead
        
        time.sleep(random.uniform(1.5, 2.5))
        
        try:
            # Extract phone
            phone_selectors = [
                'button[data-tooltip*="phone"]',
                'button[aria-label*="Phone"]',
                'a[href^="tel:"]',
            ]
            for sel in phone_selectors:
                try:
                    phone_el = driver.find_element(By.CSS_SELECTOR, sel)
                    phone_text = phone_el.text or phone_el.get_attribute('aria-label') or ''
                    phone = self._extract_phone(phone_text)
                    if phone:
                        lead.phone = self.clean_phone(phone)
                        break
                except NoSuchElementException:
                    continue
            
            # Extract website
            website_selectors = [
                'a[data-tooltip*="website"]',
                'a[aria-label*="Website"]',
                'a[href*="url?q="]',
            ]
            for sel in website_selectors:
                try:
                    website_el = driver.find_element(By.CSS_SELECTOR, sel)
                    href = website_el.get_attribute('href')
                    if href and 'google.com' not in href:
                        # Extract actual URL from Google redirect
                        if 'url?q=' in href:
                            import urllib.parse
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            if 'q' in parsed:
                                lead.website = parsed['q'][0]
                        else:
                            lead.website = href
                        break
                except NoSuchElementException:
                    continue
            
            # Extract full address
            address_selectors = [
                'button[data-tooltip*="address"]',
                'button[aria-label*="Address"]',
            ]
            for sel in address_selectors:
                try:
                    addr_el = driver.find_element(By.CSS_SELECTOR, sel)
                    lead.address = addr_el.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Check if business is claimed
            try:
                claim_el = driver.find_element(By.XPATH, '//*[contains(text(), "Claim this business")]')
                lead.is_claimed = False
            except NoSuchElementException:
                lead.is_claimed = True
            
            logger.debug(f"Got details for: {lead.name}")
            
        except Exception as e:
            logger.warning(f"Error getting details for {lead.name}: {e}")
        
        return lead
