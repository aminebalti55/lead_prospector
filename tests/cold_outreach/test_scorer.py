"""Tests for the cold_outreach scorer module."""

import pytest
from src.cold_outreach.scorer import (
    Priority,
    RecommendedOffer,
    ScoringResult,
    LeadScorer,
    ProcessedLead,
    create_processed_lead,
)


class TestScoringResult:
    """Tests for ScoringResult dataclass."""

    def test_defaults(self):
        result = ScoringResult()
        assert result.total_score == 0
        assert result.priority == Priority.COLD
        assert result.recommended_offer == RecommendedOffer.UNDETERMINED
        assert result.pain_tags == []
        assert result.score_breakdown == {}


class TestLeadScorer:
    """Tests for LeadScorer scoring logic."""

    def test_no_website_gives_25_points(self):
        scorer = LeadScorer()
        result = scorer.score_business(has_website=False)
        assert result.score_breakdown.get("no_website") == 25
        assert "no_website" in result.pain_tags

    def test_no_website_score_contributes_to_total(self):
        scorer = LeadScorer()
        result = scorer.score_business(has_website=False, review_count=0)
        # no_website=25 + few_reviews=5 = 30
        assert result.total_score == 30

    def test_hot_threshold(self):
        """Score >= 35 should be HOT priority."""
        scorer = LeadScorer()
        # no_website=25, low_rating=10, few_reviews=5 = 40
        result = scorer.score_business(
            has_website=False, rating=3.0, review_count=5
        )
        assert result.total_score >= 35
        assert result.priority == Priority.HOT

    def test_warm_threshold(self):
        """Score >= 25 but < 35 should be WARM."""
        scorer = LeadScorer()
        # no_website=25, review_count >= 10 so no few_reviews penalty
        result = scorer.score_business(has_website=False, review_count=15)
        assert result.total_score == 25
        assert result.priority == Priority.WARM

    def test_cold_threshold(self):
        """Score < 25 should be COLD."""
        scorer = LeadScorer()
        # Has website, no audit data, enough reviews, good rating
        result = scorer.score_business(
            has_website=True, rating=4.5, review_count=50
        )
        assert result.total_score < 25
        assert result.priority == Priority.COLD

    def test_website_audit_pain_signals(self):
        scorer = LeadScorer()
        audit = {
            "pain_signals": ["no_booking_cta", "no_contact_form", "no_ssl"]
        }
        result = scorer.score_business(
            website_audit=audit, review_count=50, rating=4.5
        )
        assert "no_booking_cta" in result.pain_tags
        assert "no_contact_form" in result.pain_tags
        assert "no_ssl" in result.pain_tags

    def test_offer_recommendation_no_website(self):
        scorer = LeadScorer()
        result = scorer.score_business(has_website=False)
        assert result.recommended_offer == RecommendedOffer.WEBSITE_REDESIGN

    def test_offer_recommendation_landing_page(self):
        scorer = LeadScorer()
        audit = {"pain_signals": ["no_booking_cta", "no_contact_form"]}
        result = scorer.score_business(
            website_audit=audit, review_count=50, rating=4.5
        )
        assert result.recommended_offer == RecommendedOffer.LANDING_PAGE

    def test_ops_pain_from_reviews(self):
        scorer = LeadScorer()
        review_analysis = {"ops_pain_count": 3, "conversion_pain_count": 0}
        result = scorer.score_business(
            review_analysis=review_analysis, review_count=50, rating=4.5
        )
        assert "ops_issues" in result.pain_tags
        assert result.ops_score == 20

    def test_few_reviews_penalty(self):
        scorer = LeadScorer()
        result = scorer.score_business(review_count=5, rating=4.5)
        assert "few_reviews" in result.pain_tags
        assert result.reputation_score == 5


class TestProcessedLead:
    """Tests for ProcessedLead dataclass."""

    def test_defaults(self):
        lead = ProcessedLead(name="Test Biz", niche="plumbing", address="123 Main St")
        assert lead.name == "Test Biz"
        assert lead.priority == "cold"
        assert lead.pain_tags == []

    def test_create_processed_lead_with_scoring(self):
        scoring = ScoringResult(
            total_score=40,
            priority=Priority.HOT,
            recommended_offer=RecommendedOffer.WEBSITE_REDESIGN,
            offer_reasoning="Needs website",
            pain_tags=["no_website"],
            website_score=25,
        )
        lead = create_processed_lead(scoring_result=scoring, niche="dental")
        assert lead.total_score == 40
        assert lead.priority == "hot"
        assert lead.recommended_offer == "website_redesign"
        assert lead.pain_tags == ["no_website"]
        assert lead.pain_tags_str == "no_website"
