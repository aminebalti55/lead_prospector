"""
Yelp Fusion API Integration
Fetches local business data and reviews from Yelp.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class YelpBusiness:
    """Represents a business from Yelp."""

    yelp_id: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: Optional[str] = None
    display_phone: Optional[str] = None
    website: Optional[str] = None  # Yelp URL (website requires scraping)
    rating: Optional[float] = None
    review_count: int = 0
    categories: list = field(default_factory=list)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price: Optional[str] = None  # $, $$, $$$, $$$$
    is_closed: bool = False
    yelp_url: str = ""
    reviews: list = field(default_factory=list)
    source: str = "yelp"


@dataclass
class YelpReview:
    """Represents a Yelp review."""

    id: str
    rating: int
    text: str
    time_created: str
    user_name: str


class YelpClient:
    """Client for Yelp Fusion API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.api.yelp_api_key
        self.base_url = settings.api.yelp_base_url
        self.client: Optional[httpx.AsyncClient] = None

        if not self.api_key:
            logger.warning("Yelp API key not configured")

    async def __aenter__(self):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        self.client = httpx.AsyncClient(timeout=30.0, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Make an API request with retry logic."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.base_url}/{endpoint}"

        response = await self.client.get(url, params=params or {})
        response.raise_for_status()

        return response.json()

    async def search_businesses(
        self,
        term: str,
        location: str,
        categories: str = None,
        limit: int = 50,
        offset: int = 0,
        radius: int = None,
    ) -> list[YelpBusiness]:
        """
        Search for businesses on Yelp.

        Args:
            term: Search term (e.g., "plumber")
            location: Location string (e.g., "Austin, TX")
            categories: Yelp category alias (e.g., "plumbing")
            limit: Max results per request (max 50)
            offset: Result offset for pagination
            radius: Search radius in meters (max 40000)
        """
        if not self.api_key:
            logger.error("Yelp API key not configured")
            return []

        params = {
            "term": term,
            "location": location,
            "limit": min(limit, 50),
            "offset": offset,
            "sort_by": "best_match",
        }

        if categories:
            params["categories"] = categories

        if radius:
            params["radius"] = min(radius, 40000)

        try:
            data = await self._make_request("businesses/search", params)
            businesses = []

            for biz in data.get("businesses", []):
                business = self._parse_business(biz)
                businesses.append(business)

            total = data.get("total", 0)
            logger.info(
                f"Yelp search: Found {len(businesses)} of {total} total results"
            )

            return businesses

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                logger.warning(f"Invalid Yelp search parameters: {e}")
            else:
                logger.error(f"Yelp API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching Yelp: {e}")
            return []

    async def search_all(
        self, term: str, location: str, categories: str = None, max_results: int = None
    ) -> list[YelpBusiness]:
        """
        Search for all businesses with pagination.

        Args:
            term: Search term
            location: Location string
            categories: Yelp category alias
            max_results: Maximum total results to fetch
        """
        max_results = max_results or settings.search.max_results_per_source
        all_businesses = []
        offset = 0

        while offset < max_results and offset < 1000:  # Yelp limit is 1000
            limit = min(50, max_results - offset)

            businesses = await self.search_businesses(
                term=term,
                location=location,
                categories=categories,
                limit=limit,
                offset=offset,
            )

            if not businesses:
                break

            all_businesses.extend(businesses)
            offset += len(businesses)

            # Rate limiting
            await asyncio.sleep(0.5)

        return all_businesses

    async def get_business_details(self, business_id: str) -> Optional[YelpBusiness]:
        """
        Get detailed information about a specific business.

        Args:
            business_id: Yelp business ID
        """
        if not self.api_key:
            return None

        try:
            data = await self._make_request(f"businesses/{business_id}")
            return self._parse_business(data)

        except Exception as e:
            logger.error(f"Error fetching business details for {business_id}: {e}")
            return None

    async def get_business_reviews(
        self, business_id: str, limit: int = 3
    ) -> list[YelpReview]:
        """
        Get reviews for a specific business.
        Note: Yelp API only returns up to 3 reviews.

        Args:
            business_id: Yelp business ID
            limit: Max reviews (capped at 3 by API)
        """
        if not self.api_key:
            return []

        try:
            data = await self._make_request(
                f"businesses/{business_id}/reviews", {"limit": min(limit, 3)}
            )

            reviews = []
            for review in data.get("reviews", []):
                reviews.append(
                    YelpReview(
                        id=review.get("id", ""),
                        rating=review.get("rating", 0),
                        text=review.get("text", ""),
                        time_created=review.get("time_created", ""),
                        user_name=review.get("user", {}).get("name", "Anonymous"),
                    )
                )

            return reviews

        except Exception as e:
            logger.error(f"Error fetching reviews for {business_id}: {e}")
            return []

    def _parse_business(self, data: dict) -> YelpBusiness:
        """Parse a business from Yelp API response."""
        location = data.get("location", {})
        coordinates = data.get("coordinates", {})

        # Build full address
        address_parts = [
            location.get("address1", ""),
            location.get("address2", ""),
            location.get("address3", ""),
        ]
        address = ", ".join(filter(None, address_parts))

        # Extract categories
        categories = [cat.get("alias", "") for cat in data.get("categories", [])]

        return YelpBusiness(
            yelp_id=data.get("id", ""),
            name=data.get("name", ""),
            address=address,
            city=location.get("city", ""),
            state=location.get("state", ""),
            zip_code=location.get("zip_code", ""),
            phone=data.get("phone"),
            display_phone=data.get("display_phone"),
            rating=data.get("rating"),
            review_count=data.get("review_count", 0),
            categories=categories,
            latitude=coordinates.get("latitude"),
            longitude=coordinates.get("longitude"),
            price=data.get("price"),
            is_closed=data.get("is_closed", False),
            yelp_url=data.get("url", ""),
        )

    async def search_niche(
        self, niche: str, location: str, fetch_reviews: bool = True
    ) -> list[YelpBusiness]:
        """
        Search for businesses in a specific niche.

        Args:
            niche: Niche key (plumbing, dental, pest_control)
            location: Location string
            fetch_reviews: Whether to fetch reviews for each business
        """
        category = settings.search.yelp_categories.get(niche)
        keywords = settings.search.niches.get(niche, [niche])

        all_businesses = {}  # Use dict to deduplicate by yelp_id

        # Search by category first
        if category:
            logger.info(f"Searching Yelp category: '{category}' in {location}")
            results = await self.search_all(
                term="", location=location, categories=category, max_results=40
            )
            for biz in results:
                if biz.yelp_id not in all_businesses:
                    all_businesses[biz.yelp_id] = biz

        # Then search by first keyword
        if keywords:
            keyword = keywords[0]
            logger.info(f"Searching Yelp term: '{keyword}' in {location}")
            results = await self.search_all(
                term=keyword, location=location, max_results=30
            )
            for biz in results:
                if biz.yelp_id not in all_businesses:
                    all_businesses[biz.yelp_id] = biz

        businesses = list(all_businesses.values())

        # Optionally fetch reviews for each business
        if fetch_reviews and businesses:
            logger.info(f"Fetching reviews for {len(businesses)} Yelp businesses...")

            for business in businesses:
                reviews = await self.get_business_reviews(business.yelp_id)
                business.reviews = reviews
                await asyncio.sleep(0.3)  # Rate limiting

        return businesses


async def test_yelp():
    """Test function for Yelp API."""
    async with YelpClient() as client:
        results = await client.search_niche(
            "plumbing", "Austin, TX", fetch_reviews=False
        )
        print(f"Found {len(results)} plumbing businesses on Yelp")
        for r in results[:3]:
            print(
                f"  - {r.name}: {r.address}, {r.city} ({r.rating} stars, {r.review_count} reviews)"
            )


if __name__ == "__main__":
    asyncio.run(test_yelp())
