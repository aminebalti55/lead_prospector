"""
Scoring and Prioritization Engine
Scores businesses based on pain signals and recommends offers.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import settings

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Lead priority levels."""

    HOT = "hot"  # High score - immediate outreach opportunity
    WARM = "warm"  # Medium score - good prospect
    COLD = "cold"  # Low score - may not need services


class RecommendedOffer(Enum):
    """Recommended service offerings."""

    LANDING_PAGE = "landing_page"  # High-converting landing page
    OPS_TOOL = "ops_tool"  # Internal operations tool
    BOTH = "both"  # Both services
    WEBSITE_REDESIGN = "website_redesign"  # Full website redesign
    UNDETERMINED = "undetermined"  # Needs more analysis


@dataclass
class ScoringResult:
    """Results from scoring a business."""

    total_score: int = 0
    priority: Priority = Priority.COLD
    recommended_offer: RecommendedOffer = RecommendedOffer.UNDETERMINED

    # Component scores
    website_score: int = 0
    conversion_score: int = 0
    ops_score: int = 0
    reputation_score: int = 0

    # Pain tags for quick reference
    pain_tags: list = field(default_factory=list)

    # Detailed reasoning
    score_breakdown: dict = field(default_factory=dict)
    offer_reasoning: str = ""


class LeadScorer:
    """Scores and prioritizes leads based on pain signals."""

    def __init__(self):
        self.weights = settings.scoring.weights
        self.high_threshold = settings.scoring.high_priority_threshold
        self.medium_threshold = settings.scoring.medium_priority_threshold

    def score_business(
        self,
        website_audit: Optional[dict] = None,
        review_analysis: Optional[dict] = None,
        rating: Optional[float] = None,
        review_count: int = 0,
        has_website: bool = True,
    ) -> ScoringResult:
        """
        Score a business based on all available data.

        Args:
            website_audit: Results from WebsiteAuditResult (as dict)
            review_analysis: Results from ReviewAnalyzer
            rating: Business rating (1-5)
            review_count: Number of reviews
            has_website: Whether business has a website

        Returns:
            ScoringResult with scores and recommendations
        """
        result = ScoringResult()
        breakdown = {}

        # === WEBSITE SIGNALS ===
        if not has_website:
            score = self.weights["no_website"]
            result.website_score += score
            breakdown["no_website"] = score
            result.pain_tags.append("no_website")

        elif website_audit:
            pain_signals = website_audit.get("pain_signals", [])

            # No booking CTA
            if "no_booking_cta" in pain_signals:
                score = self.weights["no_booking_cta"]
                result.conversion_score += score
                breakdown["no_booking_cta"] = score
                result.pain_tags.append("no_booking_cta")

            # No contact form
            if "no_contact_form" in pain_signals:
                score = self.weights["no_contact_form"]
                result.conversion_score += score
                breakdown["no_contact_form"] = score
                result.pain_tags.append("no_contact_form")

            # Slow page load
            if "slow_page_load" in pain_signals:
                score = self.weights["slow_page_speed"]
                result.website_score += score
                breakdown["slow_page_load"] = score
                result.pain_tags.append("slow_website")

            # Not mobile friendly
            if "not_mobile_friendly" in pain_signals:
                score = self.weights["not_mobile_friendly"]
                result.website_score += score
                breakdown["not_mobile_friendly"] = score
                result.pain_tags.append("not_mobile_friendly")

            # No SSL
            if "no_ssl" in pain_signals:
                score = self.weights["no_ssl"]
                result.website_score += score
                breakdown["no_ssl"] = score
                result.pain_tags.append("no_ssl")

            # Website unreachable
            if "website_unreachable" in pain_signals:
                score = self.weights["no_website"]
                result.website_score += score
                breakdown["website_unreachable"] = score
                result.pain_tags.append("website_down")

        # === REVIEW SIGNALS ===
        if review_analysis:
            # Ops pain in reviews
            ops_pain = review_analysis.get("ops_pain_count", 0)
            if ops_pain >= 2:
                score = self.weights["ops_pain_reviews"]
                result.ops_score += score
                breakdown["ops_pain_reviews"] = score
                result.pain_tags.append("ops_issues")
            elif ops_pain == 1:
                score = self.weights["ops_pain_reviews"] // 2
                result.ops_score += score
                breakdown["ops_pain_reviews"] = score

            # Conversion pain in reviews
            conv_pain = review_analysis.get("conversion_pain_count", 0)
            if conv_pain >= 1:
                score = self.weights["conversion_pain_reviews"]
                result.conversion_score += score
                breakdown["conversion_pain_reviews"] = score
                result.pain_tags.append("conversion_issues")

        # === REPUTATION SIGNALS ===
        # Low rating
        if rating is not None and rating < 4.0:
            score = self.weights["low_rating"]
            result.reputation_score += score
            breakdown["low_rating"] = score
            if rating < 3.5:
                result.pain_tags.append("low_rating")

        # Few reviews (may indicate new business or low visibility)
        if review_count < 10:
            score = self.weights["few_reviews"]
            result.reputation_score += score
            breakdown["few_reviews"] = score
            result.pain_tags.append("few_reviews")

        # === CALCULATE TOTALS ===
        result.total_score = (
            result.website_score
            + result.conversion_score
            + result.ops_score
            + result.reputation_score
        )
        result.score_breakdown = breakdown

        # === DETERMINE PRIORITY ===
        if result.total_score >= self.high_threshold:
            result.priority = Priority.HOT
        elif result.total_score >= self.medium_threshold:
            result.priority = Priority.WARM
        else:
            result.priority = Priority.COLD

        # === RECOMMEND OFFER ===
        result.recommended_offer, result.offer_reasoning = self._recommend_offer(result)

        return result

    def _recommend_offer(self, result: ScoringResult) -> tuple[RecommendedOffer, str]:
        """Determine the best offer based on pain signals."""

        conversion_heavy = result.conversion_score >= 20
        ops_heavy = result.ops_score >= 15
        website_heavy = result.website_score >= 20

        # Both conversion and ops issues
        if conversion_heavy and ops_heavy:
            return (
                RecommendedOffer.BOTH,
                "Shows both lead capture gaps and operational inefficiencies. "
                "Could benefit from landing page AND internal tools.",
            )

        # Primary conversion issues
        if conversion_heavy or "no_booking_cta" in result.pain_tags:
            return (
                RecommendedOffer.LANDING_PAGE,
                "Missing clear call-to-actions or lead capture. "
                "A high-converting landing page would help capture more leads.",
            )

        # Primary ops issues
        if ops_heavy:
            return (
                RecommendedOffer.OPS_TOOL,
                "Reviews mention scheduling, response, or follow-up issues. "
                "An internal ops tool could streamline their operations.",
            )

        # Major website issues
        if website_heavy or "no_website" in result.pain_tags:
            return (
                RecommendedOffer.WEBSITE_REDESIGN,
                "Significant website issues or no website at all. "
                "Needs a complete web presence solution.",
            )

        # Default based on tags
        if any(
            tag in result.pain_tags for tag in ["no_contact_form", "no_booking_cta"]
        ):
            return (
                RecommendedOffer.LANDING_PAGE,
                "Could improve lead capture with dedicated landing page.",
            )

        if any(tag in result.pain_tags for tag in ["ops_issues"]):
            return (
                RecommendedOffer.OPS_TOOL,
                "May benefit from better operational tools.",
            )

        return (
            RecommendedOffer.UNDETERMINED,
            "Insufficient signals to make a strong recommendation. "
            "May require manual review.",
        )


@dataclass
class ProcessedLead:
    """A fully processed and scored lead."""

    # Basic info
    name: str
    niche: str
    address: str
    city: str = ""
    state: str = ""
    phone: str = ""
    website: str = ""

    # Email info
    email: str = ""
    email_source: str = ""  # scraper, website, google_search, guessed
    email_confidence: str = ""  # high, medium, low

    # Source info
    source: str = ""  # google_places, yelp, or both
    google_place_id: str = ""
    yelp_id: str = ""
    yelp_url: str = ""

    # Ratings
    google_rating: Optional[float] = None
    google_review_count: int = 0
    yelp_rating: Optional[float] = None
    yelp_review_count: int = 0

    # Scoring
    total_score: int = 0
    priority: str = "cold"
    recommended_offer: str = "undetermined"
    offer_reasoning: str = ""

    # Pain signals
    pain_tags: list = field(default_factory=list)
    pain_tags_str: str = ""  # Comma-separated for CSV

    # Audit details
    has_ssl: bool = False
    has_booking_cta: bool = False
    has_contact_form: bool = False
    is_mobile_friendly: bool = True
    page_load_time_ms: Optional[int] = None

    # Review insights
    ops_pain_count: int = 0
    conversion_pain_count: int = 0
    negative_review_count: int = 0

    # Score breakdown
    website_score: int = 0
    conversion_score: int = 0
    ops_score: int = 0
    reputation_score: int = 0


def create_processed_lead(
    google_business=None,
    yelp_business=None,
    website_audit=None,
    review_analysis=None,
    scoring_result=None,
    niche: str = "",
) -> ProcessedLead:
    """
    Create a ProcessedLead from various data sources.

    Merges data from Google Places and Yelp when both are available.
    """
    lead = ProcessedLead(name="", niche=niche, address="")

    # Merge Google data
    if google_business:
        lead.name = google_business.name
        lead.address = google_business.address
        lead.phone = google_business.phone or ""
        lead.website = google_business.website or ""
        lead.google_place_id = google_business.place_id
        lead.google_rating = google_business.rating
        lead.google_review_count = google_business.review_count
        lead.source = "google_places"

    # Merge Yelp data (may add or override)
    if yelp_business:
        if not lead.name:
            lead.name = yelp_business.name
        if not lead.address:
            lead.address = yelp_business.address
        lead.city = yelp_business.city
        lead.state = yelp_business.state
        if not lead.phone:
            lead.phone = yelp_business.display_phone or yelp_business.phone or ""
        lead.yelp_id = yelp_business.yelp_id
        lead.yelp_url = yelp_business.yelp_url
        lead.yelp_rating = yelp_business.rating
        lead.yelp_review_count = yelp_business.review_count

        if lead.source:
            lead.source = "both"
        else:
            lead.source = "yelp"

    # Add website audit data
    if website_audit:
        if isinstance(website_audit, dict):
            lead.has_ssl = website_audit.get("has_ssl", False)
            lead.has_booking_cta = website_audit.get("has_booking_cta", False)
            lead.has_contact_form = website_audit.get("has_contact_form", False)
            lead.is_mobile_friendly = website_audit.get("is_mobile_friendly", True)
            lead.page_load_time_ms = website_audit.get("page_load_time_ms")
        else:
            lead.has_ssl = website_audit.has_ssl
            lead.has_booking_cta = website_audit.has_booking_cta
            lead.has_contact_form = website_audit.has_contact_form
            lead.is_mobile_friendly = website_audit.is_mobile_friendly
            lead.page_load_time_ms = website_audit.page_load_time_ms

    # Add review analysis data
    if review_analysis:
        lead.ops_pain_count = review_analysis.get("ops_pain_count", 0)
        lead.conversion_pain_count = review_analysis.get("conversion_pain_count", 0)
        lead.negative_review_count = review_analysis.get("negative_reviews", 0)

    # Add scoring data
    if scoring_result:
        lead.total_score = scoring_result.total_score
        lead.priority = scoring_result.priority.value
        lead.recommended_offer = scoring_result.recommended_offer.value
        lead.offer_reasoning = scoring_result.offer_reasoning
        lead.pain_tags = scoring_result.pain_tags
        lead.pain_tags_str = ", ".join(scoring_result.pain_tags)
        lead.website_score = scoring_result.website_score
        lead.conversion_score = scoring_result.conversion_score
        lead.ops_score = scoring_result.ops_score
        lead.reputation_score = scoring_result.reputation_score

    return lead
