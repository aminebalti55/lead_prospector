"""
Yelp scraper implementation.

Scrapes business listings from Yelp search results.
Uses sync Playwright API in a thread pool to avoid Windows asyncio issues.
Reference: docs/scraping/YELP.md
"""

import asyncio
import random
import re
import time
import logging
from typing import List, Optional
from urllib.parse import quote_plus, urlencode, urlparse, parse_qs

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, BusinessLead
from .windows_compat import get_playwright_executor

logger = logging.getLogger(__name__)


class YelpScraper(BaseScraper):
    """
    Scraper for Yelp business listings.

    Difficulty: MEDIUM-HIGH
    Rate limiting: 3-5s between requests, 150/hour
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
        start = 0
        page = context.new_page()

        try:
            # Add stealth scripts
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            """)

            while len(leads) < max_results:
                params = {
                    "find_desc": business_type,
                    "find_loc": location,
                    "start": start,
                }
                url = f"{self.BASE_URL}?{urlencode(params)}"

                self.rate_limiter.wait_sync(self.SOURCE_NAME)
                self.rate_limiter.record_request(self.SOURCE_NAME)
                
                page.goto(url, wait_until="domcontentloaded", timeout=60000)

                try:
                    selectors = ["main", '[data-testid="serp-ia-card"]', 'a[href*="/biz/"]']
                    found = False
                    for selector in selectors:
                        try:
                            page.wait_for_selector(selector, timeout=10000)
                            found = True
                            break
                        except PlaywrightTimeout:
                            continue

                    if not found:
                        page.wait_for_load_state("networkidle", timeout=20000)

                    time.sleep(random.uniform(2.5, 4.0))

                    # Check for device verification
                    verification = page.query_selector("text=Device verification")
                    if verification:
                        logger.info("Yelp device verification detected, waiting...")
                        time.sleep(10.0)

                    page_text = page.inner_text("body")
                    if len(page_text.strip()) < 100:
                        logger.warning("Yelp appears to be blocking")
                        break

                except PlaywrightTimeout:
                    logger.warning("Yelp search timed out")
                    break

                # Extract using JavaScript
                extracted_data = page.evaluate("""() => {
                    const results = [];
                    const seen = new Set();
                    const bizLinks = document.querySelectorAll('a[href*="/biz/"]');
                    
                    for (const link of bizLinks) {
                        const href = link.getAttribute('href');
                        const name = link.innerText.trim();
                        
                        if (!name || name.length < 2 || seen.has(href)) continue;
                        if (href.includes('/adredir') || href.includes('/aclk')) continue;
                        seen.add(href);
                        
                        let container = link.parentElement;
                        let attempts = 0;
                        while (container && container.innerText.length < 100 && attempts < 15) {
                            container = container.parentElement;
                            attempts++;
                        }
                        
                        const containerText = container ? container.innerText : '';
                        if (containerText.includes('Sponsored') || containerText.split('\\n')[0].includes('Ad')) {
                            continue;
                        }
                        
                        const ratingMatch = containerText.match(/(\\d+\\.?\\d*)\\s*star/i);
                        const reviewMatch = containerText.match(/\\((\\d+)\\s*reviews?\\)/i);
                        const phoneMatch = containerText.match(/\\(\\d{3}\\)\\s*\\d{3}-\\d{4}/);
                        
                        results.push({
                            name: name,
                            href: href.startsWith('/') ? 'https://www.yelp.com' + href : href,
                            rating: ratingMatch ? parseFloat(ratingMatch[1]) : null,
                            review_count: reviewMatch ? parseInt(reviewMatch[1]) : null,
                            phone: phoneMatch ? phoneMatch[0] : null
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
                                city=city,
                                state=state,
                                rating=data.get("rating"),
                                review_count=data.get("review_count"),
                                detail_url=data.get("href"),
                                is_sponsored=False,
                            )
                            page_leads.append(lead)

                if not page_leads:
                    break

                leads.extend(page_leads)
                start += 10

                if len(leads) >= max_results:
                    leads = leads[:max_results]
                    break

            logger.info(f"Found {len(leads)} leads from Yelp")

        except Exception as e:
            logger.error(f"Yelp search failed: {e}")
        finally:
            page.close()

        return leads

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Get detailed information from Yelp business page."""
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

            phone_link = page.query_selector('a[href^="tel:"]')
            if phone_link:
                phone_text = phone_link.inner_text()
                lead.phone = self.clean_phone(phone_text)

            website_link = page.query_selector('a[href*="biz_redir"]')
            if website_link:
                href = website_link.get_attribute("href")
                if href:
                    lead.website = self._unwrap_redirect_url(href)

            address_el = page.query_selector("address")
            if address_el:
                lead.address = address_el.inner_text()

            claimed_el = page.query_selector('span:has-text("Claimed")')
            lead.is_claimed = claimed_el is not None

            page_text = page.inner_text("body")
            years_match = re.search(r"(\d+)\s*years?\s*in\s*business", page_text, re.IGNORECASE)
            if years_match:
                lead.extra_data["years_in_business"] = int(years_match.group(1))

            logger.debug(f"Got Yelp details for: {lead.name}")

        except Exception as e:
            logger.warning(f"Failed to get Yelp details for {lead.name}: {e}")
        finally:
            page.close()

        return lead

    def _unwrap_redirect_url(self, url: str) -> str:
        """Unwrap Yelp's biz_redir redirect URLs."""
        if "biz_redir" in url:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if "url" in query_params:
                return query_params["url"][0]
        return url
