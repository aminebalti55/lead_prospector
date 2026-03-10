"""Tests for the cold outreach ColdOutreachPipeline module."""

import pytest

from src.core.models import BusinessLead
from src.cold_outreach.pipeline import ColdOutreachPipeline


@pytest.fixture
def pipeline():
    """Create a ColdOutreachPipeline instance for unit tests."""
    return ColdOutreachPipeline(engine=None)


# ---------------------------------------------------------------------------
# _parse_location
# ---------------------------------------------------------------------------

class TestParseLocation:
    """Tests for ColdOutreachPipeline._parse_location."""

    def test_city_and_state(self, pipeline):
        city, state = pipeline._parse_location("Austin, TX")
        assert city == "Austin"
        assert state == "TX"

    def test_city_state_with_extra_spaces(self, pipeline):
        city, state = pipeline._parse_location("  Houston ,  TX  ")
        assert city == "Houston"
        assert state == "TX"

    def test_city_only(self, pipeline):
        city, state = pipeline._parse_location("Chicago")
        assert city == "Chicago"
        assert state == ""

    def test_multi_word_city(self, pipeline):
        city, state = pipeline._parse_location("San Francisco, CA")
        assert city == "San Francisco"
        assert state == "CA"

    def test_empty_string(self, pipeline):
        city, state = pipeline._parse_location("")
        assert city == ""
        assert state == ""

    def test_multiple_commas(self, pipeline):
        city, state = pipeline._parse_location("Portland, OR, USA")
        assert city == "Portland"
        assert state == "OR"


# ---------------------------------------------------------------------------
# _deduplicate
# ---------------------------------------------------------------------------

class TestDeduplicate:
    """Tests for ColdOutreachPipeline._deduplicate."""

    def _make_lead(self, name="Biz", city="Austin", state="TX", sponsored=False):
        return BusinessLead(
            source="google_maps",
            name=name,
            city=city,
            state=state,
            is_sponsored=sponsored,
        )

    def test_removes_exact_duplicates(self, pipeline):
        leads = [
            self._make_lead("Acme Plumbing", "Austin", "TX"),
            self._make_lead("Acme Plumbing", "Austin", "TX"),
        ]
        result = pipeline._deduplicate(leads, existing=set())
        assert len(result) == 1
        assert result[0].name == "Acme Plumbing"

    def test_case_insensitive_dedup(self, pipeline):
        leads = [
            self._make_lead("ACME PLUMBING", "AUSTIN", "TX"),
            self._make_lead("acme plumbing", "austin", "tx"),
        ]
        result = pipeline._deduplicate(leads, existing=set())
        assert len(result) == 1

    def test_strips_whitespace_in_dedup(self, pipeline):
        leads = [
            self._make_lead("  Acme Plumbing  ", " Austin ", " TX "),
            self._make_lead("Acme Plumbing", "Austin", "TX"),
        ]
        result = pipeline._deduplicate(leads, existing=set())
        assert len(result) == 1

    def test_different_names_kept(self, pipeline):
        leads = [
            self._make_lead("Acme Plumbing", "Austin", "TX"),
            self._make_lead("Bob's Plumbing", "Austin", "TX"),
        ]
        result = pipeline._deduplicate(leads, existing=set())
        assert len(result) == 2

    def test_different_cities_kept(self, pipeline):
        leads = [
            self._make_lead("Acme Plumbing", "Austin", "TX"),
            self._make_lead("Acme Plumbing", "Houston", "TX"),
        ]
        result = pipeline._deduplicate(leads, existing=set())
        assert len(result) == 2

    def test_filters_sponsored(self, pipeline):
        leads = [
            self._make_lead("Real Biz", sponsored=False),
            self._make_lead("Sponsored Biz", sponsored=True),
        ]
        result = pipeline._deduplicate(leads, existing=set())
        assert len(result) == 1
        assert result[0].name == "Real Biz"

    def test_respects_existing_set(self, pipeline):
        existing = {"acme plumbing|austin|tx"}
        leads = [
            self._make_lead("Acme Plumbing", "Austin", "TX"),
            self._make_lead("New Business", "Austin", "TX"),
        ]
        result = pipeline._deduplicate(leads, existing)
        assert len(result) == 1
        assert result[0].name == "New Business"

    def test_empty_leads(self, pipeline):
        result = pipeline._deduplicate([], existing=set())
        assert result == []

    def test_all_sponsored_returns_empty(self, pipeline):
        leads = [
            self._make_lead("A", sponsored=True),
            self._make_lead("B", sponsored=True),
        ]
        result = pipeline._deduplicate(leads, existing=set())
        assert result == []
