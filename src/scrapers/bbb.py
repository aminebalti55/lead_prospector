"""
Better Business Bureau (BBB) scraper implementation using undetected-chromedriver.

Scrapes business listings from BBB directory.
Uses Selenium with anti-detection for reliable scraping.
Reference: docs/scraping/BBB.md
"""

import re
import time
import random
import logging
from typing import List, Optional
from datetime import datetime
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


class BBBScraper(BaseScraper):
    """
    Scraper for Better Business Bureau listings.

    Uses undetected-chromedriver for anti-bot evasion.
    Difficulty: MEDIUM
    Rate limiting: 2-4s between requests, 200/hour
    """

    SOURCE_NAME = "bbb"
    BASE_URL = "https://www.bbb.org/search"

    async def search(
        self, business_type: str, city: str, state: str, max_results: int = 20
    ) -> List[BusinessLead]:
        """Search BBB for businesses."""
        location = f"{city}, {state}"
        logger.info(f"Searching BBB: {business_type} in {location}")

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
                "find_country": "USA",
                "find_text": business_type,
                "find_loc": location,
                "page": page_num,
            }
            url = f"{self.BASE_URL}?{urlencode(params)}"
            
            self.wait_and_record_sync()
            
            if not safe_get(driver, url, wait_time=2.5):
                break
            
            # Handle cookie consent
            self._handle_cookie_consent(driver)
            
            # Wait for results
            time.sleep(random.uniform(2.0, 3.0))
            
            # Check for empty/blocked page
            try:
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                if len(page_text.strip()) < 300:
                    logger.warning("BBB page appears empty or blocked")
                    break
            except Exception:
                break
            
            # Extract listings
            page_leads = self._extract_listings(driver, city, state)
            
            if not page_leads:
                logger.debug("No more listings found")
                break
            
            # Deduplicate
            existing_urls = {l.detail_url for l in leads if l.detail_url}
            page_leads = [l for l in page_leads if l.detail_url not in existing_urls]
            
            leads.extend(page_leads)
            page_num += 1
            
            if len(leads) >= max_results:
                leads = leads[:max_results]
                break
        
        logger.info(f"Found {len(leads)} leads from BBB")
        return leads

    def _handle_cookie_consent(self, driver):
        """Handle BBB cookie consent banner if present."""
        try:
            consent_btn = driver.find_element(
                By.XPATH, '//button[contains(text(), "Accept All Cookies")]'
            )
            consent_btn.click()
            time.sleep(0.5)
        except NoSuchElementException:
            pass
        except Exception:
            pass

    def _extract_listings(self, driver, city: str, state: str) -> List[BusinessLead]:
        """Extract business listings from the current page."""
        leads = []
        
        # Find profile links
        elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/profile/"]')
        
        seen_urls = set()
        
        for elem in elements:
            try:
                name = elem.text.strip()
                href = elem.get_attribute('href')
                
                if not name or len(name) < 2:
                    continue
                if not href or '/profile/' not in href:
                    continue
                if 'advertisement' in name.lower():
                    continue
                if href in seen_urls:
                    continue
                
                seen_urls.add(href)
                
                # Get container for more info
                container = self._get_listing_container(elem)
                container_text = container.text if container else ""
                
                # Skip advertisements
                if 'advertisement:' in container_text.lower():
                    continue
                
                # Extract phone
                phone = self._extract_phone(container_text)
                
                # Extract BBB rating
                bbb_rating = self._extract_bbb_rating(container_text)
                
                # Check accreditation
                accredited = 'Accredited' in container_text
                
                # Build full URL
                if href.startswith('/'):
                    href = f"https://www.bbb.org{href}"
                
                extra_data = {"bbb_accredited": accredited}
                if bbb_rating:
                    extra_data["bbb_rating"] = bbb_rating
                
                lead = BusinessLead(
                    source=self.SOURCE_NAME,
                    name=name,
                    phone=self.clean_phone(phone),
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

    def _extract_bbb_rating(self, text: str) -> Optional[str]:
        """Extract BBB rating from text."""
        match = re.search(r'BBB Rating:\s*([A-F][+-]?)', text)
        if match:
            return match.group(1)
        return None

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Get detailed information from BBB business profile."""
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
        
        self._handle_cookie_consent(driver)
        time.sleep(random.uniform(1.5, 2.5))
        
        try:
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            
            # Extract phone
            if not lead.phone:
                try:
                    phone_el = driver.find_element(By.CSS_SELECTOR, 'a[href^="tel:"]')
                    lead.phone = self.clean_phone(phone_el.text)
                except NoSuchElementException:
                    pass
            
            # Extract website
            website_selectors = [
                'a[data-testid="website-link"]',
                'a[href*="://"][target="_blank"]',
            ]
            for sel in website_selectors:
                try:
                    website_el = driver.find_element(By.CSS_SELECTOR, sel)
                    href = website_el.get_attribute('href')
                    if href and 'bbb.org' not in href:
                        lead.website = href
                        break
                except NoSuchElementException:
                    continue
            
            # Extract address
            try:
                address_el = driver.find_element(By.CSS_SELECTOR, '[data-testid="business-address"]')
                lead.address = address_el.text.strip()
            except NoSuchElementException:
                pass
            
            # Extract BBB rating
            rating_match = re.search(r'BBB Rating:\s*([A-F][+-]?)', page_text)
            if rating_match:
                lead.extra_data["bbb_rating"] = rating_match.group(1)
            
            # Check accreditation
            try:
                driver.find_element(By.CSS_SELECTOR, 'img[alt*="Accredited Business"]')
                lead.extra_data["bbb_accredited"] = True
            except NoSuchElementException:
                lead.extra_data["bbb_accredited"] = False
            
            # Extract complaints
            complaint_match = re.search(
                r'(\d+)\s*complaints?\s*closed\s*in\s*last\s*3\s*years?',
                page_text, re.IGNORECASE
            )
            if complaint_match:
                lead.extra_data["complaints_last_3_years"] = int(complaint_match.group(1))
            
            # Extract years in business
            years_match = re.search(r'Business Started:\s*(\d{4})', page_text)
            if years_match:
                start_year = int(years_match.group(1))
                lead.extra_data["year_started"] = start_year
                lead.extra_data["years_in_business"] = datetime.now().year - start_year
            
            logger.debug(f"Got BBB details for: {lead.name}")
            
        except Exception as e:
            logger.warning(f"Error getting BBB details for {lead.name}: {e}")
        
        return lead
