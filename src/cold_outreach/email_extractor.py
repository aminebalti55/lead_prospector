"""
Email Extractor Module (v2)

Extracts email addresses from business websites using Scrapling.
Uses a multi-step approach:
1. Fetcher.get(homepage) - fast HTTP
2. Fetcher.get(/contact), Fetcher.get(/about) - common pages
3. StealthyFetcher.get(homepage) - JS fallback only if steps 1-2 found nothing
4. Domain-based email guessing (last resort)
"""

import re
import logging
from dataclasses import dataclass

from scrapling import Fetcher, StealthyFetcher

from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

EXCLUDED_DOMAINS = {
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
    "w3.org",
    "schema.org",
    "googleapis.com",
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

# File extensions that indicate a non-email match
_FILE_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".js", ".css", ".html", ".pdf", ".doc", ".docx", ".xml",
)


@dataclass
class EmailResult:
    """Result of email extraction for a single business."""

    email: str | None = None
    source: str = ""  # "homepage", "contact_page", "about_page", "js_rendered", "guessed"
    confidence: str = "low"  # "high", "medium", "low"


class EmailExtractor:
    """
    Extracts email addresses from business websites using Scrapling.

    Uses a tiered approach for speed: fast HTTP first, JS rendering only as fallback.
    """

    def __init__(self, engine: ScraperEngine | None = None):
        self.engine = engine or ScraperEngine()

    def extract(self, website: str) -> EmailResult:
        """Extract email from a business website."""
        if not website:
            return EmailResult()

        # Normalize URL
        url = website if website.startswith("http") else f"https://{website}"

        # Step 1: Try homepage via HTTP
        try:
            page = Fetcher().get(url)
            if page:
                text = str(page)  # get raw HTML
                emails = self._find_emails(text)
                if emails:
                    return EmailResult(
                        email=emails[0], source="homepage", confidence="high"
                    )
        except Exception:
            pass

        # Step 2: Try /contact and /about pages
        for path, source_name in [
            ("/contact", "contact_page"),
            ("/about", "about_page"),
            ("/contact-us", "contact_page"),
        ]:
            try:
                page = Fetcher().get(url.rstrip("/") + path)
                if page:
                    emails = self._find_emails(str(page))
                    if emails:
                        return EmailResult(
                            email=emails[0], source=source_name, confidence="high"
                        )
            except Exception:
                continue

        # Step 3: JS-rendered fallback
        try:
            page = StealthyFetcher().get(url)
            if page:
                emails = self._find_emails(str(page))
                if emails:
                    return EmailResult(
                        email=emails[0], source="js_rendered", confidence="medium"
                    )
        except Exception:
            pass

        # Step 4: Guess common emails from domain
        try:
            from tldextract import extract as tld_extract

            parsed = tld_extract(url)
            domain = f"{parsed.domain}.{parsed.suffix}"
            if domain and parsed.suffix and domain not in EXCLUDED_DOMAINS:
                return EmailResult(
                    email=f"info@{domain}", source="guessed", confidence="low"
                )
        except Exception:
            pass

        return EmailResult()

    def _find_emails(self, html: str) -> list[str]:
        """Find valid emails in HTML text."""
        raw_emails = EMAIL_REGEX.findall(html)
        valid: list[str] = []
        for email in raw_emails:
            email = email.lower().strip()
            domain = email.split("@")[1] if "@" in email else ""

            # Skip excluded domains
            if domain in EXCLUDED_DOMAINS:
                continue

            # Skip file extensions masquerading as emails
            if any(email.endswith(ext) for ext in _FILE_EXTENSIONS):
                continue

            # Skip malformed domains
            if not domain or domain.startswith("."):
                continue

            # Skip image resolution patterns like user@2x.png
            if re.search(r"@\d+x\.", email):
                continue

            valid.append(email)

        # Deduplicate preserving order
        return list(dict.fromkeys(valid))
