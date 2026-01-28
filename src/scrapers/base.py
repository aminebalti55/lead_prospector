"""
Base classes and utilities for web scrapers.

This module provides the foundation for all scraper implementations:
- BusinessLead: Dataclass for standardized lead data
- RateLimiter: Per-source rate limiting with hourly caps
- BaseScraper: Abstract base class for all scrapers

All scrapers use undetected-chromedriver for browser automation,
which provides excellent anti-detection and Windows compatibility.
"""

import asyncio
import random
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable

from selenium.webdriver.common.by import By

from .browser_manager import (
    BrowserSession,
    get_browser_executor,
    safe_get,
    safe_find_element,
    safe_find_elements,
    scroll_page,
    scroll_element,
    get_text_safe,
    get_attribute_safe,
    USER_AGENTS,
)

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
    - Google Maps: 3-6s between requests, 150/hour
    - Yelp: 2-4s between requests, 200/hour
    - YellowPages: 1-3s between requests, 300/hour
    - BBB: 2-4s between requests, 200/hour
    - Manta: 2-5s between requests, 150/hour
    """

    RATE_LIMITS = {
        "google_maps": {"min_delay": 3, "max_delay": 6, "hourly_cap": 150},
        "yelp": {"min_delay": 2, "max_delay": 4, "hourly_cap": 200},
        "yellowpages": {"min_delay": 1, "max_delay": 3, "hourly_cap": 300},
        "bbb": {"min_delay": 2, "max_delay": 4, "hourly_cap": 200},
        "manta": {"min_delay": 2, "max_delay": 5, "hourly_cap": 150},
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

    def record_request(self, source: str) -> None:
        """Record that a request was made."""
        self._last_request[source] = time.time()
        if source not in self._hourly_counts:
            self._hourly_counts[source] = []
        self._hourly_counts[source].append(datetime.now())

    async def wait_if_needed(self, source: str) -> None:
        """Async wait - runs sync wait in thread pool."""
        loop = asyncio.get_running_loop()
        executor = get_browser_executor()
        await loop.run_in_executor(executor, lambda: self.wait_sync(source))


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.

    Each scraper must implement:
    - search(): Find businesses matching criteria
    - get_details(): Get detailed info for a specific business
    
    Uses undetected-chromedriver for all browser operations,
    providing excellent anti-detection and Windows compatibility.
    """

    SOURCE_NAME: str = ""  # Override in subclass

    def __init__(self, rate_limiter: Optional[RateLimiter] = None, headless: bool = True):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.headless = headless
        self._session: Optional[BrowserSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        print(f"[SCRAPER] Starting {self.SOURCE_NAME} scraper...")
        logger.info(f"Starting {self.SOURCE_NAME} scraper")
        self._session = BrowserSession(headless=self.headless)
        await self._session.__aenter__()
        print(f"[SCRAPER] {self.SOURCE_NAME} scraper ready!")
        logger.info(f"{self.SOURCE_NAME} scraper started")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        print(f"[SCRAPER] Closing {self.SOURCE_NAME} scraper...")
        if self._session:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
            self._session = None
        print(f"[SCRAPER] {self.SOURCE_NAME} scraper closed")
        logger.info(f"{self.SOURCE_NAME} scraper closed")

    async def run_in_browser(self, func: Callable, *args, **kwargs) -> Any:
        """
        Run a function with the browser driver.
        
        The function receives (driver, *args, **kwargs).
        """
        print(f"[RUN_IN_BROWSER] Running function {func.__name__ if hasattr(func, '__name__') else func}...")
        if not self._session:
            print("[RUN_IN_BROWSER] ERROR: Browser not started!")
            raise RuntimeError("Browser not started. Use async context manager.")
        result = await self._session.run(func, *args, **kwargs)
        print(f"[RUN_IN_BROWSER] Function completed")
        return result

    def wait_and_record_sync(self) -> None:
        """Synchronous rate limiting (call from within thread pool)."""
        self.rate_limiter.wait_sync(self.SOURCE_NAME)
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
            # Extract first number
            import re
            match = re.search(r"(\d+\.?\d*)", cleaned)
            if match:
                return float(match.group(1))
            return None
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
