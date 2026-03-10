"""Tests for the LeadEnricher class."""

import pytest
from unittest.mock import patch, MagicMock
from src.core.models import DirectLead
from src.direct_leads.enricher import LeadEnricher, EXCLUDED_EMAIL_DOMAINS


class TestFindEmails:
    """Tests for LeadEnricher._find_emails."""

    def setup_method(self):
        with patch("src.direct_leads.enricher.Fetcher"):
            self.enricher = LeadEnricher()

    def test_basic_email_extraction(self):
        html = '<a href="mailto:hello@acme.com">Contact us</a>'
        result = self.enricher._find_emails(html)
        assert result == ["hello@acme.com"]

    def test_multiple_emails(self):
        html = "Contact sales@acme.com or support@acme.com for help."
        result = self.enricher._find_emails(html)
        assert result == ["sales@acme.com", "support@acme.com"]

    def test_deduplication(self):
        html = "Email info@test.org twice: info@test.org"
        result = self.enricher._find_emails(html)
        assert result == ["info@test.org"]

    def test_excluded_domains_filtered(self):
        for domain in EXCLUDED_EMAIL_DOMAINS:
            html = f"Contact us at user@{domain}"
            result = self.enricher._find_emails(html)
            assert result == [], f"Expected {domain} to be excluded"

    def test_file_extension_filtered(self):
        html = "background@2x.png and icon@3x.jpg and style@main.css"
        result = self.enricher._find_emails(html)
        assert result == []

    def test_case_normalized(self):
        html = "Email: John@ACME.COM"
        result = self.enricher._find_emails(html)
        assert result == ["john@acme.com"]

    def test_no_emails(self):
        html = "<p>No contact info here</p>"
        result = self.enricher._find_emails(html)
        assert result == []

    def test_mixed_valid_and_excluded(self):
        html = "real@company.io and fake@example.com"
        result = self.enricher._find_emails(html)
        assert result == ["real@company.io"]


class TestDetectSize:
    """Tests for LeadEnricher._detect_size."""

    def setup_method(self):
        with patch("src.direct_leads.enricher.Fetcher"):
            self.enricher = LeadEnricher()

    def test_enterprise(self):
        assert self.enricher._detect_size("We are a Fortune 500 company") == "enterprise"
        assert self.enricher._detect_size("Our global team spans 30 countries") == "enterprise"
        assert self.enricher._detect_size("1000+ employees worldwide") == "enterprise"

    def test_mid(self):
        assert self.enricher._detect_size("A mid-size firm") == "mid"
        assert self.enricher._detect_size("200+ employees and growing") == "mid"
        assert self.enricher._detect_size("Our growing team of experts") == "mid"

    def test_small(self):
        assert self.enricher._detect_size("A small team of experts") == "small"
        assert self.enricher._detect_size("boutique consulting firm") == "small"
        assert self.enricher._detect_size("50 employees strong") == "small"

    def test_startup(self):
        assert self.enricher._detect_size("A startup disrupting fintech") == "startup"
        assert self.enricher._detect_size("Founded in 2024") == "startup"
        assert self.enricher._detect_size("Early stage company, seed funded") == "startup"
        assert self.enricher._detect_size("Just closed our Series A") == "startup"

    def test_none_when_no_signals(self):
        assert self.enricher._detect_size("We build software.") is None
        assert self.enricher._detect_size("") is None

    def test_priority_enterprise_over_startup(self):
        # Enterprise keywords checked first
        text = "An enterprise startup with a global team"
        assert self.enricher._detect_size(text) == "enterprise"


class TestEnrich:
    """Tests for LeadEnricher.enrich with mocked fetcher."""

    def test_skips_when_no_website(self):
        with patch("src.direct_leads.enricher.Fetcher"):
            enricher = LeadEnricher()
        lead = DirectLead(source="test", title="Test", url="http://example.com")
        # company_website defaults to ""
        result = enricher.enrich(lead)
        assert result is lead
        assert result.contact_email == ""

    def test_enriches_email_and_phone(self):
        mock_page = MagicMock()
        mock_page.__str__ = MagicMock(return_value='<html>Email: sales@realcompany.com Phone: +1 (555) 123-4567</html>')
        mock_page.get_all_text = MagicMock(return_value="Email: sales@realcompany.com Phone: +1 (555) 123-4567")

        mock_fetcher_instance = MagicMock()
        mock_fetcher_instance.get.return_value = mock_page

        with patch("src.direct_leads.enricher.Fetcher", return_value=mock_fetcher_instance):
            enricher = LeadEnricher()

        lead = DirectLead(
            source="test",
            title="Test Lead",
            url="http://example.com/job/1",
            company_website="realcompany.com",
        )
        result = enricher.enrich(lead)
        assert result.contact_email == "sales@realcompany.com"
        # PHONE_REGEX may capture a substring; verify it's a valid phone from the text
        assert "555" in result.contact_phone
        assert "123-4567" in result.contact_phone

    def test_does_not_overwrite_existing_email(self):
        mock_page = MagicMock()
        mock_page.__str__ = MagicMock(return_value='<html>new@company.com</html>')
        mock_page.get_all_text = MagicMock(return_value="new@company.com")

        mock_fetcher_instance = MagicMock()
        mock_fetcher_instance.get.return_value = mock_page

        with patch("src.direct_leads.enricher.Fetcher", return_value=mock_fetcher_instance):
            enricher = LeadEnricher()

        lead = DirectLead(
            source="test",
            title="Test",
            url="http://example.com/job/2",
            company_website="company.io",
            contact_email="existing@company.io",
        )
        result = enricher.enrich(lead)
        assert result.contact_email == "existing@company.io"

    def test_detects_company_size(self):
        mock_page = MagicMock()
        mock_page.__str__ = MagicMock(return_value="<html>We are a startup</html>")
        mock_page.get_all_text = MagicMock(return_value="We are a startup founded in 2023")

        mock_fetcher_instance = MagicMock()
        mock_fetcher_instance.get.return_value = mock_page

        with patch("src.direct_leads.enricher.Fetcher", return_value=mock_fetcher_instance):
            enricher = LeadEnricher()

        lead = DirectLead(
            source="test",
            title="Test",
            url="http://example.com/job/3",
            company_website="startup.io",
        )
        result = enricher.enrich(lead)
        assert result.company_size == "startup"

    def test_handles_fetch_exception_gracefully(self):
        mock_fetcher_instance = MagicMock()
        mock_fetcher_instance.get.side_effect = Exception("Connection refused")

        with patch("src.direct_leads.enricher.Fetcher", return_value=mock_fetcher_instance):
            enricher = LeadEnricher()

        lead = DirectLead(
            source="test",
            title="Test",
            url="http://example.com/job/4",
            company_website="unreachable.com",
        )
        result = enricher.enrich(lead)
        assert result is lead
        assert result.contact_email == ""

    def test_enrich_many(self):
        with patch("src.direct_leads.enricher.Fetcher"):
            enricher = LeadEnricher()

        # No website means enrich is a no-op
        leads = [
            DirectLead(source="a", title="A", url="http://a.com"),
            DirectLead(source="b", title="B", url="http://b.com"),
        ]
        result = enricher.enrich_many(leads)
        assert len(result) == 2
        assert result is leads

    def test_prepends_https(self):
        mock_page = MagicMock()
        mock_page.__str__ = MagicMock(return_value="<html></html>")
        mock_page.get_all_text = MagicMock(return_value="")

        mock_fetcher_instance = MagicMock()
        mock_fetcher_instance.get.return_value = mock_page

        with patch("src.direct_leads.enricher.Fetcher", return_value=mock_fetcher_instance):
            enricher = LeadEnricher()

        lead = DirectLead(
            source="test",
            title="Test",
            url="http://example.com/job/5",
            company_website="nohttp.com",
        )
        enricher.enrich(lead)
        mock_fetcher_instance.get.assert_called_once_with("https://nohttp.com")

    def test_handles_none_page(self):
        mock_fetcher_instance = MagicMock()
        mock_fetcher_instance.get.return_value = None

        with patch("src.direct_leads.enricher.Fetcher", return_value=mock_fetcher_instance):
            enricher = LeadEnricher()

        lead = DirectLead(
            source="test",
            title="Test",
            url="http://example.com/job/6",
            company_website="empty.com",
        )
        result = enricher.enrich(lead)
        assert result.contact_email == ""
