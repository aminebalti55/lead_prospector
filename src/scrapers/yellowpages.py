"""
YellowPages scraper implementation.

Scrapes business listings from YellowPages directory.
Uses sync Playwright API in a thread pool to avoid Windows asyncio issues.
Reference: docs/scraping/YELLOWPAGES.md
"""

import asyncio
import random
import re
import time
import logging
from typing import List, Optional
from urllib.parse import quote_plus, urlencode

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, BusinessLead
from .windows_compat import get_playwright_executor

logger = logging.getLogger(__name__)


class YellowPagesScraper(BaseScraper):
    """
    Scraper for YellowPages business listings.

    Difficulty: MEDIUM
    Rate limiting: 2-4s between requests, 200/hour
    """

    SOURCE_NAME = "yellowpages"
    BASE_URL = "https://www.yellowpages.com/search"

    async def search(
        self, business_type: str, city: str, state: str, max_results: int = 20
    ) -> List[BusinessLead]:
        """Search YellowPages for businesses."""
        location = f"{city}, {state}"
        logger.info(f"Searching YellowPages: {business_type} in {location}")

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
                    "search_terms": business_type,
                    "geo_location_terms": location,
                    "page": page_num,
                }
                url = f"{self.BASE_URL}?{urlencode(params)}"

                self.rate_limiter.wait_sync(self.SOURCE_NAME)
                self.rate_limiter.record_request(self.SOURCE_NAME)
                
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

                try:
                    selectors = [".search-results", ".organic", "div.result", "article.result"]
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

                    time.sleep(random.uniform(0.5, 1.5))

                    page_text = page.inner_text("body")
                    if len(page_text.strip()) < 200:
                        logger.warning("YellowPages page appears empty or blocked")
                        break

                except PlaywrightTimeout:
                    logger.warning("YellowPages search timed out")
                    break

                # Extract using JavaScript
                extracted_data = page.evaluate("""() => {
                    const results = [];
                    const bizLinks = document.querySelectorAll('a.business-name, a[href*="/mip/"]');
                    const seen = new Set();
                    
                    for (const link of bizLinks) {
                        const name = link.innerText.trim();
                        const href = link.getAttribute('href');
                        
                        if (!name || name.length < 2 || seen.has(href)) continue;
                        seen.add(href);
                        
                        let container = link.parentElement;
                        let attempts = 0;
                        while (container && container.innerText.length < 100 && attempts < 10) {
                            container = container.parentElement;
                            attempts++;
                        }
                        
                        const containerText = container ? container.innerText : '';
                        if (containerText.trim().startsWith('Ad')) continue;
                        
                        const phoneMatch = containerText.match(/\\(\\d{3}\\)\\s*\\d{3}-\\d{4}/);
                        
                        let address = null;
                        const lines = containerText.split('\\n');
                        for (const line of lines) {
                            const trimmed = line.trim();
                            if (/^\\d+\\s+\\w+/.test(trimmed) && trimmed.length < 100) {
                                address = trimmed;
                                break;
                            }
                        }
                        
                        // Extract website if available
                        const websiteLink = container ? container.querySelector('a.track-visit-website') : null;
                        const website = websiteLink ? websiteLink.getAttribute('href') : null;
                        
                        results.push({
                            name: name,
                            href: href ? (href.startsWith('/') ? 'https://www.yellowpages.com' + href : href) : null,
                            phone: phoneMatch ? phoneMatch[0] : null,
                            address: address,
                            website: website
                        });
                    }
                    return results;
                }""")

                page_leads = []
                if extracted_data:
                    for data in extracted_data:
                        if data.get("name"):
                            lead = BusinessLead(
                                source=self.SOURCE_NAME,
                                name=data["name"].strip(),
                                phone=self.clean_phone(data.get("phone")),
                                address=data.get("address"),
                                website=data.get("website"),
                                city=city,
                                state=state,
                                detail_url=data.get("href"),
                                is_sponsored=False,
                            )
                            page_leads.append(lead)

                if not page_leads:
                    break

                leads.extend(page_leads)
                page_num += 1

                if len(leads) >= max_results:
                    leads = leads[:max_results]
                    break

            logger.info(f"Found {len(leads)} leads from YellowPages")

        except Exception as e:
            logger.error(f"YellowPages search failed: {e}")
        finally:
            page.close()

        return leads

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Get detailed information from YellowPages business page."""
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
            time.sleep(random.uniform(1.0, 2.0))

            if not lead.phone:
                phone_el = page.query_selector(".phone")
                if phone_el:
                    lead.phone = self.clean_phone(phone_el.inner_text())

            if not lead.website:
                website_el = page.query_selector("a.website-link")
                if website_el:
                    lead.website = website_el.get_attribute("href")

            address_el = page.query_selector(".address")
            if address_el:
                lead.address = address_el.inner_text()

            claimed_el = page.query_selector(".claimed-label")
            lead.is_claimed = claimed_el is not None

            page_text = page.inner_text("body")
            years_match = re.search(r"(\d+)\s*years?\s*in\s*business", page_text, re.IGNORECASE)
            if years_match:
                lead.extra_data["years_in_business"] = int(years_match.group(1))

            bbb_match = re.search(r"BBB Rating:\s*([A-F][+-]?)", page_text)
            if bbb_match:
                lead.extra_data["bbb_rating"] = bbb_match.group(1)

            logger.debug(f"Got YellowPages details for: {lead.name}")

        except Exception as e:
            logger.warning(f"Failed to get YellowPages details for {lead.name}: {e}")
        finally:
            page.close()

        return lead
