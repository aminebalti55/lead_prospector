"""
Email Extractor Module
Extracts email addresses from multiple sources with validation and fallbacks.

Sources (in priority order):
1. Scraper detail pages (Google Maps, Yelp, YellowPages, BBB, Manta)
2. Business website (contact page, about page, footer)
3. Google search fallback
4. Domain-based email guessing (last resort)

ENHANCED VERSION with:
- Playwright + Stealth for JavaScript rendering and bot evasion
- User-Agent rotation with realistic browser signatures
- Retry logic with exponential backoff
- Fallback chain: httpx -> playwright stealth
- Uses sync Playwright API in thread pool for Windows compatibility
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

from .windows_compat import get_playwright_executor

# Playwright imports (optional - graceful fallback if not installed)
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    from playwright_stealth import Stealth

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    PlaywrightTimeout = Exception

logger = logging.getLogger(__name__)


# Realistic User-Agent rotation pool (2024/2025 browsers)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]


# Realistic browser headers
def get_random_headers() -> dict:
    """Get randomized headers that mimic a real browser."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


# Email regex pattern
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.IGNORECASE
)

# Domains to skip (not real business emails)
SKIP_DOMAINS = {
    # Placeholder/example domains
    "example.com",
    "example.org",
    "example.net",
    "email.com",
    "domain.com",
    "yoursite.com",
    "yourdomain.com",
    "yourcompany.com",
    "company.com",
    "placeholder.com",
    "test.com",
    "sample.com",
    # Website builder/platform domains
    "wixpress.com",
    "wix.com",
    "squarespace.com",
    "weebly.com",
    "godaddy.com",
    "wordpress.com",
    "wordpress.org",
    "shopify.com",
    "webflow.io",
    # Tech/tracking domains
    "sentry.io",
    "sentry-next.wixpress.com",
    "w3.org",
    "schema.org",
    "google.com",
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "pinterest.com",
    # Image/asset domains
    "gravatar.com",
    "githubusercontent.com",
    "cloudinary.com",
    "imgix.net",
    # Protection/privacy domains
    "privacyguard.com",
    "domainsbyproxy.com",
    "whoisguard.com",
    "contactprivacy.com",
}

# Common contact page paths to check
CONTACT_PAGES = [
    "/contact",
    "/contact-us",
    "/contactus",
    "/about/contact",
    "/about",
    "/about-us",
    "/aboutus",
    "/get-in-touch",
    "/reach-us",
    "/connect",
    "/support",
    "/help",
]

# Common email prefixes for guessing
COMMON_EMAIL_PREFIXES = [
    "info",
    "contact",
    "hello",
    "support",
    "sales",
    "service",
    "office",
    "admin",
    "help",
    "inquiries",
]

# Rate limits for email extraction
EMAIL_RATE_LIMITS = {
    "website": {"min_delay": 1.5, "max_delay": 3.0, "hourly_cap": 200},
    "google_search": {"min_delay": 5, "max_delay": 10, "hourly_cap": 50},
}


@dataclass
class EmailResult:
    """Result of email extraction for a single business."""

    email: Optional[str] = None
    source: Optional[str] = None  # scraper, website, google_search, guessed
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
    Extracts and validates email addresses from multiple sources.

    ENHANCED with:
    - User-Agent rotation
    - Playwright + Stealth fallback for bot-protected sites
    - Retry logic with exponential backoff
    - Better error handling for 403s and timeouts
    - Uses sync Playwright API in thread pool for Windows compatibility

    Usage:
        async with EmailExtractor() as extractor:
            result = await extractor.extract_email(
                website_url="https://example-plumber.com",
                business_name="Example Plumbing",
                city="Miami",
                state="FL"
            )
    """

    def __init__(
        self, timeout: float = 15.0, max_retries: int = 3, use_playwright: bool = True
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self.client: Optional[httpx.AsyncClient] = None
        self._seen_emails: Set[str] = set()

        if self.use_playwright:
            logger.info("Playwright stealth enabled for bot evasion")
        else:
            if not PLAYWRIGHT_AVAILABLE:
                logger.warning(
                    "Playwright not installed. Run: pip install playwright playwright-stealth && playwright install chromium"
                )

    async def __aenter__(self):
        # Create httpx client with rotating user-agent
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=get_random_headers(),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

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

        Args:
            website_url: Business website URL
            business_name: Name of the business
            city: City location
            state: State location
            existing_emails: Emails already found by scrapers

        Returns:
            EmailResult with best email and metadata
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
                result.extraction_notes = (
                    f"Found {len(valid_emails)} email(s) from scraper"
                )
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
            # Sort by confidence (high > medium > low)
            confidence_order = {"high": 0, "medium": 1, "low": 2}
            all_found.sort(key=lambda x: confidence_order.get(x[2], 3))

            best_email, best_source, best_confidence = all_found[0]
            result.email = best_email
            result.source = best_source
            result.confidence = best_confidence
            result.all_emails_found = list(set(e[0] for e in all_found))
            result.extraction_notes = (
                f"Found {len(all_found)} email(s), best from {best_source}"
            )
        else:
            result.extraction_notes = "No email found from any source"

        return result

    async def extract_from_website(self, url: str) -> List[str]:
        """
        Extract emails from a business website.

        Checks:
        1. Homepage
        2. Contact page
        3. About page

        Returns:
            List of valid email addresses found
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

        # Pages to check
        pages_to_check = [url]  # Homepage first
        for contact_path in CONTACT_PAGES[:5]:  # Limit to 5 contact pages
            pages_to_check.append(urljoin(base_url, contact_path))

        # Remove duplicates while preserving order
        pages_to_check = list(dict.fromkeys(pages_to_check))

        for page_url in pages_to_check:
            try:
                emails = await self._extract_emails_from_page(page_url)
                found_emails.update(emails)

                # If we found emails, we can stop
                if found_emails:
                    break

                # Rate limiting between pages
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.debug(f"Failed to extract from {page_url}: {e}")
                continue

        return list(found_emails)

    async def _extract_emails_from_page(self, url: str) -> Set[str]:
        """Extract emails from a single page using fallback chain."""
        emails: Set[str] = set()

        # Strategy 1: Try httpx with rotating headers
        html = await self._fetch_with_httpx(url)

        # Strategy 2: If httpx fails (403, timeout, etc.), try Playwright stealth
        if html is None and self.use_playwright:
            logger.debug(f"httpx failed for {url}, trying Playwright stealth...")
            html = await self._fetch_with_playwright(url)

        if html is None:
            return emails

        # Parse the HTML and extract emails
        emails = self._parse_emails_from_html(html)
        return emails

    async def _fetch_with_httpx(self, url: str) -> Optional[str]:
        """Fetch page with httpx and retry logic."""
        for attempt in range(self.max_retries):
            try:
                if not self.client:
                    raise RuntimeError("Client not initialized")

                # Rotate headers on each attempt
                self.client.headers.update(get_random_headers())

                response = await self.client.get(url)

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 403:
                    logger.debug(f"403 Forbidden for {url} (attempt {attempt + 1})")
                    # Don't retry 403s with httpx - go straight to Playwright
                    return None
                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    delay = (2**attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.debug(f"Status {response.status_code} for {url}")
                    return None

            except httpx.TimeoutException:
                logger.debug(f"Timeout for {url} (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
            except httpx.ConnectError as e:
                logger.debug(f"Connection error for {url}: {e}")
                return None
            except Exception as e:
                logger.debug(f"Error fetching {url}: {e}")
                return None

        return None

    async def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """
        Fetch page with Playwright + Stealth for bot-protected sites.
        
        Uses sync API in thread pool for Windows compatibility.
        """
        if not PLAYWRIGHT_AVAILABLE:
            return None

        def _fetch_sync():
            """Synchronous Playwright fetch that runs in thread pool."""
            import sys
            import asyncio as aio
            
            try:
                # CRITICAL: Set ProactorEventLoop policy in this thread
                # sync_playwright creates an internal event loop that needs subprocess support
                if sys.platform == "win32":
                    aio.set_event_loop_policy(aio.WindowsProactorEventLoopPolicy())
                
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(
                        headless=True,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--disable-dev-shm-usage",
                            "--no-sandbox",
                        ],
                    )
                    try:
                        context = browser.new_context(
                            viewport={"width": 1920, "height": 1080},
                            user_agent=random.choice(USER_AGENTS),
                            locale="en-US",
                        )
                        
                        page = context.new_page()
                        
                        # Add stealth script
                        page.add_init_script("""
                            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                        """)
                        
                        # Navigate with timeout
                        page.goto(
                            url, 
                            timeout=int(self.timeout * 1000), 
                            wait_until="domcontentloaded"
                        )
                        
                        # Wait a bit for any JS to render
                        time.sleep(1)
                        
                        # Get page content
                        content = page.content()
                        
                        context.close()
                        logger.debug(f"Playwright successfully fetched {url}")
                        return content
                        
                    finally:
                        browser.close()
                        
            except Exception as e:
                logger.debug(f"Playwright error for {url}: {e}")
                return None

        # Run sync Playwright in thread pool
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        return await loop.run_in_executor(executor, _fetch_sync)

    def _parse_emails_from_html(self, html: str) -> Set[str]:
        """Parse emails from HTML content."""
        emails: Set[str] = set()

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Method 1: Find mailto: links
            mailto_links = soup.find_all("a", href=re.compile(r"^mailto:", re.I))
            for link in mailto_links:
                href_val = link.get("href")
                href = str(href_val) if href_val else ""
                email = href.replace("mailto:", "").split("?")[0].strip()
                if self.validate_email(email):
                    emails.add(email.lower())

            # Method 2: Regex search in text content
            text = soup.get_text()
            regex_emails = EMAIL_PATTERN.findall(text)
            for email in regex_emails:
                if self.validate_email(email):
                    emails.add(email.lower())

            # Method 3: Check for obfuscated emails
            # Look for patterns like: info [at] domain [dot] com
            obfuscated = self._find_obfuscated_emails(text)
            for email in obfuscated:
                if self.validate_email(email):
                    emails.add(email.lower())

            # Method 4: Check raw HTML for emails (sometimes hidden in attributes)
            raw_emails = EMAIL_PATTERN.findall(html)
            for email in raw_emails:
                if self.validate_email(email):
                    emails.add(email.lower())

        except Exception as e:
            logger.debug(f"Error parsing HTML: {e}")

        return emails

    def _find_obfuscated_emails(self, text: str) -> List[str]:
        """Find obfuscated email patterns like 'info [at] domain [dot] com'."""
        emails = []

        # Pattern: word [at] or (at) or {at} domain [dot] or (dot) or {dot} tld
        patterns = [
            r"(\w+[\w.+-]*)\s*[\[\(\{]at[\]\)\}]\s*(\w+[\w.-]*)\s*[\[\(\{]dot[\]\)\}]\s*(\w+)",
            r"(\w+[\w.+-]*)\s*@\s*(\w+[\w.-]*)\s*[\[\(\{]dot[\]\)\}]\s*(\w+)",
        ]

        text_lower = text.lower()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if len(match) == 3:
                    email = f"{match[0]}@{match[1]}.{match[2]}"
                    emails.append(email)

        return emails

    def validate_email(self, email: str) -> bool:
        """
        Validate an email address.

        Checks:
        1. Valid format
        2. Not a skip domain
        3. Not a generic/fake pattern
        4. Not a file path (image, JS, etc.)
        """
        if not email:
            return False

        email = email.lower().strip()

        # Check format
        if not EMAIL_PATTERN.match(email):
            return False

        # Skip file extensions (false positives from image/asset filenames)
        file_extensions = [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".webp",
            ".ico",
            ".js",
            ".css",
            ".html",
            ".pdf",
            ".doc",
            ".docx",
            ".xml",
        ]
        if any(email.endswith(ext) for ext in file_extensions):
            return False

        # Skip if it looks like a file path (contains @ followed by size indicators)
        if re.search(r"@\d+x\.", email):
            return False

        # Extract domain
        try:
            domain = email.split("@")[1]
        except IndexError:
            return False

        # Domain must have at least one dot and valid TLD
        if "." not in domain:
            return False

        # TLD must be at least 2 chars and only letters
        tld = domain.split(".")[-1]
        if len(tld) < 2 or not tld.isalpha():
            return False

        # Check skip domains
        for skip_domain in SKIP_DOMAINS:
            if domain == skip_domain or domain.endswith(f".{skip_domain}"):
                return False

        # Check for fake patterns
        fake_patterns = [
            "your",
            "email",
            "name",
            "user",
            "test",
            "demo",
            "sample",
            "fake",
            "example",
        ]
        local_part = email.split("@")[0]
        if any(pattern in local_part for pattern in fake_patterns):
            # Only skip if it looks truly fake
            if local_part in fake_patterns or local_part.startswith(
                tuple(fake_patterns)
            ):
                return False

        return True

    def guess_email_from_domain(self, website_url: str) -> List[str]:
        """
        Guess likely email addresses from a domain.

        Returns list of guessed emails (low confidence).
        """
        guessed = []

        # Parse domain
        if not website_url.startswith(("http://", "https://")):
            website_url = f"https://{website_url}"

        try:
            parsed = urlparse(website_url)
            domain = parsed.netloc

            # Remove www prefix
            if domain.startswith("www."):
                domain = domain[4:]

            # Skip invalid domains
            if not domain or "." not in domain:
                return guessed

            # Skip known platform domains
            for skip in SKIP_DOMAINS:
                if skip in domain:
                    return guessed

            # Generate guesses
            for prefix in COMMON_EMAIL_PREFIXES[:3]:  # Top 3 prefixes only
                guessed.append(f"{prefix}@{domain}")

        except Exception as e:
            logger.debug(f"Error guessing email from {website_url}: {e}")

        return guessed

    @staticmethod
    def extract_email_from_mailto(href: str) -> Optional[str]:
        """Extract email from a mailto: href."""
        if not href:
            return None

        if href.lower().startswith("mailto:"):
            email = href[7:].split("?")[0].strip()
            return email if email else None

        return None

    @staticmethod
    def clean_email(email: str) -> str:
        """Clean and normalize an email address."""
        if not email:
            return ""

        # Remove whitespace and lowercase
        email = email.strip().lower()

        # Remove common prefixes accidentally included
        for prefix in ["email:", "e-mail:", "mail:"]:
            if email.startswith(prefix):
                email = email[len(prefix) :].strip()

        return email


async def extract_emails_for_leads(
    leads: list,
    extractor: Optional[EmailExtractor] = None,
    max_concurrent: int = 5,
) -> list:
    """
    Extract emails for a list of leads.

    Args:
        leads: List of BusinessLead or ProcessedLead objects
        extractor: EmailExtractor instance (will create one if not provided)
        max_concurrent: Max concurrent extractions

    Returns:
        List of leads with email fields populated
    """

    async def extract_for_lead(lead, extractor):
        """Extract email for a single lead."""
        try:
            # Get existing emails if any
            existing = []
            if hasattr(lead, "extra_data") and lead.extra_data:
                if "email" in lead.extra_data:
                    existing.append(lead.extra_data["email"])

            # Extract
            result = await extractor.extract_email(
                website_url=getattr(lead, "website", None),
                business_name=getattr(lead, "name", None),
                city=getattr(lead, "city", None),
                state=getattr(lead, "state", None),
                existing_emails=existing,
            )

            # Update lead
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
            logger.warning(
                f"Failed to extract email for {getattr(lead, 'name', 'unknown')}: {e}"
            )
            return lead

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_extract(lead, extractor):
        async with semaphore:
            return await extract_for_lead(lead, extractor)

    # Process leads
    own_extractor = extractor is None
    if own_extractor:
        extractor = EmailExtractor()

    try:
        async with extractor:
            tasks = [bounded_extract(lead, extractor) for lead in leads]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
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


# Convenience function for testing
async def test_email_extractor():
    """Test the email extractor."""
    async with EmailExtractor() as extractor:
        # Test with a sample website
        result = await extractor.extract_email(
            website_url="https://www.example.com",
            business_name="Example Business",
            city="Miami",
            state="FL",
        )
        print(f"Email: {result.email}")
        print(f"Source: {result.source}")
        print(f"Confidence: {result.confidence}")
        print(f"All found: {result.all_emails_found}")
        print(f"Notes: {result.extraction_notes}")


if __name__ == "__main__":
    asyncio.run(test_email_extractor())
