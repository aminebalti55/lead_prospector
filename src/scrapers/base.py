"""
Base classes and utilities for web scrapers.

This module provides the foundation for all scraper implementations:
- BusinessLead: Dataclass for standardized lead data
- RateLimiter: Per-source rate limiting with hourly caps
- BaseScraper: Abstract base class for all scrapers
- Browser utilities: Playwright setup with anti-detection

On Windows, Playwright runs via sync API in a thread pool to avoid
asyncio event loop conflicts with uvicorn/FastAPI.
"""

import asyncio
import random
import sys
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from urllib.parse import quote_plus, urlencode
from concurrent.futures import ThreadPoolExecutor

from .windows_compat import get_playwright_executor

logger = logging.getLogger(__name__)


@dataclass
class BusinessLead:
    """Standardized business lead data structure."""

    # Required fields
    source: str  # google_maps, yelp, yellowpages, bbb, manta
    name: str
    city: str
    state: str

    # Contact info
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    email_source: Optional[str] = None  # scraper, website, google_search, guessed

    # Ratings and reviews
    rating: Optional[float] = None
    review_count: Optional[int] = None

    # Business info
    categories: List[str] = field(default_factory=list)
    is_claimed: bool = False
    is_sponsored: bool = False

    # URLs
    detail_url: Optional[str] = None

    # Source-specific fields (BBB rating, years in business, etc.)
    extra_data: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "source": self.source,
            "name": self.name,
            "phone": self.phone,
            "website": self.website,
            "address": self.address,
            "email": self.email,
            "email_source": self.email_source,
            "city": self.city,
            "state": self.state,
            "rating": self.rating,
            "review_count": self.review_count,
            "categories": ", ".join(self.categories),
            "is_claimed": self.is_claimed,
            "is_sponsored": self.is_sponsored,
            "detail_url": self.detail_url,
            "scraped_at": self.scraped_at.isoformat(),
            **self.extra_data,
        }


class RateLimiter:
    """
    Per-source rate limiting with hourly caps.

    Each source has different rate limits to avoid detection:
    - Google Maps: 5-10s between requests, 100/hour
    - Yelp: 3-5s between requests, 150/hour
    - YellowPages: 2-4s between requests, 200/hour
    - BBB: 3-5s between requests, 120/hour
    - Manta: 3-6s between requests, 100/hour
    """

    RATE_LIMITS = {
        "google_maps": {"min_delay": 5, "max_delay": 10, "hourly_cap": 100},
        "yelp": {"min_delay": 3, "max_delay": 5, "hourly_cap": 150},
        "yellowpages": {"min_delay": 2, "max_delay": 4, "hourly_cap": 200},
        "bbb": {"min_delay": 3, "max_delay": 5, "hourly_cap": 120},
        "manta": {"min_delay": 3, "max_delay": 6, "hourly_cap": 100},
    }

    def __init__(self):
        self._last_request: Dict[str, float] = {}
        self._hourly_counts: Dict[str, List[datetime]] = {}

    def _clean_old_requests(self, source: str) -> None:
        """Remove requests older than 1 hour."""
        if source not in self._hourly_counts:
            self._hourly_counts[source] = []
            return

        one_hour_ago = datetime.now() - timedelta(hours=1)
        self._hourly_counts[source] = [
            dt for dt in self._hourly_counts[source] if dt > one_hour_ago
        ]

    def get_requests_in_last_hour(self, source: str) -> int:
        """Get number of requests made in the last hour."""
        self._clean_old_requests(source)
        return len(self._hourly_counts.get(source, []))

    def can_make_request(self, source: str) -> bool:
        """Check if we can make a request without hitting hourly cap."""
        if source not in self.RATE_LIMITS:
            return True

        self._clean_old_requests(source)
        hourly_cap = self.RATE_LIMITS[source]["hourly_cap"]
        current_count = len(self._hourly_counts.get(source, []))

        return current_count < hourly_cap

    async def wait_if_needed(self, source: str) -> None:
        """Wait for appropriate delay before making a request."""
        if source not in self.RATE_LIMITS:
            return

        limits = self.RATE_LIMITS[source]

        # Check hourly cap
        if not self.can_make_request(source):
            wait_time = 60  # Wait 1 minute if at cap
            logger.warning(f"Hourly cap reached for {source}, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            return await self.wait_if_needed(source)

        # Calculate delay since last request
        last_time = self._last_request.get(source, 0)
        elapsed = time.time() - last_time
        min_delay = limits["min_delay"]
        max_delay = limits["max_delay"]

        # Random delay within range
        target_delay = random.uniform(min_delay, max_delay)

        if elapsed < target_delay:
            wait_time = target_delay - elapsed
            logger.debug(f"Rate limiting {source}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

    def record_request(self, source: str) -> None:
        """Record that a request was made."""
        self._last_request[source] = time.time()
        if source not in self._hourly_counts:
            self._hourly_counts[source] = []
        self._hourly_counts[source].append(datetime.now())
    
    def wait_sync(self, source: str) -> None:
        """Synchronous wait for rate limiting (used in thread pool)."""
        if source not in self.RATE_LIMITS:
            return
        
        limits = self.RATE_LIMITS[source]
        last_time = self._last_request.get(source, 0)
        elapsed = time.time() - last_time
        target_delay = random.uniform(limits["min_delay"], limits["max_delay"])
        
        if elapsed < target_delay:
            time.sleep(target_delay - elapsed)


# User agent rotation pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.

    Each scraper must implement:
    - search(): Find businesses matching criteria
    - get_details(): Get detailed info for a specific business
    
    On Windows, all Playwright operations run via the sync API in a thread pool
    to avoid asyncio event loop conflicts.
    """

    SOURCE_NAME: str = ""  # Override in subclass

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter()
        self._playwright = None
        self._browser = None
        self._context = None
        self._started = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self, headless: bool = True) -> None:
        """Initialize browser and context."""
        if self._started:
            return
        
        def _init():
            import sys
            import asyncio as aio
            from playwright.sync_api import sync_playwright
            
            # CRITICAL: Set ProactorEventLoop policy in this thread
            # sync_playwright creates an internal event loop that needs subprocess support
            if sys.platform == "win32":
                aio.set_event_loop_policy(aio.WindowsProactorEventLoopPolicy())
            
            pw = sync_playwright().start()
            browser = pw.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(USER_AGENTS),
                locale="en-US",
                timezone_id="America/New_York",
            )
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)
            return pw, browser, context
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        self._playwright, self._browser, self._context = await loop.run_in_executor(
            executor, _init
        )
        self._started = True
        logger.info(f"{self.SOURCE_NAME} scraper started")

    async def close(self) -> None:
        """Clean up browser resources."""
        if not self._started:
            return
        
        def _cleanup():
            try:
                if self._context:
                    self._context.close()
                if self._browser:
                    self._browser.close()
                if self._playwright:
                    self._playwright.stop()
            except Exception as e:
                logger.debug(f"Error during cleanup: {e}")
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        await loop.run_in_executor(executor, _cleanup)
        
        self._context = None
        self._browser = None
        self._playwright = None
        self._started = False
        logger.info(f"{self.SOURCE_NAME} scraper closed")

    async def run_in_browser(self, func: Callable, *args, **kwargs) -> Any:
        """
        Run a synchronous function in the browser thread pool.
        
        The function receives (context, *args, **kwargs).
        """
        if not self._started:
            raise RuntimeError("Browser not started. Call start() first.")
        
        def _run():
            return func(self._context, *args, **kwargs)
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        return await loop.run_in_executor(executor, _run)

    async def wait_and_record(self) -> None:
        """Wait for rate limit and record the request."""
        await self.rate_limiter.wait_if_needed(self.SOURCE_NAME)
        self.rate_limiter.record_request(self.SOURCE_NAME)

    @abstractmethod
    async def search(
        self, business_type: str, city: str, state: str, max_results: int = 20
    ) -> List[BusinessLead]:
        """
        Search for businesses matching the criteria.

        Args:
            business_type: Type of business (plumber, dentist, pest control, etc.)
            city: City name
            state: State abbreviation (TX, FL, etc.)
            max_results: Maximum number of results to return

        Returns:
            List of BusinessLead objects
        """
        pass

    @abstractmethod
    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """
        Get detailed information for a business.

        Args:
            lead: BusinessLead with at least detail_url populated

        Returns:
            BusinessLead with additional details filled in
        """
        pass

    def is_sponsored(self, element) -> bool:
        """Check if a listing is sponsored/ad. Override in subclass."""
        return False

    @staticmethod
    def clean_phone(phone: Optional[str]) -> Optional[str]:
        """Normalize phone number format."""
        if not phone:
            return None
        # Remove all non-digit characters
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == "1":
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        return phone

    @staticmethod
    def clean_rating(rating_str: Optional[str]) -> Optional[float]:
        """Parse rating string to float."""
        if not rating_str:
            return None
        try:
            # Handle locale-specific formats (4,8 vs 4.8)
            cleaned = rating_str.replace(",", ".").strip()
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def clean_review_count(count_str: Optional[str]) -> Optional[int]:
        """Parse review count string to int."""
        if not count_str:
            return None
        try:
            # Extract digits only
            digits = "".join(c for c in count_str if c.isdigit())
            return int(digits) if digits else None
        except ValueError:
            return None
