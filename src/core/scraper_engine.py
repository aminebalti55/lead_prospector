import asyncio
import random
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from scrapling import Fetcher, StealthyFetcher, DynamicFetcher

logger = logging.getLogger(__name__)


class RateLimiter:
    """Per-source rate limiting with hourly caps."""

    RATE_LIMITS = {
        "google_maps": {"min_delay": 3, "max_delay": 6, "hourly_cap": 150},
        "yelp": {"min_delay": 2, "max_delay": 4, "hourly_cap": 200},
        "yellowpages": {"min_delay": 1, "max_delay": 3, "hourly_cap": 300},
        "bbb": {"min_delay": 2, "max_delay": 4, "hourly_cap": 200},
        "manta": {"min_delay": 2, "max_delay": 5, "hourly_cap": 150},
        "indeed": {"min_delay": 3, "max_delay": 6, "hourly_cap": 150},
        "linkedin": {"min_delay": 3, "max_delay": 6, "hourly_cap": 100},
        "clutch": {"min_delay": 1, "max_delay": 3, "hourly_cap": 300},
        "goodfirms": {"min_delay": 1, "max_delay": 3, "hourly_cap": 300},
        "twitter": {"min_delay": 2, "max_delay": 5, "hourly_cap": 150},
        "reddit": {"min_delay": 1, "max_delay": 2, "hourly_cap": 500},
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
        """Synchronous wait for rate limiting."""
        if source not in self.RATE_LIMITS:
            return

        limits = self.RATE_LIMITS[source]
        last_time = self._last_request.get(source, 0)
        elapsed = time.time() - last_time
        target_delay = random.uniform(limits["min_delay"], limits["max_delay"])

        if elapsed < target_delay:
            time.sleep(target_delay - elapsed)

    async def wait_async(self, source: str) -> None:
        """Async wait for rate limiting using asyncio.sleep."""
        if source not in self.RATE_LIMITS:
            return

        limits = self.RATE_LIMITS[source]
        last_time = self._last_request.get(source, 0)
        elapsed = time.time() - last_time
        target_delay = random.uniform(limits["min_delay"], limits["max_delay"])

        if elapsed < target_delay:
            await asyncio.sleep(target_delay - elapsed)

    def record_request(self, source: str) -> None:
        """Record that a request was made."""
        self._last_request[source] = time.time()
        if source not in self._hourly_counts:
            self._hourly_counts[source] = []
        self._hourly_counts[source].append(datetime.now())


class ScraperEngine:
    """Central Scrapling wrapper that selects the appropriate fetcher per source."""

    FETCHER_MAP = {
        "google_maps": "dynamic",
        "yelp": "stealth",
        "bbb": "stealth",
        "yellowpages": "http",
        "manta": "http",
        "indeed": "stealth",
        "linkedin": "stealth",
        "clutch": "http",
        "goodfirms": "http",
        "twitter": "stealth",
        "reddit": "http",
    }

    def __init__(self, proxy_url: Optional[str] = None):
        self.rate_limiter = RateLimiter()
        self.proxy_url = proxy_url

    def _get_fetcher(self, source: str):
        """Return the appropriate Scrapling fetcher for a source."""
        tier = self.FETCHER_MAP.get(source, "http")
        if tier == "dynamic":
            return DynamicFetcher
        elif tier == "stealth":
            return StealthyFetcher
        else:
            return Fetcher

    def fetch(self, url: str, source: str):
        """Fetch a URL using the appropriate fetcher for the source. Returns Scrapling response."""
        self.rate_limiter.wait_sync(source)
        self.rate_limiter.record_request(source)
        fetcher_class = self._get_fetcher(source)
        try:
            response = fetcher_class().get(url)
            return response
        except Exception as e:
            logger.error(f"[{source}] Error fetching {url}: {e}")
            raise

    def fetch_with_retry(self, url: str, source: str, max_retries: int = 3):
        """Fetch with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                return self.fetch(url, source)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait = (2 ** attempt) * 2  # 2s, 4s, 8s
                logger.warning(
                    f"[{source}] Retry {attempt+1}/{max_retries} for {url}, waiting {wait}s: {e}"
                )
                time.sleep(wait)

    def fetch_many(self, urls: list, source: str, delay: tuple = (2, 5)) -> list:
        """Fetch multiple URLs with delays. Returns list of (url, response|None) tuples."""
        results = []
        for url in urls:
            try:
                response = self.fetch(url, source)
                results.append((url, response))
            except Exception as e:
                logger.warning(f"[{source}] Skipping {url}: {e}")
                results.append((url, None))
            if url != urls[-1]:
                time.sleep(random.uniform(*delay))
        return results
