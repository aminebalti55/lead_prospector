"""
Website Audit Module
Performs lightweight website audits to detect pain signals.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WebsiteAuditResult:
    """Results from a website audit."""

    url: str
    is_accessible: bool = False
    has_ssl: bool = False
    is_mobile_friendly: bool = True  # Assume true unless detected otherwise

    # Content analysis
    has_booking_cta: bool = False
    has_contact_form: bool = False
    has_phone_number: bool = False
    has_email: bool = False
    has_chat_widget: bool = False

    # Technical signals
    page_load_time_ms: Optional[int] = None
    page_size_kb: Optional[int] = None
    has_meta_description: bool = False
    has_title: bool = False
    title: str = ""

    # Pain signals detected
    pain_signals: list = field(default_factory=list)

    # Raw data for further analysis
    found_ctas: list = field(default_factory=list)
    found_forms: int = 0
    found_phone_numbers: list = field(default_factory=list)
    found_emails: list = field(default_factory=list)

    # Error info
    error_message: Optional[str] = None


class WebsiteAuditor:
    """Performs lightweight website audits."""

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.timeout = settings.audit.request_timeout
        self.user_agent = settings.audit.user_agent

        # Compile regex patterns
        self.phone_pattern = re.compile(
            r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}"
        )
        self.email_pattern = re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def audit_website(self, url: str) -> WebsiteAuditResult:
        """
        Perform a lightweight audit of a website.

        Args:
            url: Website URL to audit

        Returns:
            WebsiteAuditResult with detected signals
        """
        result = WebsiteAuditResult(url=url)

        # Normalize URL
        if not url:
            result.error_message = "No URL provided"
            result.pain_signals.append("no_website")
            return result

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        result.url = url

        # Check SSL
        result.has_ssl = url.startswith("https://")

        try:
            # Fetch the page
            start_time = asyncio.get_event_loop().time()
            response = await self._fetch_page(url)
            end_time = asyncio.get_event_loop().time()

            if response is None:
                result.error_message = "Failed to fetch page"
                result.pain_signals.append("website_unreachable")
                return result

            result.is_accessible = True
            result.page_load_time_ms = int((end_time - start_time) * 1000)
            result.page_size_kb = len(response.content) // 1024

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Analyze the page
            self._analyze_meta(soup, result)
            self._analyze_ctas(soup, result)
            self._analyze_forms(soup, result)
            self._analyze_contact_info(soup, response.text, result)
            self._analyze_chat_widgets(soup, response.text, result)
            self._check_mobile_viewport(soup, result)

            # Detect pain signals
            self._detect_pain_signals(result)

        except httpx.TimeoutException:
            result.error_message = "Request timed out"
            result.pain_signals.append("slow_website")
        except httpx.ConnectError:
            result.error_message = "Connection failed"
            result.pain_signals.append("website_unreachable")
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Error auditing {url}: {e}")

        return result

    @retry(
        stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def _fetch_page(self, url: str) -> Optional[httpx.Response]:
        """Fetch a page with retry logic."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        response = await self.client.get(url)
        response.raise_for_status()
        return response

    def _analyze_meta(self, soup: BeautifulSoup, result: WebsiteAuditResult):
        """Analyze meta tags and title."""
        # Title
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            result.has_title = True
            result.title = title_tag.string.strip()[:100]

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result.has_meta_description = True

    def _analyze_ctas(self, soup: BeautifulSoup, result: WebsiteAuditResult):
        """Analyze call-to-action elements."""
        cta_keywords = settings.audit.booking_keywords

        # Check buttons and links
        clickable_elements = soup.find_all(["a", "button"])

        found_ctas = []
        for element in clickable_elements:
            text = element.get_text(strip=True).lower()
            href = element.get("href", "").lower()

            for keyword in cta_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in text or keyword_lower in href:
                    found_ctas.append(
                        {
                            "text": element.get_text(strip=True)[:50],
                            "type": element.name,
                            "keyword": keyword,
                        }
                    )
                    break

        result.found_ctas = found_ctas[:10]  # Limit to 10
        result.has_booking_cta = len(found_ctas) > 0

    def _analyze_forms(self, soup: BeautifulSoup, result: WebsiteAuditResult):
        """Analyze forms on the page."""
        forms = soup.find_all("form")
        result.found_forms = len(forms)

        # Check if any form looks like a contact form
        contact_indicators = [
            "contact",
            "message",
            "email",
            "phone",
            "name",
            "inquiry",
            "quote",
        ]

        for form in forms:
            form_text = form.get_text().lower()
            form_html = str(form).lower()

            for indicator in contact_indicators:
                if indicator in form_text or indicator in form_html:
                    result.has_contact_form = True
                    break

            if result.has_contact_form:
                break

        # Also check for input fields that suggest a contact form
        if not result.has_contact_form:
            inputs = soup.find_all("input")
            textareas = soup.find_all("textarea")

            email_inputs = [
                i
                for i in inputs
                if i.get("type") == "email" or "email" in i.get("name", "").lower()
            ]
            message_areas = [
                t
                for t in textareas
                if "message" in t.get("name", "").lower()
                or "message" in t.get("placeholder", "").lower()
            ]

            if email_inputs and (
                message_areas
                or len([i for i in inputs if i.get("type") == "text"]) >= 2
            ):
                result.has_contact_form = True

    def _analyze_contact_info(
        self, soup: BeautifulSoup, html: str, result: WebsiteAuditResult
    ):
        """Extract contact information."""
        # Find phone numbers
        text = soup.get_text()
        phones = self.phone_pattern.findall(text)

        # Filter likely phone numbers (7+ digits)
        valid_phones = []
        for phone in phones:
            digits = re.sub(r"\D", "", phone)
            if len(digits) >= 10:
                valid_phones.append(phone)

        result.found_phone_numbers = list(set(valid_phones))[:5]
        result.has_phone_number = len(valid_phones) > 0

        # Find email addresses
        emails = self.email_pattern.findall(text)
        # Filter out common non-contact emails
        excluded = [
            "example.com",
            "domain.com",
            "email.com",
            "yoursite.com",
            "sentry.io",
        ]
        valid_emails = [
            e for e in emails if not any(ex in e.lower() for ex in excluded)
        ]

        result.found_emails = list(set(valid_emails))[:5]
        result.has_email = len(valid_emails) > 0

    def _analyze_chat_widgets(
        self, soup: BeautifulSoup, html: str, result: WebsiteAuditResult
    ):
        """Detect live chat widgets."""
        chat_indicators = [
            "livechat",
            "intercom",
            "drift",
            "zendesk",
            "tawk.to",
            "crisp",
            "hubspot",
            "freshchat",
            "olark",
            "livechatinc",
            "chat-widget",
            "chatbot",
            "messenger-widget",
        ]

        html_lower = html.lower()
        for indicator in chat_indicators:
            if indicator in html_lower:
                result.has_chat_widget = True
                break

    def _check_mobile_viewport(self, soup: BeautifulSoup, result: WebsiteAuditResult):
        """Check for mobile viewport meta tag."""
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if not viewport:
            result.is_mobile_friendly = False

    def _detect_pain_signals(self, result: WebsiteAuditResult):
        """Detect pain signals from audit results."""

        # No booking/CTA
        if not result.has_booking_cta:
            result.pain_signals.append("no_booking_cta")

        # No contact form
        if not result.has_contact_form:
            result.pain_signals.append("no_contact_form")

        # No visible phone number
        if not result.has_phone_number:
            result.pain_signals.append("no_phone_visible")

        # No SSL
        if not result.has_ssl:
            result.pain_signals.append("no_ssl")

        # Not mobile friendly
        if not result.is_mobile_friendly:
            result.pain_signals.append("not_mobile_friendly")

        # Slow page load (> 5 seconds)
        if result.page_load_time_ms and result.page_load_time_ms > 5000:
            result.pain_signals.append("slow_page_load")

        # Missing meta
        if not result.has_meta_description:
            result.pain_signals.append("missing_meta_description")

        if not result.has_title:
            result.pain_signals.append("missing_title")


class ReviewAnalyzer:
    """Analyzes reviews for pain signals."""

    def __init__(self):
        self.ops_keywords = settings.audit.ops_pain_keywords
        self.conversion_keywords = settings.audit.conversion_pain_keywords

    def analyze_reviews(self, reviews: list) -> dict:
        """
        Analyze reviews for pain signals.

        Args:
            reviews: List of review objects (from Google or Yelp)

        Returns:
            Dict with pain analysis results
        """
        result = {
            "total_reviews": len(reviews),
            "ops_pain_count": 0,
            "conversion_pain_count": 0,
            "ops_pain_examples": [],
            "conversion_pain_examples": [],
            "negative_reviews": 0,
            "pain_tags": [],
        }

        for review in reviews:
            # Get review text and rating
            if hasattr(review, "text"):
                text = review.text.lower()
                rating = getattr(review, "rating", 5)
            elif isinstance(review, dict):
                text = review.get("text", "").lower()
                rating = review.get("rating", 5)
            else:
                continue

            # Count negative reviews
            if rating <= 2:
                result["negative_reviews"] += 1

            # Check for ops pain keywords
            for keyword in self.ops_keywords:
                if keyword.lower() in text:
                    result["ops_pain_count"] += 1
                    if len(result["ops_pain_examples"]) < 3:
                        result["ops_pain_examples"].append(
                            {"keyword": keyword, "snippet": text[:200]}
                        )
                    break

            # Check for conversion pain keywords
            for keyword in self.conversion_keywords:
                if keyword.lower() in text:
                    result["conversion_pain_count"] += 1
                    if len(result["conversion_pain_examples"]) < 3:
                        result["conversion_pain_examples"].append(
                            {"keyword": keyword, "snippet": text[:200]}
                        )
                    break

        # Generate pain tags
        if result["ops_pain_count"] >= 2:
            result["pain_tags"].append("ops_issues_in_reviews")

        if result["conversion_pain_count"] >= 1:
            result["pain_tags"].append("conversion_issues_in_reviews")

        if result["negative_reviews"] >= 3:
            result["pain_tags"].append("many_negative_reviews")

        return result


async def test_auditor():
    """Test the website auditor."""
    async with WebsiteAuditor() as auditor:
        result = await auditor.audit_website("https://example.com")
        print(f"Audit result for {result.url}:")
        print(f"  Accessible: {result.is_accessible}")
        print(f"  SSL: {result.has_ssl}")
        print(f"  Booking CTA: {result.has_booking_cta}")
        print(f"  Contact Form: {result.has_contact_form}")
        print(f"  Pain Signals: {result.pain_signals}")


if __name__ == "__main__":
    asyncio.run(test_auditor())
