"""
Lead Prospector - Configuration Module
Handles all settings, API keys, and environment configuration.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent  # src/ -> lead_prospector/
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


class APISettings(BaseSettings):
    """API keys and endpoints configuration."""

    # Google Places API
    google_places_api_key: str = Field(default="", env="GOOGLE_PLACES_API_KEY")
    google_places_base_url: str = "https://maps.googleapis.com/maps/api/place"

    # Yelp Fusion API
    yelp_api_key: str = Field(default="", env="YELP_API_KEY")
    yelp_base_url: str = "https://api.yelp.com/v3"

    # Optional: PageSpeed Insights API (free, no key required for basic usage)
    pagespeed_api_key: str = Field(default="", env="PAGESPEED_API_KEY")
    pagespeed_base_url: str = (
        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class SearchSettings(BaseSettings):
    """Search and scraping configuration."""

    # Target niches - keywords for each category
    niches: dict = {
        "plumbing": [
            "plumber",
            "plumbing",
            "plumbing service",
            "emergency plumber",
            "drain cleaning",
            "pipe repair",
        ],
        "dental": [
            "dentist",
            "dental clinic",
            "dental office",
            "family dentist",
            "cosmetic dentist",
            "dental care",
        ],
        "pest_control": [
            "pest control",
            "exterminator",
            "pest removal",
            "termite control",
            "rodent control",
            "bug exterminator",
        ],
    }

    # Yelp category aliases
    yelp_categories: dict = {
        "plumbing": "plumbing",
        "dental": "dentists",
        "pest_control": "pest_control",
    }

    # Google Places types
    google_types: dict = {
        "plumbing": "plumber",
        "dental": "dentist",
        "pest_control": "pest_control",
    }

    # Search radius in meters (default 25 miles = ~40km)
    search_radius_meters: int = 40000

    # Maximum results per source per location
    max_results_per_source: int = 60

    # Rate limiting
    requests_per_second: float = 2.0

    class Config:
        extra = "ignore"


class AuditSettings(BaseSettings):
    """Website audit configuration."""

    # Request timeout in seconds
    request_timeout: int = 15

    # User agent for requests
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Keywords indicating booking/CTA presence
    booking_keywords: list = [
        "book",
        "schedule",
        "appointment",
        "reserve",
        "request quote",
        "get quote",
        "free estimate",
        "contact us",
        "call now",
        "book online",
        "schedule now",
        "request service",
        "get started",
        "book appointment",
        "schedule appointment",
        "free consultation",
    ]

    # Keywords indicating contact forms
    contact_form_keywords: list = [
        "form",
        "input",
        "textarea",
        "submit",
        "send message",
        "contact form",
        "get in touch",
        "reach out",
    ]

    # Keywords in reviews indicating operational pain
    ops_pain_keywords: list = [
        "never called back",
        "didn't respond",
        "hard to reach",
        "couldn't get through",
        "no one answered",
        "missed appointment",
        "showed up late",
        "didn't show up",
        "poor communication",
        "scheduling nightmare",
        "couldn't schedule",
        "waited forever",
        "no follow up",
        "lost my information",
        "had to call multiple times",
        "unresponsive",
        "unprofessional",
        "disorganized",
    ]

    # Keywords indicating conversion pain
    conversion_pain_keywords: list = [
        "no website",
        "website down",
        "couldn't find",
        "hard to find information",
        "outdated website",
        "confusing website",
        "no prices",
        "no information",
    ]

    class Config:
        extra = "ignore"


class ScoringSettings(BaseSettings):
    """Scoring and prioritization configuration."""

    # Weight factors for final score (higher = more weight)
    weights: dict = {
        "no_website": 25,
        "no_booking_cta": 20,
        "no_contact_form": 15,
        "slow_page_speed": 10,
        "not_mobile_friendly": 15,
        "no_ssl": 10,
        "ops_pain_reviews": 20,
        "conversion_pain_reviews": 15,
        "low_rating": 10,
        "few_reviews": 5,
    }

    # Score thresholds (adjusted for scraping mode where website audit is often skipped)
    # no_website (25) + few_reviews (5) + low_rating (10) = 40 max without audit
    high_priority_threshold: int = 35  # Scores >= this are hot leads
    medium_priority_threshold: int = 25  # Scores >= this are warm leads

    class Config:
        extra = "ignore"


class Settings(BaseSettings):
    """Main settings container."""

    api: APISettings = APISettings()
    search: SearchSettings = SearchSettings()
    audit: AuditSettings = AuditSettings()
    scoring: ScoringSettings = ScoringSettings()

    # Output settings
    output_format: str = "both"  # csv, xlsx, or both
    output_filename: str = "lead_prospects"

    # Concurrency
    max_concurrent_requests: int = 5

    # Logging
    log_level: str = "INFO"

    class Config:
        extra = "ignore"


# Global settings instance
settings = Settings()


def validate_api_keys() -> dict[str, bool]:
    """Validate that required API keys are configured."""
    return {
        "google_places": bool(settings.api.google_places_api_key),
        "yelp": bool(settings.api.yelp_api_key),
        "pagespeed": bool(settings.api.pagespeed_api_key),
    }


def get_missing_keys() -> list[str]:
    """Get list of missing API keys."""
    validation = validate_api_keys()
    missing = []
    if not validation["google_places"]:
        missing.append("GOOGLE_PLACES_API_KEY")
    if not validation["yelp"]:
        missing.append("YELP_API_KEY")
    return missing
