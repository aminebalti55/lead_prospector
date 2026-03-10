"""Tests for the cold outreach EmailExtractor module."""

import pytest

from src.cold_outreach.email_extractor import (
    EmailExtractor,
    EmailResult,
    EMAIL_REGEX,
    EXCLUDED_DOMAINS,
)


@pytest.fixture
def extractor():
    """Create an EmailExtractor instance (no engine needed for unit tests)."""
    return EmailExtractor(engine=None)


# ---------------------------------------------------------------------------
# _find_emails — basic extraction
# ---------------------------------------------------------------------------

class TestFindEmails:
    """Tests for EmailExtractor._find_emails."""

    def test_finds_simple_email(self, extractor):
        html = "<p>Contact us at info@acmeplumbing.com for more info.</p>"
        result = extractor._find_emails(html)
        assert result == ["info@acmeplumbing.com"]

    def test_finds_multiple_emails(self, extractor):
        html = """
        <p>Email us: sales@example-biz.com</p>
        <a href="mailto:support@example-biz.com">Support</a>
        """
        result = extractor._find_emails(html)
        assert "sales@example-biz.com" in result
        assert "support@example-biz.com" in result

    def test_deduplicates(self, extractor):
        html = """
        <p>info@acme.com</p>
        <p>INFO@ACME.COM</p>
        <p>info@acme.com</p>
        """
        result = extractor._find_emails(html)
        assert result == ["info@acme.com"]

    def test_lowercases_emails(self, extractor):
        html = "<p>Contact JOHN@BigCompany.COM today.</p>"
        result = extractor._find_emails(html)
        assert result == ["john@bigcompany.com"]

    def test_empty_html(self, extractor):
        assert extractor._find_emails("") == []

    def test_no_emails_in_html(self, extractor):
        html = "<p>Call us at (555) 123-4567 today!</p>"
        assert extractor._find_emails(html) == []

    def test_email_in_mailto(self, extractor):
        html = '<a href="mailto:hello@mybusiness.net">Email us</a>'
        result = extractor._find_emails(html)
        assert "hello@mybusiness.net" in result

    def test_email_with_plus_and_dots(self, extractor):
        html = "<p>john.doe+tag@real-company.co.uk</p>"
        result = extractor._find_emails(html)
        assert "john.doe+tag@real-company.co.uk" in result


# ---------------------------------------------------------------------------
# _find_emails — excluded domain filtering
# ---------------------------------------------------------------------------

class TestExcludedDomains:
    """Tests that emails from excluded domains are filtered out."""

    def test_filters_example_com(self, extractor):
        html = "<p>user@example.com</p>"
        assert extractor._find_emails(html) == []

    def test_filters_wixpress(self, extractor):
        html = "<p>noreply@wixpress.com</p>"
        assert extractor._find_emails(html) == []

    def test_filters_sentry(self, extractor):
        html = "<p>error@sentry.io</p>"
        assert extractor._find_emails(html) == []

    def test_filters_googleapis(self, extractor):
        html = "<p>noreply@googleapis.com</p>"
        assert extractor._find_emails(html) == []

    def test_filters_schema_org(self, extractor):
        html = "<p>info@schema.org</p>"
        assert extractor._find_emails(html) == []

    def test_filters_social_media_domains(self, extractor):
        html = """
        <p>user@facebook.com</p>
        <p>user@twitter.com</p>
        <p>user@instagram.com</p>
        """
        assert extractor._find_emails(html) == []

    def test_keeps_real_business_emails(self, extractor):
        html = """
        <p>noreply@wixpress.com</p>
        <p>contact@realbusiness.com</p>
        """
        result = extractor._find_emails(html)
        assert result == ["contact@realbusiness.com"]

    def test_all_excluded_domains_filtered(self, extractor):
        """Every domain in EXCLUDED_DOMAINS should be filtered."""
        for domain in EXCLUDED_DOMAINS:
            html = f"<p>test@{domain}</p>"
            result = extractor._find_emails(html)
            assert result == [], f"Expected {domain} to be excluded but got {result}"


# ---------------------------------------------------------------------------
# _find_emails — file extension filtering
# ---------------------------------------------------------------------------

class TestFileExtensionFiltering:
    """Tests that email-like strings ending in file extensions are filtered."""

    def test_filters_png(self, extractor):
        html = "<p>image@2x.png</p>"
        assert extractor._find_emails(html) == []

    def test_filters_js(self, extractor):
        html = "<p>bundle@hash.js</p>"
        assert extractor._find_emails(html) == []

    def test_filters_css(self, extractor):
        html = "<p>style@min.css</p>"
        assert extractor._find_emails(html) == []

    def test_filters_jpg(self, extractor):
        html = "<p>photo@thumb.jpg</p>"
        assert extractor._find_emails(html) == []

    def test_filters_gif(self, extractor):
        html = "<p>anim@loop.gif</p>"
        assert extractor._find_emails(html) == []


# ---------------------------------------------------------------------------
# _find_emails — edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases for email extraction."""

    def test_email_with_subdomain(self, extractor):
        html = "<p>admin@mail.mybusiness.com</p>"
        result = extractor._find_emails(html)
        assert "admin@mail.mybusiness.com" in result

    def test_preserves_order(self, extractor):
        html = "<p>first@a.com second@b.com third@c.com</p>"
        result = extractor._find_emails(html)
        assert result == ["first@a.com", "second@b.com", "third@c.com"]

    def test_mixed_valid_and_invalid(self, extractor):
        html = """
        <p>good@realbiz.com</p>
        <p>bad@example.com</p>
        <p>also-good@anotherbiz.org</p>
        <p>logo@2x.png</p>
        """
        result = extractor._find_emails(html)
        assert "good@realbiz.com" in result
        assert "also-good@anotherbiz.org" in result
        assert "bad@example.com" not in result
        assert "logo@2x.png" not in result

    def test_resolution_pattern_filtered(self, extractor):
        """Patterns like image@2x.png should be filtered."""
        html = "<p>icon@3x.png</p>"
        assert extractor._find_emails(html) == []


# ---------------------------------------------------------------------------
# EmailResult dataclass
# ---------------------------------------------------------------------------

class TestEmailResult:
    """Tests for the EmailResult dataclass."""

    def test_default_values(self):
        r = EmailResult()
        assert r.email is None
        assert r.source == ""
        assert r.confidence == "low"

    def test_custom_values(self):
        r = EmailResult(email="a@b.com", source="homepage", confidence="high")
        assert r.email == "a@b.com"
        assert r.source == "homepage"
        assert r.confidence == "high"


# ---------------------------------------------------------------------------
# extract — input validation
# ---------------------------------------------------------------------------

class TestExtractInputValidation:
    """Tests for the extract method's input handling."""

    def test_empty_website_returns_empty_result(self, extractor):
        result = extractor.extract("")
        assert result.email is None
        assert result.source == ""

    def test_none_website_returns_empty_result(self, extractor):
        result = extractor.extract(None)
        assert result.email is None
