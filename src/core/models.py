"""
Core data models for Lead Prospector.

Centralizes all lead-related dataclasses so every module imports from one place.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OutreachStatus(str, Enum):
    """Outreach pipeline stages."""

    new = "new"
    queued = "queued"
    contacted = "contacted"
    replied = "replied"
    meeting = "meeting"
    converted = "converted"
    passed = "passed"


# ---------------------------------------------------------------------------
# BusinessLead  (migrated from src/scrapers/base.py)
# ---------------------------------------------------------------------------

@dataclass
class BusinessLead:
    """Standardized business lead data structure."""

    # Required fields
    source: str  # google_maps, yelp, yellowpages, bbb, manta
    name: str
    city: str
    state: str

    # Contact info
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    email_source: Optional[str] = None  # scraper, website, google_search, guessed

    # Ratings and reviews
    rating: Optional[float] = None
    review_count: Optional[int] = None

    # Business info
    categories: List[str] = field(default_factory=list)
    is_claimed: bool = False
    is_sponsored: bool = False

    # URLs
    detail_url: Optional[str] = None

    # Source-specific fields (BBB rating, years in business, etc.)
    extra_data: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "source": self.source,
            "name": self.name,
            "phone": self.phone,
            "website": self.website,
            "address": self.address,
            "email": self.email,
            "email_source": self.email_source,
            "city": self.city,
            "state": self.state,
            "rating": self.rating,
            "review_count": self.review_count,
            "categories": ", ".join(self.categories),
            "is_claimed": self.is_claimed,
            "is_sponsored": self.is_sponsored,
            "detail_url": self.detail_url,
            "scraped_at": self.scraped_at.isoformat(),
            **self.extra_data,
        }

    @staticmethod
    def clean_phone(phone: Optional[str]) -> Optional[str]:
        """Normalize phone number format."""
        if not phone:
            return None
        # Remove all non-digit characters
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == "1":
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        return phone

    @staticmethod
    def clean_rating(rating_str: Optional[str]) -> Optional[float]:
        """Parse rating string to float."""
        if not rating_str:
            return None
        try:
            # Handle locale-specific formats (4,8 vs 4.8)
            cleaned = rating_str.replace(",", ".").strip()
            # Extract first number
            match = re.search(r"(\d+\.?\d*)", cleaned)
            if match:
                return float(match.group(1))
            return None
        except ValueError:
            return None

    @staticmethod
    def clean_review_count(count_str: Optional[str]) -> Optional[int]:
        """Parse review count string to int."""
        if not count_str:
            return None
        try:
            # Extract digits only
            digits = "".join(c for c in count_str if c.isdigit())
            return int(digits) if digits else None
        except ValueError:
            return None


# ---------------------------------------------------------------------------
# ProcessedLead  (migrated from src/scoring/scorer.py, with CRM fields)
# ---------------------------------------------------------------------------

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

    # CRM fields
    outreach_status: str = "new"
    notes: str = ""
    owner: str = ""
    last_contacted: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None


# ---------------------------------------------------------------------------
# DirectLead  (new — for direct/freelance leads)
# ---------------------------------------------------------------------------

@dataclass
class DirectLead:
    """A lead sourced from job boards, RFP sites, or similar direct channels."""

    # Identity (lead_id computed in __post_init__)
    lead_id: str = field(init=False)

    source: str = ""
    title: str = ""
    description: str = ""
    url: str = ""
    posted_date: Optional[datetime] = None

    # Company info
    company_name: str = ""
    company_website: str = ""
    company_size: str = ""
    location: str = ""

    # Contact
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""

    # Scoring / signals
    relevance_score: int = 0
    budget_signal: str = ""
    urgency_signal: str = ""
    matched_skills: List[str] = field(default_factory=list)

    # Pipeline
    outreach_status: str = "new"
    notes: str = ""

    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        raw = f"{self.source}|{self.url}"
        self.lead_id = hashlib.sha1(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Opportunity (unified shape for the Pulse UI)
# ---------------------------------------------------------------------------


class Stage(str, Enum):
    NEW = "new"
    RESEARCHING = "researching"
    CONTACTED = "contacted"
    REPLIED = "replied"
    MEETING = "meeting"
    WON = "won"
    LOST = "lost"


class OpportunityType(str, Enum):
    DIRECT = "direct"  # job/gig from Reddit/LinkedIn/Indeed/Twitter/Clutch/GoodFirms
    COLD = "cold"      # local business prospect from Google Maps/Yelp/BBB/YellowPages/Manta


@dataclass
class Opportunity:
    """Unified opportunity used by the new Pulse UI. Read-only projection
    over ProcessedLead (cold) and DirectLead (direct)."""

    id: str
    type: str          # OpportunityType value
    source: str        # "reddit" | "linkedin" | "google_maps" | ...
    title: str
    description: str
    url: str
    posted_date: Optional[str] = None  # ISO date string
    company_name: str = ""
    location: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    score: int = 0                  # 0-100, normalized
    priority: str = "cold"          # "hot" | "warm" | "cold"
    stage: str = Stage.NEW.value
    estimated_value_usd: int = 0    # heuristic dollar estimate
    matched_skills: List[str] = field(default_factory=list)
    budget_signal: str = ""
    urgency_signal: str = ""
    pain_tags: List[str] = field(default_factory=list)
    notes: str = ""
    source_file: str = ""           # which Excel file this came from (for write-back)
    raw_lead_id: str = ""           # original Lead_ID in the source file
