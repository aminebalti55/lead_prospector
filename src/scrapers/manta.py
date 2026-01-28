"""
Manta scraper implementation using undetected-chromedriver.

Scrapes business listings from Manta business directory.
Uses Selenium with anti-detection for reliable scraping.
Reference: docs/scraping/MANTA.md
"""

import re
import time
import random
import logging
from typing import List, Optional
from datetime import datetime
from urllib.parse import urlencode, urlparse, parse_qs, unquote

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


class MantaScraper(BaseScraper):
    """
    Scraper for Manta business directory listings.

    Uses undetected-chromedriver for anti-bot evasion.
    Difficulty: MEDIUM
    Rate limiting: 2-5s between requests, 150/hour
    """

    SOURCE_NAME = "manta"
    BASE_URL = "https://www.manta.com/search"

    async def search(
        self, business_type: str, city: str, state: str, max_results: int = 20
    ) -> List[BusinessLead]:
        """Search Manta for businesses."""
        logger.info(f"Searching Manta: {business_type} in {city}, {state}")

        def _do_search(driver):
            return self._search_sync(driver, business_type, city, state, max_results)
        
        return await self.run_in_browser(_do_search)

    def _search_sync(self, driver, business_type: str, city: str, state: str,
                     max_results: int) -> List[BusinessLead]:
        """Synchronous search implementation."""
        leads: List[BusinessLead] = []
        page_num = 1
        
        # Visit homepage first to establish session
        safe_get(driver, "https://www.manta.com", wait_time=2.0)
        
        while len(leads) < max_results:
            params = {
                "search": business_type,
                "country": "United States",
                "state": state,
                "city": city,
                "page_size": 25,
                "pg": page_num,
            }
            url = f"{self.BASE_URL}?{urlencode(params)}"
            
            self.wait_and_record_sync()
            
            if not safe_get(driver, url, wait_time=2.5):
                break
            
            # Wait for results
            time.sleep(random.uniform(2.0, 3.5))
            
            # Check for empty/blocked page
            try:
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                if len(page_text.strip()) < 300:
                    logger.warning("Manta page appears empty or blocked")
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
        
        logger.info(f"Found {len(leads)} leads from Manta")
        return leads

    def _extract_listings(self, driver, city: str, state: str) -> List[BusinessLead]:
        """Extract business listings from the current page."""
        leads = []
        
        # Find company links
        elements = driver.find_elements(By.CSS_SELECTOR, 'a[href^="/c/"]:not([href*="category"])')
        
        seen_urls = set()
        
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
                
                # Skip promoted listings
                if '★' in container_text or 'Promoted' in container_text:
                    continue
                
                # Extract phone
                phone = self._extract_phone(container_text)
                
                # Extract address
                address = self._extract_address(container_text)
                
                # Check claimed status
                is_claimed = 'CLAIMED' in container_text
                
                # Extract employee count
                emp_match = re.search(r'(\d+)\s*employees?', container_text, re.IGNORECASE)
                employee_count = int(emp_match.group(1)) if emp_match else None
                
                # Extract years in business
                years_match = re.search(r'(\d+)\s*years?\s*in\s*business', container_text, re.IGNORECASE)
                years_in_business = int(years_match.group(1)) if years_match else None
                
                # Build full URL
                if href.startswith('/'):
                    href = f"https://www.manta.com{href}"
                
                extra_data = {}
                if employee_count:
                    extra_data["employee_count"] = employee_count
                if years_in_business:
                    extra_data["years_in_business"] = years_in_business
                
                lead = BusinessLead(
                    source=self.SOURCE_NAME,
                    name=name,
                    phone=self.clean_phone(phone),
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

    def _get_listing_container(self, element):
        """Get the parent container of a listing element."""
        try:
            container = element
            for _ in range(10):
                container = container.find_element(By.XPATH, '..')
                if len(container.text) > 50:
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

    def _unwrap_redirect_url(self, url: str) -> str:
        """Unwrap Manta's urlverify redirect URLs."""
        if "/urlverify" in url and "redirect=" in url:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if "redirect" in query_params:
                return unquote(query_params["redirect"][0])
        return url

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Get detailed information from Manta business profile."""
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
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            
            # Extract phone
            if not lead.phone:
                try:
                    phone_el = driver.find_element(By.CSS_SELECTOR, 'a[href^="tel:"]')
                    lead.phone = self.clean_phone(phone_el.text)
                except NoSuchElementException:
                    pass
            
            # Extract website
            if not lead.website:
                try:
                    website_el = driver.find_element(By.CSS_SELECTOR, 'a[href*="/urlverify"]')
                    href = website_el.get_attribute('href')
                    if href:
                        lead.website = self._unwrap_redirect_url(href)
                except NoSuchElementException:
                    pass
            
            # Extract address
            try:
                address_el = driver.find_element(By.CSS_SELECTOR, '[data-testid="business-address"], .address')
                lead.address = address_el.text.strip()
            except NoSuchElementException:
                pass
            
            # Extract SIC code
            sic_match = re.search(r'SIC\s*(?:Code)?:\s*(\d+)', page_text)
            if sic_match:
                lead.extra_data["sic_code"] = sic_match.group(1)
            
            # Extract contact name
            contact_match = re.search(r'Contact(?:\s*Name)?:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)', page_text)
            if contact_match:
                lead.extra_data["contact_name"] = contact_match.group(1)
            
            # Extract employee count
            emp_match = re.search(r'Employees?:\s*(\d+)', page_text)
            if emp_match:
                lead.extra_data["employee_count"] = int(emp_match.group(1))
            
            # Extract years in business
            date_match = re.search(r'(?:Founded|Opened|Started):\s*(\d{4})', page_text)
            if date_match:
                start_year = int(date_match.group(1))
                lead.extra_data["year_started"] = start_year
                lead.extra_data["years_in_business"] = datetime.now().year - start_year
            
            logger.debug(f"Got Manta details for: {lead.name}")
            
        except Exception as e:
            logger.warning(f"Error getting Manta details for {lead.name}: {e}")
        
        return lead
