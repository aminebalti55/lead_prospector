"""Tests for the cold_outreach auditor module."""

import pytest
from src.cold_outreach.auditor import WebsiteAuditResult, ReviewAnalyzer


class TestWebsiteAuditResult:
    """Tests for WebsiteAuditResult dataclass."""

    def test_default_values(self):
        result = WebsiteAuditResult(url="https://example.com")
        assert result.url == "https://example.com"
        assert result.is_reachable is False
        assert result.has_ssl is False
        assert result.has_booking_cta is False
        assert result.has_contact_form is False
        assert result.is_mobile_friendly is True
        assert result.page_load_time_ms is None
        assert result.pain_signals == []
        assert result.error is None

    def test_custom_values(self):
        result = WebsiteAuditResult(
            url="https://test.com",
            is_reachable=True,
            has_ssl=True,
            has_booking_cta=True,
            page_load_time_ms=1200,
        )
        assert result.is_reachable is True
        assert result.has_ssl is True
        assert result.has_booking_cta is True
        assert result.page_load_time_ms == 1200

    def test_pain_signals_independent_per_instance(self):
        """Ensure pain_signals list is not shared between instances."""
        r1 = WebsiteAuditResult(url="https://a.com")
        r2 = WebsiteAuditResult(url="https://b.com")
        r1.pain_signals.append("no_ssl")
        assert r2.pain_signals == []


class TestReviewAnalyzer:
    """Tests for ReviewAnalyzer."""

    def test_empty_reviews(self):
        analyzer = ReviewAnalyzer()
        result = analyzer.analyze([])
        assert result["ops_pain_count"] == 0
        assert result["conversion_pain_count"] == 0
        assert result["negative_reviews"] == 0
        assert result["total_analyzed"] == 0

    def test_ops_pain_detection(self):
        analyzer = ReviewAnalyzer()
        reviews = [
            "They never called back after my first inquiry.",
            "Great service, very professional.",
            "Poor communication and showed up late.",
        ]
        result = analyzer.analyze(reviews)
        assert result["ops_pain_count"] == 2
        assert result["total_analyzed"] == 3

    def test_conversion_pain_detection(self):
        analyzer = ReviewAnalyzer()
        reviews = [
            "They have no website, hard to find information.",
            "Couldn't find any prices listed.",
            "Beautiful office and friendly staff.",
        ]
        result = analyzer.analyze(reviews)
        assert result["conversion_pain_count"] == 2
        assert result["total_analyzed"] == 3

    def test_mixed_pain_signals(self):
        analyzer = ReviewAnalyzer()
        reviews = [
            "Never called back and their website down constantly.",
            "Good work but outdated website.",
        ]
        result = analyzer.analyze(reviews)
        # "never called back" is ops, "website down" is conversion
        assert result["ops_pain_count"] >= 1
        assert result["conversion_pain_count"] >= 1

    def test_negative_reviews_always_zero(self):
        """The simplified ReviewAnalyzer does not count negative reviews."""
        analyzer = ReviewAnalyzer()
        reviews = ["Terrible service!", "Worst experience ever!"]
        result = analyzer.analyze(reviews)
        assert result["negative_reviews"] == 0
