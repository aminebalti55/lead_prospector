"""
Website Finder Utilities.

This module provides helper functions for finding business websites
when they're not available from the original scraping source.

NOTE: Direct web search scraping (Google, Bing, DuckDuckGo) is blocked by CAPTCHAs.
For automated website discovery, consider:
1. Using the --fetch-details flag to get websites from detail pages (BBB, Manta)
2. Using the Firecrawl MCP tool for manual website lookups (available to AI assistants)
3. Using a paid API like SerpAPI, Google Custom Search, or Bing Search API
"""

import logging
import re
from typing import Optional, List, Set
from urllib.parse import urlparse

from .base import BusinessLead

logger = logging.getLogger(__name__)


# Default domains to skip (directories, not actual business websites)
DEFAULT_SKIP_DOMAINS: Set[str] = {
    # Business directories
    "yelp.com",
    "yellowpages.com",
    "bbb.org",
    "manta.com",
    "angieslist.com",
    "homeadvisor.com",
    "thumbtack.com",
    "houzz.com",
    "superpages.com",
    "citysearch.com",
    "mapquest.com",
    "nextdoor.com",
    "chamberofcommerce.com",
    "dandb.com",
    "buzzfile.com",
    # Social media
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "linkedin.com",
    "youtube.com",
    "pinterest.com",
    "tiktok.com",
    # Review sites
    "tripadvisor.com",
    "trustpilot.com",
    "glassdoor.com",
    # Data providers
    "opencorporates.com",
    "zoominfo.com",
    "crunchbase.com",
    # Search engines
    "google.com",
    "bing.com",
    "yahoo.com",
    "duckduckgo.com",
}


def is_valid_business_website(
    url: str, skip_domains: Optional[Set[str]] = None
) -> bool:
    """
    Check if URL is likely a real business website (not a directory or social media).

    Args:
        url: URL to check
        skip_domains: Optional set of domains to skip. Uses DEFAULT_SKIP_DOMAINS if None.

    Returns:
        True if URL appears to be a valid business website
    """
    if not url:
        return False

    skip = skip_domains or DEFAULT_SKIP_DOMAINS

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]

        # Check against skip list
        for skip_domain in skip:
            if skip_domain in domain:
                return False

        return True
    except Exception:
        return False


def extract_domain_keywords(business_name: str) -> List[str]:
    """
    Extract keywords from business name for domain matching.

    Args:
        business_name: Business name string

    Returns:
        List of keywords that might appear in the business domain
    """
    # Remove common suffixes
    name = business_name.lower()
    for suffix in [
        "llc",
        "inc",
        "corp",
        "co",
        "company",
        "services",
        "service",
        "plumbing",
        "dental",
        "pest",
        "control",
        "heating",
        "cooling",
    ]:
        name = re.sub(rf"\b{suffix}\b", "", name)

    # Split into words
    words = re.findall(r"[a-z]+", name)
    return [w for w in words if len(w) >= 3]


def find_best_website_from_results(
    search_results: List[dict],
    business_name: str,
    skip_domains: Optional[Set[str]] = None,
) -> Optional[str]:
    """
    Find the best matching website from search results.

    This function is designed to work with Firecrawl search results
    or any list of dicts with 'url' keys.

    Args:
        search_results: List of search result dicts with 'url' key
        business_name: Name of the business
        skip_domains: Optional set of domains to skip

    Returns:
        Best matching URL or None

    Example:
        # Firecrawl returns results like:
        # [{"url": "https://example.com", "title": "...", "description": "..."}]
        website = find_best_website_from_results(results, "Example Business")
    """
    if not search_results:
        return None

    keywords = extract_domain_keywords(business_name)
    skip = skip_domains or DEFAULT_SKIP_DOMAINS

    # First pass: look for domain that matches business name
    for result in search_results:
        url = result.get("url", "")
        if not is_valid_business_website(url, skip):
            continue

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
            domain_name = domain.split(".")[0]

            # Check if any keyword matches the domain
            for keyword in keywords:
                if len(keyword) >= 4 and keyword in domain_name:
                    logger.debug(f"Found matching website for {business_name}: {url}")
                    return url
        except Exception:
            continue

    # Second pass: return first valid result
    for result in search_results:
        url = result.get("url", "")
        if is_valid_business_website(url, skip):
            logger.debug(f"Found potential website for {business_name}: {url}")
            return url

    return None


def build_search_query(business_name: str, city: str, state: str) -> str:
    """
    Build a search query to find a business website.

    Args:
        business_name: Name of the business
        city: City where business is located
        state: State abbreviation

    Returns:
        Search query string optimized for finding official business website
    """
    return f"{business_name} {city} {state} official website"


def get_leads_without_websites(leads: List[BusinessLead]) -> List[BusinessLead]:
    """
    Filter leads to only those without websites.

    Args:
        leads: List of BusinessLead objects

    Returns:
        List of leads that don't have website URLs
    """
    return [lead for lead in leads if not lead.website]


def get_website_coverage_stats(leads: List[BusinessLead]) -> dict:
    """
    Calculate website coverage statistics for a list of leads.

    Args:
        leads: List of BusinessLead objects

    Returns:
        Dict with coverage statistics
    """
    total = len(leads)
    with_websites = sum(1 for lead in leads if lead.website)
    without_websites = total - with_websites

    return {
        "total": total,
        "with_websites": with_websites,
        "without_websites": without_websites,
        "coverage_percent": round(100 * with_websites / total, 1) if total > 0 else 0,
    }
