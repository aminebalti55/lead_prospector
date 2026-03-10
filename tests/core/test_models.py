"""Tests for src.core.models."""

from datetime import datetime

from src.core.models import (
    BusinessLead,
    DirectLead,
    OutreachStatus,
    ProcessedLead,
)


def test_business_lead_to_dict():
    """to_dict returns all expected keys with correct values."""
    lead = BusinessLead(
        source="google_maps",
        name="Acme Plumbing",
        city="Austin",
        state="TX",
        phone="(512) 555-1234",
        website="https://acme.com",
        categories=["plumber", "contractor"],
        rating=4.5,
        review_count=42,
    )
    d = lead.to_dict()

    assert d["source"] == "google_maps"
    assert d["name"] == "Acme Plumbing"
    assert d["city"] == "Austin"
    assert d["state"] == "TX"
    assert d["phone"] == "(512) 555-1234"
    assert d["website"] == "https://acme.com"
    assert d["categories"] == "plumber, contractor"
    assert d["rating"] == 4.5
    assert d["review_count"] == 42
    assert d["is_claimed"] is False
    assert d["is_sponsored"] is False
    assert "scraped_at" in d


def test_direct_lead_id_computed():
    """lead_id should be a 40-character hex SHA-1 digest."""
    lead = DirectLead(source="upwork", url="https://upwork.com/job/123")
    assert len(lead.lead_id) == 40
    assert all(c in "0123456789abcdef" for c in lead.lead_id)


def test_direct_lead_id_deterministic():
    """Same source+url must produce the same lead_id."""
    a = DirectLead(source="upwork", url="https://upwork.com/job/123")
    b = DirectLead(source="upwork", url="https://upwork.com/job/123")
    assert a.lead_id == b.lead_id

    # Different URL should differ
    c = DirectLead(source="upwork", url="https://upwork.com/job/999")
    assert a.lead_id != c.lead_id


def test_outreach_status_values():
    """OutreachStatus enum should contain exactly the expected members."""
    expected = {"new", "queued", "contacted", "replied", "meeting", "converted", "passed"}
    actual = {s.value for s in OutreachStatus}
    assert actual == expected


def test_processed_lead_has_crm_fields():
    """ProcessedLead should expose the new CRM tracking fields."""
    lead = ProcessedLead(name="Test Biz", niche="plumbing", address="123 Main St")

    assert lead.outreach_status == "new"
    assert lead.notes == ""
    assert lead.owner == ""
    assert lead.last_contacted is None
    assert lead.follow_up_date is None
