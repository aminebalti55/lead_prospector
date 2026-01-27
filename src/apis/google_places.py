"""
Google Places API Integration
Fetches local business data from Google Places API.
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
class GooglePlaceBusiness:
    """Represents a business from Google Places."""

    place_id: str
    name: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: int = 0
    business_status: str = "OPERATIONAL"
    types: list = field(default_factory=list)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_level: Optional[int] = None
    # Additional details from Place Details API
    opening_hours: Optional[dict] = None
    reviews: list = field(default_factory=list)
    source: str = "google_places"


class GooglePlacesClient:
    """Client for Google Places API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.api.google_places_api_key
        self.base_url = settings.api.google_places_base_url
        self.client: Optional[httpx.AsyncClient] = None

        if not self.api_key:
            logger.warning("Google Places API key not configured")

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make an API request with retry logic."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        params["key"] = self.api_key
        url = f"{self.base_url}/{endpoint}/json"

        response = await self.client.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if data.get("status") == "REQUEST_DENIED":
            raise Exception(
                f"API Request Denied: {data.get('error_message', 'Unknown error')}"
            )

        return data

    async def text_search(
        self, query: str, location: str, radius: int = None
    ) -> list[GooglePlaceBusiness]:
        """
        Search for businesses using text query.

        Args:
            query: Search query (e.g., "plumber")
            location: Location string (e.g., "Austin, TX")
            radius: Search radius in meters
        """
        if not self.api_key:
            logger.error("Google Places API key not configured")
            return []

        radius = radius or settings.search.search_radius_meters

        params = {"query": f"{query} in {location}", "radius": radius}

        all_results = []
        next_page_token = None

        # Fetch up to 3 pages (60 results max)
        for page in range(3):
            if page > 0:
                if not next_page_token:
                    break
                # Google requires a short delay before using next_page_token
                await asyncio.sleep(2)
                params = {"pagetoken": next_page_token}
                params["key"] = self.api_key

            try:
                data = await self._make_request("textsearch", params)

                results = data.get("results", [])
                for result in results:
                    business = self._parse_place_result(result)
                    all_results.append(business)

                next_page_token = data.get("next_page_token")

                logger.info(
                    f"Google Places page {page + 1}: Found {len(results)} results"
                )

            except Exception as e:
                logger.error(f"Error fetching Google Places results: {e}")
                break

        return all_results

    async def nearby_search(
        self, location_coords: tuple[float, float], place_type: str, radius: int = None
    ) -> list[GooglePlaceBusiness]:
        """
        Search for nearby businesses by type.

        Args:
            location_coords: (latitude, longitude) tuple
            place_type: Google place type (e.g., "plumber", "dentist")
            radius: Search radius in meters
        """
        if not self.api_key:
            logger.error("Google Places API key not configured")
            return []

        radius = radius or settings.search.search_radius_meters
        lat, lng = location_coords

        params = {"location": f"{lat},{lng}", "radius": radius, "type": place_type}

        all_results = []
        next_page_token = None

        for page in range(3):
            if page > 0:
                if not next_page_token:
                    break
                await asyncio.sleep(2)
                params = {"pagetoken": next_page_token}
                params["key"] = self.api_key

            try:
                data = await self._make_request("nearbysearch", params)

                results = data.get("results", [])
                for result in results:
                    business = self._parse_place_result(result)
                    all_results.append(business)

                next_page_token = data.get("next_page_token")

            except Exception as e:
                logger.error(f"Error fetching nearby results: {e}")
                break

        return all_results

    async def get_place_details(self, place_id: str) -> Optional[GooglePlaceBusiness]:
        """
        Get detailed information about a specific place.

        Args:
            place_id: Google Place ID
        """
        if not self.api_key:
            return None

        params = {
            "place_id": place_id,
            "fields": (
                "place_id,name,formatted_address,formatted_phone_number,"
                "website,rating,user_ratings_total,business_status,"
                "types,geometry,price_level,opening_hours,reviews"
            ),
        }

        try:
            data = await self._make_request("details", params)
            result = data.get("result", {})

            return GooglePlaceBusiness(
                place_id=result.get("place_id", place_id),
                name=result.get("name", ""),
                address=result.get("formatted_address", ""),
                phone=result.get("formatted_phone_number"),
                website=result.get("website"),
                rating=result.get("rating"),
                review_count=result.get("user_ratings_total", 0),
                business_status=result.get("business_status", "OPERATIONAL"),
                types=result.get("types", []),
                latitude=result.get("geometry", {}).get("location", {}).get("lat"),
                longitude=result.get("geometry", {}).get("location", {}).get("lng"),
                price_level=result.get("price_level"),
                opening_hours=result.get("opening_hours"),
                reviews=result.get("reviews", []),
            )

        except Exception as e:
            logger.error(f"Error fetching place details for {place_id}: {e}")
            return None

    def _parse_place_result(self, result: dict) -> GooglePlaceBusiness:
        """Parse a place result from search API."""
        geometry = result.get("geometry", {})
        location = geometry.get("location", {})

        return GooglePlaceBusiness(
            place_id=result.get("place_id", ""),
            name=result.get("name", ""),
            address=result.get("formatted_address", ""),
            rating=result.get("rating"),
            review_count=result.get("user_ratings_total", 0),
            business_status=result.get("business_status", "OPERATIONAL"),
            types=result.get("types", []),
            latitude=location.get("lat"),
            longitude=location.get("lng"),
            price_level=result.get("price_level"),
        )

    async def search_niche(
        self, niche: str, location: str, fetch_details: bool = True
    ) -> list[GooglePlaceBusiness]:
        """
        Search for businesses in a specific niche.

        Args:
            niche: Niche key (plumbing, dental, pest_control)
            location: Location string
            fetch_details: Whether to fetch detailed info for each result
        """
        keywords = settings.search.niches.get(niche, [niche])
        all_businesses = {}  # Use dict to deduplicate by place_id

        for keyword in keywords[:2]:  # Limit to first 2 keywords to avoid rate limits
            logger.info(f"Searching Google Places: '{keyword}' in {location}")

            results = await self.text_search(keyword, location)

            for business in results:
                if business.place_id not in all_businesses:
                    all_businesses[business.place_id] = business

            # Rate limiting
            await asyncio.sleep(0.5)

        businesses = list(all_businesses.values())

        # Optionally fetch details for each business
        if fetch_details and businesses:
            logger.info(f"Fetching details for {len(businesses)} businesses...")
            detailed_businesses = []

            for business in businesses:
                detailed = await self.get_place_details(business.place_id)
                if detailed:
                    detailed_businesses.append(detailed)
                else:
                    detailed_businesses.append(business)
                await asyncio.sleep(0.3)  # Rate limiting

            return detailed_businesses

        return businesses


async def test_google_places():
    """Test function for Google Places API."""
    async with GooglePlacesClient() as client:
        results = await client.search_niche(
            "plumbing", "Austin, TX", fetch_details=False
        )
        print(f"Found {len(results)} plumbing businesses")
        for r in results[:3]:
            print(f"  - {r.name}: {r.address}")


if __name__ == "__main__":
    asyncio.run(test_google_places())
