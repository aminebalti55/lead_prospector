"""
Web scrapers for lead prospection.

This package provides scrapers for multiple data sources:
- GoogleMapsScraper: Google Maps search results
- YelpScraper: Yelp business listings
- YellowPagesScraper: YellowPages directory
- BBBScraper: Better Business Bureau listings
- MantaScraper: Manta business directory

All scrapers use undetected-chromedriver for browser automation,
providing excellent anti-detection and Windows compatibility.
"""

from .base import (
    BusinessLead,
    RateLimiter,
    BaseScraper,
)

from .browser_manager import (
    BrowserSession,
    get_browser_executor,
    shutdown_browser_executor,
    create_driver,
    USER_AGENTS,
)

from .google_maps import GoogleMapsScraper
from .yelp import YelpScraper
from .yellowpages import YellowPagesScraper
from .bbb import BBBScraper
from .manta import MantaScraper

from .website_finder import (
    is_valid_business_website,
    find_best_website_from_results,
    build_search_query,
    get_leads_without_websites,
    get_website_coverage_stats,
    DEFAULT_SKIP_DOMAINS,
)

from .email_extractor import (
    EmailExtractor,
    EmailResult,
    extract_emails_for_leads,
)

__all__ = [
    # Base classes
    "BusinessLead",
    "RateLimiter",
    "BaseScraper",
    # Browser manager
    "BrowserSession",
    "get_browser_executor",
    "shutdown_browser_executor",
    "create_driver",
    "USER_AGENTS",
    # Scrapers
    "GoogleMapsScraper",
    "YelpScraper",
    "YellowPagesScraper",
    "BBBScraper",
    "MantaScraper",
    # Website finder utilities
    "is_valid_business_website",
    "find_best_website_from_results",
    "build_search_query",
    "get_leads_without_websites",
    "get_website_coverage_stats",
    "DEFAULT_SKIP_DOMAINS",
    # Email extractor
    "EmailExtractor",
    "EmailResult",
    "extract_emails_for_leads",
]
