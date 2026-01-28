"""
Yelp scraper implementation using undetected-chromedriver.

Scrapes business listings from Yelp search results.
Uses Selenium with anti-detection for reliable scraping.
Reference: docs/scraping/YELP.md
"""

import re
import time
import random
import logging
from typing import List, Optional
from urllib.parse import urlencode, urlparse, parse_qs

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base import BaseScraper, BusinessLead
from .browser_manager import (
    get_browser_executor,
    safe_get,
    safe_find_element,
    safe_find_elements,
    scroll_page,
    get_text_safe,
    get_attribute_safe,
)

logger = logging.getLogger(__name__)


class YelpScraper(BaseScraper):
    """
    Scraper for Yelp business listings.

    Uses undetected-chromedriver for anti-bot evasion.
    Difficulty: MEDIUM-HIGH
    Rate limiting: 2-4s between requests, 200/hour
    Pagination: start param increments by 10
    """

    SOURCE_NAME = "yelp"
    BASE_URL = "https://www.yelp.com/search"

    async def search(
        self, business_type: str, city: str, state: str, max_results: int = 20
    ) -> List[BusinessLead]:
        """Search Yelp for businesses."""
        location = f"{city}, {state}"
        logger.info(f"Searching Yelp: {business_type} in {location}")

        def _do_search(driver):
            return self._search_sync(driver, business_type, city, state, location, max_results)
        
        return await self.run_in_browser(_do_search)

    def _search_sync(self, driver, business_type: str, city: str, state: str, 
                     location: str, max_results: int) -> List[BusinessLead]:
        """Synchronous search implementation."""
        leads: List[BusinessLead] = []
        start = 0
        
        while len(leads) < max_results:
            params = {
                "find_desc": business_type,
                "find_loc": location,
                "start": start,
            }
            url = f"{self.BASE_URL}?{urlencode(params)}"
            
            self.wait_and_record_sync()
            
            if not safe_get(driver, url, wait_time=3.0):
                break
            
            # Wait for results to load
            time.sleep(random.uniform(2.0, 3.5))
            
            # Check for bot detection
            if self._check_for_blocking(driver):
                logger.warning("Yelp appears to be blocking")
                break
            
            # Extract listings
            page_leads = self._extract_listings(driver, city, state)
            
            if not page_leads:
                logger.debug("No more listings found")
                break
            
            leads.extend(page_leads)
            start += 10
            
            if len(leads) >= max_results:
                leads = leads[:max_results]
                break
        
        logger.info(f"Found {len(leads)} leads from Yelp")
        return leads

    def _check_for_blocking(self, driver) -> bool:
        """Check if Yelp is blocking us."""
        try:
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            blocking_indicators = [
                "Device verification",
                "Please verify you're a human",
                "unusual traffic",
                "Access denied",
            ]
            return any(ind.lower() in page_text.lower() for ind in blocking_indicators)
        except Exception:
            return False

    def _extract_listings(self, driver, city: str, state: str) -> List[BusinessLead]:
        """Extract business listings from the current page."""
        leads = []
        
        # Find all business links
        listing_selectors = [
            'a[href*="/biz/"]',
            '[data-testid="serp-ia-card"] a',
            '.businessName__09f24__3Wql2 a',
        ]
        
        seen_urls = set()
        
        for selector in listing_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for elem in elements:
                try:
                    href = elem.get_attribute('href')
                    name = elem.text.strip()
                    
                    if not name or len(name) < 2:
                        continue
                    if not href or '/biz/' not in href:
                        continue
                    if '/adredir' in href or '/aclk' in href:
                        continue
                    if href in seen_urls:
                        continue
                    
                    seen_urls.add(href)
                    
                    # Get container for more info
                    container = self._get_listing_container(elem)
                    container_text = container.text if container else ""
                    
                    # Skip sponsored
                    if 'Sponsored' in container_text or container_text.startswith('Ad'):
                        continue
                    
                    # Extract rating
                    rating = self._extract_rating(container_text)
                    
                    # Extract review count
                    review_count = self._extract_review_count(container_text)
                    
                    # Extract phone
                    phone = self._extract_phone(container_text)
                    
                    # Build full URL
                    if href.startswith('/'):
                        href = f"https://www.yelp.com{href}"
                    
                    lead = BusinessLead(
                        source=self.SOURCE_NAME,
                        name=name,
                        phone=self.clean_phone(phone),
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

    def _get_listing_container(self, element):
        """Get the parent container of a listing element."""
        try:
            container = element
            for _ in range(15):
                container = container.find_element(By.XPATH, '..')
                if len(container.text) > 100:
                    return container
            return element.find_element(By.XPATH, '..')
        except Exception:
            return None

    def _extract_rating(self, text: str) -> Optional[float]:
        """Extract rating from text."""
        match = re.search(r'(\d+\.?\d*)\s*star', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    def _extract_review_count(self, text: str) -> Optional[int]:
        """Extract review count from text."""
        match = re.search(r'\((\d+)\s*reviews?\)', text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone from text."""
        match = re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', text)
        if match:
            return match.group()
        return None

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Get detailed information from Yelp business page."""
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
            try:
                phone_el = driver.find_element(By.CSS_SELECTOR, 'a[href^="tel:"]')
                lead.phone = self.clean_phone(phone_el.text)
            except NoSuchElementException:
                pass
            
            # Extract website
            try:
                website_el = driver.find_element(By.CSS_SELECTOR, 'a[href*="biz_redir"]')
                href = website_el.get_attribute('href')
                if href:
                    lead.website = self._unwrap_redirect_url(href)
            except NoSuchElementException:
                pass
            
            # Extract address
            try:
                address_el = driver.find_element(By.TAG_NAME, 'address')
                lead.address = address_el.text.strip()
            except NoSuchElementException:
                pass
            
            # Check claimed status
            try:
                driver.find_element(By.XPATH, '//*[contains(text(), "Claimed")]')
                lead.is_claimed = True
            except NoSuchElementException:
                lead.is_claimed = False
            
            # Extract years in business
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            years_match = re.search(r'(\d+)\s*years?\s*in\s*business', page_text, re.IGNORECASE)
            if years_match:
                lead.extra_data["years_in_business"] = int(years_match.group(1))
            
            logger.debug(f"Got Yelp details for: {lead.name}")
            
        except Exception as e:
            logger.warning(f"Error getting Yelp details for {lead.name}: {e}")
        
        return lead

    def _unwrap_redirect_url(self, url: str) -> str:
        """Unwrap Yelp's biz_redir redirect URLs."""
        if "biz_redir" in url:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if "url" in query_params:
                return query_params["url"][0]
        return url
