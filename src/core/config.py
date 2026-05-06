"""
Lead Prospector v2 - Configuration Module
Handles all settings, API keys, and environment configuration.
Extends the original config with direct lead and scraping settings.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Project paths. Persistence is now Supabase — local dirs are for runtime
# scratch only (logs, scraper cache).
PROJECT_ROOT = Path(__file__).parent.parent.parent  # src/core/ -> src/ -> lead_prospector/
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

DATA_DIR.mkdir(exist_ok=True)
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

    # Target niches - keywords for each category. High-ROI for cold-emailing
    # SMBs as a freelance dev (web design / landing pages / booking systems).
    niches: dict = {
        # Tier 1 - Home services ($3-10K project value, terrible sites, emergency-driven)
        "plumbing": [
            "plumber", "plumbing", "plumbing service",
            "emergency plumber", "drain cleaning", "pipe repair",
        ],
        "hvac": [
            "hvac", "hvac contractor", "heating cooling", "air conditioning repair",
            "furnace repair", "ac repair", "hvac service",
        ],
        "roofing": [
            "roofing", "roofer", "roof repair", "roofing contractor",
            "metal roofing", "shingle replacement",
        ],
        "pest_control": [
            "pest control", "exterminator", "pest removal",
            "termite control", "rodent control", "bug exterminator",
        ],

        # Tier 1 - Healthcare specialists (high LTV per patient, marketing-savvy)
        "dental": [
            "dentist", "dental clinic", "dental office",
            "family dentist", "cosmetic dentist", "dental care",
        ],
        "cosmetic_dentist": [
            "cosmetic dentist", "orthodontist", "invisalign provider",
            "teeth whitening", "veneers dentist", "smile makeover",
        ],
        "med_spa": [
            "med spa", "medical spa", "aesthetic clinic", "botox clinic",
            "laser hair removal", "skin clinic",
        ],

        # Tier 1 - Legal (highest marketing spend per dollar earned)
        "personal_injury_lawyer": [
            "personal injury lawyer", "personal injury attorney", "accident lawyer",
            "car accident lawyer", "injury law firm", "trial attorney",
        ],

        # Tier 2 - Real estate + auto (high-volume, lots of small budgets that add up)
        "real_estate": [
            "real estate broker", "realtor", "real estate agent",
            "property management", "real estate office",
        ],
        "auto_repair": [
            "auto repair", "auto shop", "mechanic", "auto body",
            "transmission repair", "brake repair",
        ],
    }

    # Yelp category aliases - slugs from yelp.com/categories
    yelp_categories: dict = {
        "plumbing": "plumbing",
        "hvac": "hvac",
        "roofing": "roofing",
        "pest_control": "pestcontrol",
        "dental": "dentists",
        "cosmetic_dentist": "cosmeticdentists",
        "med_spa": "medspas",
        "personal_injury_lawyer": "personal_injury_law",
        "real_estate": "realestateagents",
        "auto_repair": "autorepair",
    }

    # Google Places types (https://developers.google.com/maps/documentation/places/web-service/supported_types)
    google_types: dict = {
        "plumbing": "plumber",
        "hvac": "hvac_contractor",
        "roofing": "roofing_contractor",
        "pest_control": "pest_control",
        "dental": "dentist",
        "cosmetic_dentist": "dentist",
        "med_spa": "spa",
        "personal_injury_lawyer": "lawyer",
        "real_estate": "real_estate_agency",
        "auto_repair": "car_repair",
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


class DirectLeadSettings(BaseSettings):
    """Direct lead generation settings for freelance/service matching."""

    your_skills: list[str] = Field(
        default=["python", "react", "nextjs", "fastapi", "typescript", "postgresql"]
    )
    your_services: list[str] = Field(
        default=[
            "web app",
            "saas",
            "api",
            "automation",
            "mvp",
            "full-stack development",
        ]
    )
    your_hourly_rate: int = Field(default=75)
    your_min_budget: int = Field(default=500)

    # Drop hiring-type leads older than this. Stale job posts never convert.
    # Agencies (GoodFirms/Clutch) are not date-sensitive and bypass this.
    max_age_days: int = Field(default=30)

    class Config:
        extra = "ignore"


class ScrapingSettings(BaseSettings):
    """Web scraping configuration."""

    proxy_url: str | None = Field(default=None)
    max_concurrent_scrapers: int = Field(default=3)

    class Config:
        extra = "ignore"


class Settings(BaseSettings):
    """Main settings container."""

    api: APISettings = APISettings()
    search: SearchSettings = SearchSettings()
    audit: AuditSettings = AuditSettings()
    scoring: ScoringSettings = ScoringSettings()
    direct_leads: DirectLeadSettings = DirectLeadSettings()
    scraping: ScrapingSettings = ScrapingSettings()

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
