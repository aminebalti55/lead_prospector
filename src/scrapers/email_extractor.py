"""
Email Extractor Module using undetected-chromedriver.

Extracts email addresses from business websites with anti-bot evasion.
Uses Selenium with undetected-chromedriver for reliable extraction.

Sources (in priority order):
1. Scraper detail pages (existing emails from scrapers)
2. Business website (contact page, about page, footer)
3. Domain-based email guessing (last resort)
"""

import asyncio
import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import Optional, List, Set, Tuple
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

from .browser_manager import (
    BrowserSession,
    get_browser_executor,
    safe_get,
    USER_AGENTS,
)

logger = logging.getLogger(__name__)


# Email regex pattern
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.IGNORECASE
)

# Domains to skip (not real business emails)
SKIP_DOMAINS = {
    # Placeholder/example domains
    "example.com", "example.org", "example.net",
    "email.com", "domain.com", "yoursite.com",
    "yourdomain.com", "yourcompany.com", "company.com",
    "placeholder.com", "test.com", "sample.com",
    # Website builder/platform domains
    "wixpress.com", "wix.com", "squarespace.com",
    "weebly.com", "godaddy.com", "wordpress.com",
    "wordpress.org", "shopify.com", "webflow.io",
    # Tech/tracking domains
    "sentry.io", "w3.org", "schema.org",
    "google.com", "facebook.com", "twitter.com",
    "instagram.com", "linkedin.com", "youtube.com", "pinterest.com",
    # Image/asset domains
    "gravatar.com", "githubusercontent.com",
    "cloudinary.com", "imgix.net",
    # Protection/privacy domains
    "privacyguard.com", "domainsbyproxy.com",
    "whoisguard.com", "contactprivacy.com",
}

# Common contact page paths to check (ordered by likelihood)
CONTACT_PAGES = [
    "/contact",
    "/contact-us",
    "/contactus",
    "/contact.html",
    "/contact.php",
    "/about/contact",
    "/about",
    "/about-us",
    "/aboutus",
    "/about.html",
    "/get-in-touch",
    "/reach-us",
    "/connect",
    "/support",
    "/help",
    "/info",
    "/location",
    "/locations",
    "/our-team",
    "/team",
    "/staff",
]

# Common email prefixes for guessing
COMMON_EMAIL_PREFIXES = [
    "info", "contact", "hello", "support",
    "sales", "service", "office", "admin",
    "help", "inquiries",
]


def get_random_headers() -> dict:
    """Get randomized headers that mimic a real browser."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


@dataclass
class EmailResult:
    """Result of email extraction for a single business."""

    email: Optional[str] = None
    source: Optional[str] = None  # scraper, website, guessed
    confidence: str = "none"  # high, medium, low, none
    all_emails_found: List[str] = field(default_factory=list)
    extraction_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "email": self.email,
            "email_source": self.source,
            "email_confidence": self.confidence,
            "all_emails_found": ", ".join(self.all_emails_found),
            "extraction_notes": self.extraction_notes,
        }


class EmailExtractor:
    """
    Extracts and validates email addresses from business websites.

    Uses a multi-strategy approach:
    1. Try HTTP request first (fast)
    2. Fall back to browser for JavaScript-heavy sites
    
    Usage:
        async with EmailExtractor() as extractor:
            result = await extractor.extract_email(
                website_url="https://example-plumber.com",
                business_name="Example Plumbing",
            )
    """

    def __init__(self, timeout: float = 8.0, max_retries: int = 1, use_browser: bool = True):
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_browser = use_browser
        self.client: Optional[httpx.AsyncClient] = None
        self._session: Optional[BrowserSession] = None
        self._seen_emails: Set[str] = set()

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=get_random_headers(),
            follow_redirects=True,
        )
        if self.use_browser:
            self._session = BrowserSession(headless=True)
            await self._session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
        if self._session:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)

    async def extract_email(
        self,
        website_url: str = "",
        business_name: str = "",
        city: str = "",
        state: str = "",
        existing_emails: Optional[List[str]] = None,
    ) -> EmailResult:
        """
        Extract email for a business using multiple sources.

        Priority:
        1. Use existing emails if provided (from scrapers)
        2. Scrape business website
        3. Guess from domain (last resort)
        """
        result = EmailResult()
        all_found: List[Tuple[str, str, str]] = []  # (email, source, confidence)

        # 1. Check existing emails from scrapers
        if existing_emails:
            valid_emails = [e for e in existing_emails if self.validate_email(e)]
            if valid_emails:
                result.email = valid_emails[0]
                result.source = "scraper"
                result.confidence = "high"
                result.all_emails_found = valid_emails
                result.extraction_notes = f"Found {len(valid_emails)} email(s) from scraper"
                return result

        # 2. Extract from website
        if website_url:
            website_emails = await self.extract_from_website(website_url)
            for email in website_emails:
                all_found.append((email, "website", "high"))

        # 3. Guess from domain (low confidence)
        if website_url and not all_found:
            guessed = self.guess_email_from_domain(website_url)
            for email in guessed:
                all_found.append((email, "guessed", "low"))

        # Select best email
        if all_found:
            confidence_order = {"high": 0, "medium": 1, "low": 2}
            all_found.sort(key=lambda x: confidence_order.get(x[2], 3))

            best_email, best_source, best_confidence = all_found[0]
            result.email = best_email
            result.source = best_source
            result.confidence = best_confidence
            result.all_emails_found = list(set(e[0] for e in all_found))
            result.extraction_notes = f"Found {len(all_found)} email(s), best from {best_source}"
        else:
            result.extraction_notes = "No email found from any source"

        return result

    async def extract_from_website(self, url: str) -> List[str]:
        """
        Extract emails from a business website.

        Checks homepage and key contact pages concurrently for speed.
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        found_emails: Set[str] = set()

        # Normalize URL
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Parse base URL
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Priority pages - only check the most common ones for speed
        priority_paths = ["/contact", "/contact-us", "/about", "/about-us"]
        pages_to_check = [url]  # Homepage first
        for contact_path in priority_paths:
            contact_url = urljoin(base_url, contact_path)
            if contact_url not in pages_to_check:
                pages_to_check.append(contact_url)

        # Check homepage + up to 4 contact pages concurrently (max 5 pages)
        pages_to_check = pages_to_check[:5]
        
        # Concurrent extraction for speed
        tasks = [self._extract_emails_from_page(page_url) for page_url in pages_to_check]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"Failed to extract from {pages_to_check[i]}: {result}")
            elif result:
                found_emails.update(result)
                if result:
                    logger.info(f"Found emails on {pages_to_check[i]}: {result}")
        
        # If still no emails and we have browser, try one more time with browser on contact page
        if not found_emails and self.use_browser and self._session:
            contact_url = urljoin(base_url, "/contact")
            try:
                html = await self._fetch_with_browser(contact_url)
                if html:
                    browser_emails = self._parse_emails_from_html(html)
                    found_emails.update(browser_emails)
            except Exception as e:
                logger.debug(f"Browser fallback failed for {contact_url}: {e}")
        
        return list(found_emails)

    async def _extract_emails_from_page(self, url: str) -> Set[str]:
        """Extract emails from a single page using HTTP only (fast)."""
        emails: Set[str] = set()

        # HTTP request only for speed - browser fallback handled at website level
        html = await self._fetch_with_httpx(url)
        
        if html:
            emails = self._parse_emails_from_html(html)

        return emails

    async def _fetch_with_httpx(self, url: str) -> Optional[str]:
        """Fetch page with HTTP request."""
        for attempt in range(self.max_retries):
            try:
                if not self.client:
                    return None

                self.client.headers.update(get_random_headers())
                response = await self.client.get(url)

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 403:
                    # Blocked - try browser instead
                    return None
                elif response.status_code >= 500:
                    await asyncio.sleep(1)
                    continue
                else:
                    return None

            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"HTTP error for {url}: {e}")
                return None

        return None

    async def _fetch_with_browser(self, url: str) -> Optional[str]:
        """Fetch page with browser (for JS-heavy sites)."""
        if not self._session:
            return None

        def _fetch(driver):
            if not safe_get(driver, url, wait_time=2.0):
                return None
            time.sleep(1)
            return driver.page_source

        try:
            return await self._session.run(_fetch)
        except Exception as e:
            logger.debug(f"Browser error for {url}: {e}")
            return None

    def _parse_emails_from_html(self, html: str) -> Set[str]:
        """Parse emails from HTML content."""
        emails: Set[str] = set()

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Method 1: Find mailto: links (most reliable)
            mailto_links = soup.find_all("a", href=re.compile(r"^mailto:", re.I))
            for link in mailto_links:
                href_val = link.get("href")
                href = str(href_val) if href_val else ""
                # Extract email, handling mailto:email?subject=... format
                email = href.replace("mailto:", "").split("?")[0].split("&")[0].strip()
                if self.validate_email(email):
                    emails.add(email.lower())
                    logger.debug(f"Found mailto email: {email}")

            # Method 2: Find emails in HTML attributes (href, data-*, etc.)
            attr_emails = self._find_emails_in_html_attrs(html)
            emails.update(attr_emails)

            # Method 3: Regex search in visible text
            text = soup.get_text(separator=" ")
            regex_emails = EMAIL_PATTERN.findall(text)
            for email in regex_emails:
                if self.validate_email(email):
                    emails.add(email.lower())

            # Method 4: Check for obfuscated emails in text
            obfuscated = self._find_obfuscated_emails(text)
            for email in obfuscated:
                if self.validate_email(email):
                    emails.add(email.lower())

            # Method 5: Check raw HTML for emails (catches JS-embedded emails)
            raw_emails = EMAIL_PATTERN.findall(html)
            for email in raw_emails:
                if self.validate_email(email):
                    emails.add(email.lower())
            
            # Method 6: Look for email-like patterns near "email" or "contact" keywords
            email_sections = soup.find_all(
                string=re.compile(r"email|e-mail|contact|reach", re.I)
            )
            for section in email_sections:
                parent = section.parent
                if parent:
                    # Get text from parent and siblings
                    parent_text = parent.get_text() if parent else ""
                    found = EMAIL_PATTERN.findall(parent_text)
                    for email in found:
                        if self.validate_email(email):
                            emails.add(email.lower())
                            logger.debug(f"Found email near keyword: {email}")

        except Exception as e:
            logger.debug(f"Error parsing HTML: {e}")

        return emails

    def _find_obfuscated_emails(self, text: str) -> List[str]:
        """Find obfuscated email patterns."""
        emails = []
        
        # Pattern 1: name [at] domain [dot] com
        patterns_3part = [
            r"(\w+[\w.+-]*)\s*[\[\(\{<]?\s*at\s*[\]\)\}>]?\s*(\w+[\w.-]*)\s*[\[\(\{<]?\s*dot\s*[\]\)\}>]?\s*(\w+)",
            r"(\w+[\w.+-]*)\s*@\s*(\w+[\w.-]*)\s*[\[\(\{<]?\s*dot\s*[\]\)\}>]?\s*(\w+)",
        ]
        
        # Pattern 2: [email protected] or \[email protected\] (escaped brackets)
        # This catches WordPress/website builder obfuscation
        patterns_direct = [
            r"\\?\[email[^\]]*\\?\]",  # [email protected] or \[email protected\]
            r"\[email\s*protected\]",  # [email protected]
        ]

        text_lower = text.lower()
        
        # Try 3-part patterns
        for pattern in patterns_3part:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if len(match) == 3:
                    email = f"{match[0]}@{match[1]}.{match[2]}"
                    emails.append(email)
        
        # For [email protected] patterns, we need to look at the raw HTML
        # These are often mailto: links with obfuscated display text
        # The actual email is usually in the href
        
        return emails
    
    def _find_emails_in_html_attrs(self, html: str) -> Set[str]:
        """Find emails hidden in HTML attributes (href, data-*, onclick, etc.)."""
        emails: Set[str] = set()
        
        # Look for mailto: in any attribute
        mailto_pattern = r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        matches = re.findall(mailto_pattern, html, re.IGNORECASE)
        for email in matches:
            if self.validate_email(email):
                emails.add(email.lower())
        
        # Look for emails in data attributes
        data_pattern = r'data-[^=]*=["\']([^"\']*@[^"\']*)["\']'
        matches = re.findall(data_pattern, html, re.IGNORECASE)
        for match in matches:
            found = EMAIL_PATTERN.findall(match)
            for email in found:
                if self.validate_email(email):
                    emails.add(email.lower())
        
        # Look for emails in onclick/javascript
        js_pattern = r'["\']([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']'
        matches = re.findall(js_pattern, html)
        for email in matches:
            if self.validate_email(email):
                emails.add(email.lower())
        
        return emails

    def validate_email(self, email: str) -> bool:
        """Validate an email address."""
        if not email:
            return False

        email = email.lower().strip()

        if not EMAIL_PATTERN.match(email):
            return False

        # Skip file extensions
        file_extensions = [
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
            ".js", ".css", ".html", ".pdf", ".doc", ".docx", ".xml",
        ]
        if any(email.endswith(ext) for ext in file_extensions):
            return False

        # Skip file paths
        if re.search(r"@\d+x\.", email):
            return False

        # Extract domain
        try:
            domain = email.split("@")[1]
        except IndexError:
            return False

        if "." not in domain:
            return False

        tld = domain.split(".")[-1]
        if len(tld) < 2 or not tld.isalpha():
            return False

        # Check skip domains
        for skip_domain in SKIP_DOMAINS:
            if domain == skip_domain or domain.endswith(f".{skip_domain}"):
                return False

        # Check for fake patterns
        fake_patterns = ["your", "email", "name", "user", "test", "demo", "sample", "fake", "example"]
        local_part = email.split("@")[0]
        if any(pattern in local_part for pattern in fake_patterns):
            if local_part in fake_patterns or local_part.startswith(tuple(fake_patterns)):
                return False

        return True

    def guess_email_from_domain(self, website_url: str) -> List[str]:
        """Guess likely email addresses from a domain."""
        guessed = []

        if not website_url.startswith(("http://", "https://")):
            website_url = f"https://{website_url}"

        try:
            parsed = urlparse(website_url)
            domain = parsed.netloc

            if domain.startswith("www."):
                domain = domain[4:]

            if not domain or "." not in domain:
                return guessed

            for skip in SKIP_DOMAINS:
                if skip in domain:
                    return guessed

            for prefix in COMMON_EMAIL_PREFIXES[:3]:
                guessed.append(f"{prefix}@{domain}")

        except Exception as e:
            logger.debug(f"Error guessing email from {website_url}: {e}")

        return guessed


async def extract_emails_for_leads(
    leads: list,
    extractor: Optional[EmailExtractor] = None,
    max_concurrent: int = 3,
) -> list:
    """
    Extract emails for a list of leads.

    Args:
        leads: List of BusinessLead objects
        extractor: EmailExtractor instance (will create one if not provided)
        max_concurrent: Max concurrent extractions

    Returns:
        List of leads with email fields populated
    """

    async def extract_for_lead(lead, extractor):
        """Extract email for a single lead."""
        try:
            existing = []
            if hasattr(lead, "extra_data") and lead.extra_data:
                if "email" in lead.extra_data:
                    existing.append(lead.extra_data["email"])

            result = await extractor.extract_email(
                website_url=getattr(lead, "website", None),
                business_name=getattr(lead, "name", None),
                city=getattr(lead, "city", None),
                state=getattr(lead, "state", None),
                existing_emails=existing,
            )

            if result.email:
                if hasattr(lead, "email"):
                    lead.email = result.email
                if hasattr(lead, "email_source"):
                    lead.email_source = result.source
                if hasattr(lead, "extra_data"):
                    lead.extra_data["email"] = result.email
                    lead.extra_data["email_source"] = result.source
                    lead.extra_data["email_confidence"] = result.confidence

            return lead

        except Exception as e:
            logger.warning(f"Failed to extract email for {getattr(lead, 'name', 'unknown')}: {e}")
            return lead

    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_extract(lead, extractor):
        async with semaphore:
            return await extract_for_lead(lead, extractor)

    own_extractor = extractor is None
    if own_extractor:
        extractor = EmailExtractor()

    try:
        async with extractor:
            tasks = [bounded_extract(lead, extractor) for lead in leads]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            processed_leads = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Exception for lead {i}: {result}")
                    processed_leads.append(leads[i])
                else:
                    processed_leads.append(result)

            return processed_leads

    except Exception as e:
        logger.error(f"Error in batch email extraction: {e}")
        return leads
