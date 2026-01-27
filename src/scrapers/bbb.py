"""
Better Business Bureau (BBB) scraper implementation.

Scrapes business listings from BBB directory.
Uses sync Playwright API in a thread pool to avoid Windows asyncio issues.
Reference: docs/scraping/BBB.md
"""

import asyncio
import random
import re
import time
import logging
from typing import List, Optional
from urllib.parse import quote_plus, urlencode
from datetime import datetime

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, BusinessLead
from .windows_compat import get_playwright_executor

logger = logging.getLogger(__name__)


class BBBScraper(BaseScraper):
    """
    Scraper for Better Business Bureau listings.

    Difficulty: MEDIUM
    Rate limiting: 3-5s between searches, 120/hour
    """

    SOURCE_NAME = "bbb"
    BASE_URL = "https://www.bbb.org/search"

    async def search(
        self, business_type: str, city: str, state: str, max_results: int = 20
    ) -> List[BusinessLead]:
        """Search BBB for businesses."""
        location = f"{city}, {state}"
        logger.info(f"Searching BBB: {business_type} in {location}")

        def _do_search(context):
            return self._search_sync(context, business_type, city, state, location, max_results)
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        return await loop.run_in_executor(
            executor,
            lambda: _do_search(self._context)
        )

    def _search_sync(
        self, context, business_type: str, city: str, state: str, location: str, max_results: int
    ) -> List[BusinessLead]:
        """Synchronous search implementation (runs in thread pool)."""
        leads: List[BusinessLead] = []
        page_num = 1
        page = context.new_page()

        try:
            while len(leads) < max_results:
                params = {
                    "find_country": "USA",
                    "find_text": business_type,
                    "find_loc": location,
                    "page": page_num,
                }
                url = f"{self.BASE_URL}?{urlencode(params)}"

                self.rate_limiter.wait_sync(self.SOURCE_NAME)
                self.rate_limiter.record_request(self.SOURCE_NAME)
                
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Handle cookie consent
                self._handle_cookie_consent_sync(page)

                try:
                    selectors = ["main", 'a[href*="/profile/"]']
                    found = False
                    for selector in selectors:
                        try:
                            page.wait_for_selector(selector, timeout=8000)
                            found = True
                            break
                        except PlaywrightTimeout:
                            continue

                    if not found:
                        page.wait_for_load_state("networkidle", timeout=15000)

                    time.sleep(random.uniform(1.0, 2.0))

                    page_text = page.inner_text("body")
                    if len(page_text.strip()) < 200:
                        logger.warning("BBB page appears empty or blocked")
                        break

                except PlaywrightTimeout:
                    logger.warning("BBB search timed out")
                    break

                # Extract using JavaScript
                extracted_data = page.evaluate("""() => {
                    const results = [];
                    const seen = new Set();
                    const profileLinks = document.querySelectorAll('a[href*="/profile/"]');
                    
                    for (const link of profileLinks) {
                        const href = link.getAttribute('href');
                        const name = link.innerText.trim();
                        
                        if (!name || name.length < 2 || seen.has(href)) continue;
                        if (name.toLowerCase().includes('advertisement')) continue;
                        seen.add(href);
                        
                        let container = link.parentElement;
                        let attempts = 0;
                        while (container && container.innerText.length < 100 && attempts < 10) {
                            container = container.parentElement;
                            attempts++;
                        }
                        
                        const containerText = container ? container.innerText : '';
                        if (containerText.toLowerCase().includes('advertisement:')) continue;
                        
                        const phoneMatch = containerText.match(/\\(\\d{3}\\)\\s*\\d{3}-\\d{4}/);
                        const ratingMatch = containerText.match(/BBB Rating:\\s*([A-F][+-]?)/);
                        const accredited = containerText.includes('Accredited');
                        
                        results.push({
                            name: name,
                            href: href.startsWith('/') ? 'https://www.bbb.org' + href : href,
                            phone: phoneMatch ? phoneMatch[0] : null,
                            bbb_rating: ratingMatch ? ratingMatch[1] : null,
                            accredited: accredited
                        });
                    }
                    return results;
                }""")

                page_leads = []
                seen_urls = {lead.detail_url for lead in leads if lead.detail_url}

                if extracted_data:
                    for data in extracted_data:
                        if data.get("name"):
                            detail_url = data.get("href")
                            if detail_url and detail_url in seen_urls:
                                continue
                            if detail_url:
                                seen_urls.add(detail_url)

                            extra_data = {}
                            if data.get("bbb_rating"):
                                extra_data["bbb_rating"] = data["bbb_rating"]
                            extra_data["bbb_accredited"] = data.get("accredited", False)

                            lead = BusinessLead(
                                source=self.SOURCE_NAME,
                                name=data["name"].strip(),
                                phone=self.clean_phone(data.get("phone")),
                                city=city,
                                state=state,
                                detail_url=detail_url,
                                is_sponsored=False,
                                extra_data=extra_data,
                            )
                            page_leads.append(lead)

                if not page_leads:
                    break

                leads.extend(page_leads)
                page_num += 1

                if len(leads) >= max_results:
                    leads = leads[:max_results]
                    break

            logger.info(f"Found {len(leads)} leads from BBB")

        except Exception as e:
            logger.error(f"BBB search failed: {e}")
        finally:
            page.close()

        return leads

    def _handle_cookie_consent_sync(self, page: Page) -> None:
        """Handle BBB cookie consent banner if present (sync version)."""
        try:
            consent_btn = page.query_selector('button:has-text("Accept All Cookies")')
            if consent_btn:
                consent_btn.click()
                time.sleep(0.5)
        except Exception:
            pass

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Get detailed information from BBB business profile."""
        if not lead.detail_url:
            return lead

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
            self.rate_limiter.wait_sync(self.SOURCE_NAME)
            self.rate_limiter.record_request(self.SOURCE_NAME)
            
            page.goto(lead.detail_url, wait_until="domcontentloaded", timeout=30000)
            self._handle_cookie_consent_sync(page)
            time.sleep(random.uniform(1.5, 2.5))

            page_text = page.inner_text("body")

            if not lead.phone:
                phone_el = page.query_selector('a[href^="tel:"]')
                if phone_el:
                    lead.phone = self.clean_phone(phone_el.inner_text())

            website_el = page.query_selector('a[data-testid="website-link"]')
            if not website_el:
                website_el = page.query_selector('a:has-text("Visit Website")')
            if website_el:
                lead.website = website_el.get_attribute("href")

            address_el = page.query_selector('[data-testid="business-address"]')
            if address_el:
                lead.address = address_el.inner_text()

            rating_match = re.search(r"BBB Rating:\s*([A-F][+-]?)", page_text)
            if rating_match:
                lead.extra_data["bbb_rating"] = rating_match.group(1)

            accred_el = page.query_selector('img[alt*="Accredited Business"]')
            lead.extra_data["bbb_accredited"] = accred_el is not None

            complaint_match = re.search(
                r"(\d+)\s*complaints?\s*closed\s*in\s*last\s*3\s*years?",
                page_text, re.IGNORECASE
            )
            if complaint_match:
                lead.extra_data["complaints_last_3_years"] = int(complaint_match.group(1))

            years_match = re.search(r"Business Started:\s*(\d{4})", page_text)
            if years_match:
                start_year = int(years_match.group(1))
                lead.extra_data["year_started"] = start_year
                lead.extra_data["years_in_business"] = datetime.now().year - start_year

            logger.debug(f"Got BBB details for: {lead.name}")

        except Exception as e:
            logger.warning(f"Failed to get BBB details for {lead.name}: {e}")
        finally:
            page.close()

        return lead
