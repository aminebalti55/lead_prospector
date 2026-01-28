"""
YellowPages scraper implementation using undetected-chromedriver.

Scrapes business listings from YellowPages directory.
Uses Selenium with anti-detection for reliable scraping.
Reference: docs/scraping/YELLOWPAGES.md
"""

import re
import time
import random
import logging
from typing import List, Optional
from urllib.parse import urlencode

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base import BaseScraper, BusinessLead
from .browser_manager import (
    get_browser_executor,
    safe_get,
    safe_find_elements,
    scroll_page,
)

logger = logging.getLogger(__name__)


class YellowPagesScraper(BaseScraper):
    """
    Scraper for YellowPages business listings.

    Uses undetected-chromedriver for anti-bot evasion.
    Difficulty: MEDIUM
    Rate limiting: 1-3s between requests, 300/hour
    """

    SOURCE_NAME = "yellowpages"
    BASE_URL = "https://www.yellowpages.com/search"

    async def search(
        self, business_type: str, city: str, state: str, max_results: int = 20
    ) -> List[BusinessLead]:
        """Search YellowPages for businesses."""
        location = f"{city}, {state}"
        logger.info(f"Searching YellowPages: {business_type} in {location}")

        def _do_search(driver):
            return self._search_sync(driver, business_type, city, state, location, max_results)
        
        return await self.run_in_browser(_do_search)

    def _search_sync(self, driver, business_type: str, city: str, state: str,
                     location: str, max_results: int) -> List[BusinessLead]:
        """Synchronous search implementation."""
        leads: List[BusinessLead] = []
        page_num = 1
        
        while len(leads) < max_results:
            params = {
                "search_terms": business_type,
                "geo_location_terms": location,
                "page": page_num,
            }
            url = f"{self.BASE_URL}?{urlencode(params)}"
            
            self.wait_and_record_sync()
            
            if not safe_get(driver, url, wait_time=2.0):
                break
            
            # Wait for results
            time.sleep(random.uniform(1.5, 2.5))
            
            # Check for empty/blocked page
            try:
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                if len(page_text.strip()) < 300:
                    logger.warning("YellowPages page appears empty or blocked")
                    break
            except Exception:
                break
            
            # Extract listings
            page_leads = self._extract_listings(driver, city, state)
            
            if not page_leads:
                logger.debug("No more listings found")
                break
            
            leads.extend(page_leads)
            page_num += 1
            
            if len(leads) >= max_results:
                leads = leads[:max_results]
                break
        
        logger.info(f"Found {len(leads)} leads from YellowPages")
        return leads

    def _extract_listings(self, driver, city: str, state: str) -> List[BusinessLead]:
        """Extract business listings from the current page."""
        leads = []
        
        # Find business name links
        selectors = [
            'a.business-name',
            'a[href*="/mip/"]',
            '.info-primary a[href*="/mip/"]',
        ]
        
        seen_urls = set()
        
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for elem in elements:
                try:
                    name = elem.text.strip()
                    href = elem.get_attribute('href')
                    
                    if not name or len(name) < 2:
                        continue
                    if not href:
                        continue
                    if href in seen_urls:
                        continue
                    
                    seen_urls.add(href)
                    
                    # Get container for more info
                    container = self._get_listing_container(elem)
                    container_text = container.text if container else ""
                    
                    # Skip ads
                    if container_text.strip().startswith('Ad'):
                        continue
                    
                    # Extract phone
                    phone = self._extract_phone(container_text)
                    
                    # Extract address
                    address = self._extract_address(container_text)
                    
                    # Extract website
                    website = self._extract_website(container)
                    
                    # Build full URL
                    if href.startswith('/'):
                        href = f"https://www.yellowpages.com{href}"
                    
                    lead = BusinessLead(
                        source=self.SOURCE_NAME,
                        name=name,
                        phone=self.clean_phone(phone),
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

    def _get_listing_container(self, element):
        """Get the parent container of a listing element."""
        try:
            container = element
            for _ in range(10):
                container = container.find_element(By.XPATH, '..')
                if len(container.text) > 100:
                    return container
            return element.find_element(By.XPATH, '..')
        except Exception:
            return None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone from text."""
        match = re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', text)
        if match:
            return match.group()
        return None

    def _extract_address(self, text: str) -> Optional[str]:
        """Extract address from text."""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\s+\w+', line) and len(line) < 100:
                return line
        return None

    def _extract_website(self, container) -> Optional[str]:
        """Extract website URL from container."""
        if not container:
            return None
        try:
            website_el = container.find_element(By.CSS_SELECTOR, 'a.track-visit-website')
            return website_el.get_attribute('href')
        except NoSuchElementException:
            return None

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Get detailed information from YellowPages business page."""
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
        
        time.sleep(random.uniform(1.0, 2.0))
        
        try:
            # Extract phone if missing
            if not lead.phone:
                try:
                    phone_el = driver.find_element(By.CSS_SELECTOR, '.phone')
                    lead.phone = self.clean_phone(phone_el.text)
                except NoSuchElementException:
                    pass
            
            # Extract website if missing
            if not lead.website:
                try:
                    website_el = driver.find_element(By.CSS_SELECTOR, 'a.website-link')
                    lead.website = website_el.get_attribute('href')
                except NoSuchElementException:
                    pass
            
            # Extract full address
            try:
                address_el = driver.find_element(By.CSS_SELECTOR, '.address')
                lead.address = address_el.text.strip()
            except NoSuchElementException:
                pass
            
            # Check claimed status
            try:
                driver.find_element(By.CSS_SELECTOR, '.claimed-label')
                lead.is_claimed = True
            except NoSuchElementException:
                lead.is_claimed = False
            
            # Extract additional info
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            
            years_match = re.search(r'(\d+)\s*years?\s*in\s*business', page_text, re.IGNORECASE)
            if years_match:
                lead.extra_data["years_in_business"] = int(years_match.group(1))
            
            bbb_match = re.search(r'BBB Rating:\s*([A-F][+-]?)', page_text)
            if bbb_match:
                lead.extra_data["bbb_rating"] = bbb_match.group(1)
            
            logger.debug(f"Got YellowPages details for: {lead.name}")
            
        except Exception as e:
            logger.warning(f"Error getting YellowPages details for {lead.name}: {e}")
        
        return lead
