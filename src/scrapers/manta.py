"""
Manta scraper implementation.

Scrapes business listings from Manta business directory.
Uses sync Playwright API in a thread pool to avoid Windows asyncio issues.
Reference: docs/scraping/MANTA.md
"""

import asyncio
import random
import re
import time
import logging
from typing import List, Optional
from urllib.parse import quote_plus, urlencode, urlparse, parse_qs, unquote
from datetime import datetime

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, BusinessLead
from .windows_compat import get_playwright_executor

logger = logging.getLogger(__name__)


class MantaScraper(BaseScraper):
    """
    Scraper for Manta business directory listings.

    Difficulty: MEDIUM
    Rate limiting: 3-6s between searches, 100/hour
    """

    SOURCE_NAME = "manta"
    BASE_URL = "https://www.manta.com/search"

    async def search(
        self, business_type: str, city: str, state: str, max_results: int = 20
    ) -> List[BusinessLead]:
        """Search Manta for businesses."""
        logger.info(f"Searching Manta: {business_type} in {city}, {state}")

        def _do_search(context):
            return self._search_sync(context, business_type, city, state, max_results)
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        return await loop.run_in_executor(
            executor,
            lambda: _do_search(self._context)
        )

    def _search_sync(
        self, context, business_type: str, city: str, state: str, max_results: int
    ) -> List[BusinessLead]:
        """Synchronous search implementation (runs in thread pool)."""
        leads: List[BusinessLead] = []
        page_num = 1
        page = context.new_page()

        try:
            # Visit homepage first to establish session
            page.goto("https://www.manta.com", wait_until="domcontentloaded", timeout=15000)
            time.sleep(random.uniform(1.0, 2.0))

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

                self.rate_limiter.wait_sync(self.SOURCE_NAME)
                self.rate_limiter.record_request(self.SOURCE_NAME)
                
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

                try:
                    selectors = ['a[href^="/c/"]', ".company-name"]
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

                    time.sleep(random.uniform(2.0, 3.0))

                    page_text = page.inner_text("body")
                    if len(page_text.strip()) < 200:
                        logger.warning("Manta page appears empty or blocked")
                        break

                except PlaywrightTimeout:
                    logger.warning("Manta content didn't render")
                    break

                # Extract using JavaScript
                extracted_data = page.evaluate("""() => {
                    const results = [];
                    const seen = new Set();
                    const links = document.querySelectorAll('a[href^="/c/"]:not([href*="category"])');
                    
                    for (const link of links) {
                        const href = link.getAttribute('href');
                        const name = link.innerText.trim();
                        
                        if (!name || name.length < 2 || seen.has(href)) continue;
                        seen.add(href);
                        
                        let card = link.parentElement;
                        let attempts = 0;
                        while (card && card.innerText.length < 50 && attempts < 10) {
                            card = card.parentElement;
                            attempts++;
                        }
                        
                        const cardText = card ? card.innerText : '';
                        const phoneMatch = cardText.match(/\\(\\d{3}\\)\\s*\\d{3}-\\d{4}/);
                        const isClaimed = cardText.includes('CLAIMED');
                        const isPromoted = cardText.includes('★') || cardText.includes('Promoted');
                        
                        let address = null;
                        const lines = cardText.split('\\n');
                        for (const line of lines) {
                            const trimmed = line.trim();
                            if (/^\\d+\\s+\\w+/.test(trimmed) && trimmed.length < 100) {
                                address = trimmed;
                                break;
                            }
                        }
                        
                        const empMatch = cardText.match(/(\\d+)\\s*employees?/i);
                        const yearsMatch = cardText.match(/(\\d+)\\s*years?\\s*in\\s*business/i);
                        
                        results.push({
                            name: name,
                            href: href,
                            phone: phoneMatch ? phoneMatch[0] : null,
                            address: address,
                            is_claimed: isClaimed,
                            is_promoted: isPromoted,
                            employee_count: empMatch ? parseInt(empMatch[1]) : null,
                            years_in_business: yearsMatch ? parseInt(yearsMatch[1]) : null
                        });
                    }
                    
                    return results;
                }""")

                page_leads = []
                if extracted_data:
                    for data in extracted_data:
                        if data.get("is_promoted"):
                            continue

                        name = data.get("name", "").strip()
                        href = data.get("href", "")

                        if not name or not href:
                            continue

                        detail_url = f"https://www.manta.com{href}" if href.startswith("/") else href

                        extra_data = {}
                        if data.get("employee_count"):
                            extra_data["employee_count"] = data["employee_count"]
                        if data.get("years_in_business"):
                            extra_data["years_in_business"] = data["years_in_business"]

                        lead = BusinessLead(
                            source=self.SOURCE_NAME,
                            name=name,
                            phone=self.clean_phone(data.get("phone")),
                            address=data.get("address"),
                            city=city,
                            state=state,
                            is_claimed=data.get("is_claimed", False),
                            is_sponsored=False,
                            detail_url=detail_url,
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

            logger.info(f"Found {len(leads)} leads from Manta")

        except Exception as e:
            logger.error(f"Manta search failed: {e}")
        finally:
            page.close()

        return leads

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

            page_text = page.inner_text("body")

            if not lead.phone:
                phone_el = page.query_selector('a[href^="tel:"]')
                if phone_el:
                    lead.phone = self.clean_phone(phone_el.inner_text())

            if not lead.website:
                website_el = page.query_selector('a[href*="/urlverify"]')
                if website_el:
                    href = website_el.get_attribute("href")
                    lead.website = self._unwrap_redirect_url(href)

            address_el = page.query_selector('[data-testid="business-address"], .address')
            if address_el:
                lead.address = address_el.inner_text()

            sic_match = re.search(r"SIC\s*(?:Code)?:\s*(\d+)", page_text)
            if sic_match:
                lead.extra_data["sic_code"] = sic_match.group(1)

            contact_match = re.search(r"Contact(?:\s*Name)?:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)", page_text)
            if contact_match:
                lead.extra_data["contact_name"] = contact_match.group(1)

            emp_match = re.search(r"Employees?:\s*(\d+)", page_text)
            if emp_match:
                lead.extra_data["employee_count"] = int(emp_match.group(1))

            date_match = re.search(r"(?:Founded|Opened|Started):\s*(\d{4})", page_text)
            if date_match:
                start_year = int(date_match.group(1))
                lead.extra_data["year_started"] = start_year
                lead.extra_data["years_in_business"] = datetime.now().year - start_year

            logger.debug(f"Got Manta details for: {lead.name}")

        except Exception as e:
            logger.warning(f"Failed to get Manta details for {lead.name}: {e}")
        finally:
            page.close()

        return lead
