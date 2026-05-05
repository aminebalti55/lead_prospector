"""Tests for backend.services.opportunity_aggregator."""
from __future__ import annotations

import pytest

from src.core.models import DirectLead, Stage, OpportunityType
from backend.services.opportunity_aggregator import (
    direct_lead_to_opportunity,
    cold_row_to_opportunity,
    estimate_value_usd,
)


def test_direct_lead_to_opportunity_minimal():
    lead = DirectLead(
        source="reddit",
        title="Need a Webflow dev",
        description="Build me a landing page",
        url="https://reddit.com/r/forhire/abc",
        company_name="Acme",
        location="Remote",
        contact_email="hi@acme.io",
        relevance_score=72,
        budget_signal="$3000",
        matched_skills=["webflow", "landing-page"],
        outreach_status="new",
    )
    opp = direct_lead_to_opportunity(lead, source_file="direct_x.xlsx")

    assert opp.type == OpportunityType.DIRECT.value
    assert opp.id == lead.lead_id
    assert opp.source == "reddit"
    assert opp.title == "Need a Webflow dev"
    assert opp.score == 72
    assert opp.priority == "hot"  # >= 60
    assert opp.stage == Stage.NEW.value
    assert opp.estimated_value_usd == 3000
    assert opp.matched_skills == ["webflow", "landing-page"]
    assert opp.source_file == "direct_x.xlsx"
    assert opp.raw_lead_id == lead.lead_id


def test_priority_thresholds():
    cold_lead = DirectLead(source="reddit", url="u1", relevance_score=20)
    warm_lead = DirectLead(source="reddit", url="u2", relevance_score=40)
    hot_lead = DirectLead(source="reddit", url="u3", relevance_score=80)
    assert direct_lead_to_opportunity(cold_lead, "f").priority == "cold"
    assert direct_lead_to_opportunity(warm_lead, "f").priority == "warm"
    assert direct_lead_to_opportunity(hot_lead, "f").priority == "hot"


def test_stage_normalization_from_legacy_status():
    """Old ProcessedLead used 'queued', 'passed', 'converted' — normalize them."""
    lead = DirectLead(source="reddit", url="u", outreach_status="passed")
    assert direct_lead_to_opportunity(lead, "f").stage == Stage.LOST.value

    lead = DirectLead(source="reddit", url="u", outreach_status="converted")
    assert direct_lead_to_opportunity(lead, "f").stage == Stage.WON.value

    lead = DirectLead(source="reddit", url="u", outreach_status="queued")
    assert direct_lead_to_opportunity(lead, "f").stage == Stage.NEW.value


def test_estimate_value_from_budget_signal_with_dollar_amount():
    assert estimate_value_usd(budget_signal="$3,000", source="reddit", priority="hot") == 3000
    assert estimate_value_usd(budget_signal="around $1500", source="reddit", priority="warm") == 1500
    assert estimate_value_usd(budget_signal="2000 USD", source="reddit", priority="hot") == 2000


def test_estimate_value_fallback_by_source_and_priority():
    # No explicit dollar amount → fall back to heuristic by source + priority
    # direct sources (reddit/linkedin/etc) baseline
    assert estimate_value_usd("", "reddit", "hot") == 2500
    assert estimate_value_usd("", "reddit", "warm") == 1500
    assert estimate_value_usd("", "reddit", "cold") == 800
    # cold sources (google_maps/yelp/etc) baseline (longer sales cycle, bigger deals)
    assert estimate_value_usd("", "google_maps", "hot") == 4000
    assert estimate_value_usd("", "google_maps", "warm") == 2000
    assert estimate_value_usd("", "google_maps", "cold") == 1000


def test_cold_row_to_opportunity_minimal():
    row = {
        "Lead_ID": "abc123",
        "Business_Name": "Joe's Plumbing",
        "Niche": "plumbing",
        "City": "Austin",
        "State": "TX",
        "Phone": "555-1234",
        "Website": "https://joesplumbing.com",
        "Email": "joe@joesplumbing.com",
        "Total_Score": 65,
        "Priority": "hot",
        "Pain_Tags_Str": "no_booking_cta, slow_page",
        "Outreach_Status": "contacted",
    }
    opp = cold_row_to_opportunity(row, source_file="cold_x.xlsx")

    assert opp.type == OpportunityType.COLD.value
    assert opp.id == "abc123"
    assert opp.title == "Joe's Plumbing"
    assert opp.location == "Austin, TX"
    assert opp.contact_email == "joe@joesplumbing.com"
    assert opp.contact_phone == "555-1234"
    assert opp.url == "https://joesplumbing.com"
    assert opp.score == 65
    assert opp.priority == "hot"
    assert opp.stage == Stage.CONTACTED.value
    assert opp.pain_tags == ["no_booking_cta", "slow_page"]
    assert opp.estimated_value_usd > 0  # heuristic — should set something
