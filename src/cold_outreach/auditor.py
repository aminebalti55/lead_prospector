"""
Website Auditor Module (v2)
Performs lightweight website audits using Scrapling's Fetcher to detect pain signals.
"""

import time
import logging
from dataclasses import dataclass, field

from scrapling import Fetcher

from src.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WebsiteAuditResult:
    """Results from a website audit."""

    url: str
    is_reachable: bool = False
    has_ssl: bool = False
    has_booking_cta: bool = False
    has_contact_form: bool = False
    is_mobile_friendly: bool = True
    page_load_time_ms: int | None = None
    pain_signals: list[str] = field(default_factory=list)
    error: str | None = None


class WebsiteAuditor:
    """Performs lightweight website audits using Scrapling."""

    def __init__(self):
        self.audit_settings = settings.audit
        self.fetcher = Fetcher()

    def audit(self, url: str) -> WebsiteAuditResult:
        """Audit a website for pain signals."""
        result = WebsiteAuditResult(url=url)
        try:
            start = time.time()
            page = self.fetcher.get(url)
            result.page_load_time_ms = int((time.time() - start) * 1000)
            result.is_reachable = True

            # Check SSL
            result.has_ssl = url.startswith("https")

            # Get page text for keyword scanning
            text = page.get_all_text().lower() if page else ""
            html = str(page) if page else ""  # raw HTML for form detection

            # Check booking CTA
            result.has_booking_cta = any(
                kw in text for kw in self.audit_settings.booking_keywords
            )

            # Check contact form (look for <form>, <input>, <textarea> elements)
            result.has_contact_form = any(
                kw in html.lower() for kw in ["<form", "<input", "<textarea"]
            )

            # Check mobile friendliness (look for viewport meta tag)
            result.is_mobile_friendly = "viewport" in html.lower()

            # Build pain signals
            if not result.has_ssl:
                result.pain_signals.append("no_ssl")
            if not result.has_booking_cta:
                result.pain_signals.append("no_booking_cta")
            if not result.has_contact_form:
                result.pain_signals.append("no_contact_form")
            if not result.is_mobile_friendly:
                result.pain_signals.append("not_mobile_friendly")
            if result.page_load_time_ms and result.page_load_time_ms > 5000:
                result.pain_signals.append("slow_page_load")

        except Exception as e:
            result.error = str(e)
            result.pain_signals.append("website_unreachable")

        return result


class ReviewAnalyzer:
    """Analyzes review text for pain signals."""

    def __init__(self):
        self.ops_keywords = settings.audit.ops_pain_keywords
        self.conversion_keywords = settings.audit.conversion_pain_keywords

    def analyze(self, reviews: list[str]) -> dict:
        """
        Analyze reviews for pain signals.

        Args:
            reviews: List of review text strings

        Returns:
            Dict with pain analysis counts
        """
        ops_count = 0
        conv_count = 0
        negative_count = 0
        for review in reviews:
            text = review.lower()
            if any(kw in text for kw in self.ops_keywords):
                ops_count += 1
            if any(kw in text for kw in self.conversion_keywords):
                conv_count += 1
        return {
            "ops_pain_count": ops_count,
            "conversion_pain_count": conv_count,
            "negative_reviews": negative_count,
            "total_analyzed": len(reviews),
        }
