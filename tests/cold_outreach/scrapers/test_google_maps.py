"""Tests for the Google Maps scraper (cold_outreach)."""

import pytest
from scrapling.parser import Adaptor

from src.cold_outreach.scrapers.google_maps import GoogleMapsScraper
from src.core.models import BusinessLead

# ---------------------------------------------------------------------------
# Realistic mock HTML that mirrors Google Maps search result structure
# ---------------------------------------------------------------------------

MOCK_GMAPS_HTML = """
<html>
<body>
<div role="feed" class="m6QErb" aria-label="Results">

  <div class="Nv2PK">
    <a class="hfpxzc" href="https://www.google.com/maps/place/Joe's+Plumbing/data=!4m2" aria-label="Joe's Plumbing">
      <span class="hidden-label">Joe's Plumbing</span>
    </a>
    <div class="qBF1Pd fontHeadlineSmall">Joe's Plumbing</div>
    <span class="MW4etd">4.7</span>
    <span class="UY7F9">(215)</span>
    <div class="details-text">
      Plumber
      123 Main St
      (512) 555-1234
      Professional plumbing services serving the Austin area with expert technicians.
    </div>
  </div>

  <div class="Nv2PK">
    <a class="hfpxzc" href="https://www.google.com/maps/place/ABC+Heating/data=!4m2" aria-label="ABC Heating & Cooling">
      <span class="hidden-label">ABC Heating & Cooling</span>
    </a>
    <div class="qBF1Pd fontHeadlineSmall">ABC Heating & Cooling</div>
    <span class="MW4etd">4.2</span>
    <span class="UY7F9">(89)</span>
    <div class="details-text">
      HVAC
      456 Oak Ave
      (512) 555-5678
      Reliable heating and cooling solutions for homes and businesses in Austin.
    </div>
  </div>

  <div class="Nv2PK">
    <a class="hfpxzc" href="https://www.google.com/maps/place/Sponsored+Biz/data=!4m2" aria-label="Sponsored Biz">
      <span class="hidden-label">Sponsored Biz</span>
    </a>
    <div class="qBF1Pd fontHeadlineSmall">Sponsored Biz</div>
    <span class="ad-badge">Sponsored</span>
    <div class="details-text">
      This is a sponsored listing that should be filtered out by the scraper.
    </div>
  </div>

</div>
</body>
</html>
"""

MOCK_GMAPS_LINK_HTML = """
<html>
<body>
<div role="feed">
  <div class="result-item">
    <a href="https://www.google.com/maps/place/Link+Plumber/data=!4m2" aria-label="Link Plumber">
      Link Plumber
    </a>
    <div class="info">
      Plumber
      789 Elm Dr
      (512) 555-9999
      Affordable plumbing repair and installation services in the greater Austin area.
    </div>
  </div>
</div>
</body>
</html>
"""

MOCK_GMAPS_EMPTY_HTML = """
<html>
<body>
<div role="feed" class="m6QErb" aria-label="Results">
  <p>No results found.</p>
</div>
</body>
</html>
"""

MOCK_GMAPS_NO_RATING_HTML = """
<html>
<body>
<div role="feed">
  <div class="Nv2PK">
    <a class="hfpxzc" href="https://www.google.com/maps/place/New+Biz/data=!4m2" aria-label="New Biz">
      <span class="hidden-label">New Biz</span>
    </a>
    <div class="qBF1Pd fontHeadlineSmall">New Biz</div>
    <div class="details-text">
      Contractor
      A brand new business listing with no rating or review count available yet.
    </div>
  </div>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scraper():
    """GoogleMapsScraper with a dummy engine (not used in parse tests)."""
    return GoogleMapsScraper(engine=None)


@pytest.fixture
def gmaps_page():
    return Adaptor(MOCK_GMAPS_HTML, auto_match=False)


@pytest.fixture
def gmaps_link_page():
    return Adaptor(MOCK_GMAPS_LINK_HTML, auto_match=False)


@pytest.fixture
def gmaps_empty_page():
    return Adaptor(MOCK_GMAPS_EMPTY_HTML, auto_match=False)


@pytest.fixture
def gmaps_no_rating_page():
    return Adaptor(MOCK_GMAPS_NO_RATING_HTML, auto_match=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGoogleMapsParseSearchResults:
    """Tests for _parse_search_results."""

    def test_extracts_leads_from_containers(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        # Should find at least the two non-sponsored listings
        assert len(leads) >= 2

    def test_lead_has_correct_source(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        for lead in leads:
            assert lead.source == "google_maps"

    def test_lead_names_extracted(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Joe's Plumbing" in names
        assert "ABC Heating & Cooling" in names

    def test_sponsored_listings_skipped(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Sponsored Biz" not in names

    def test_rating_extracted(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        joes = [l for l in leads if l.name == "Joe's Plumbing"]
        assert len(joes) == 1
        assert joes[0].rating == 4.7

    def test_review_count_extracted(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        joes = [l for l in leads if l.name == "Joe's Plumbing"]
        assert len(joes) == 1
        assert joes[0].review_count == 215

    def test_phone_extraction(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        phones = [lead.phone for lead in leads if lead.phone]
        assert len(phones) >= 1
        for phone in phones:
            assert phone.startswith("(")

    def test_detail_url_present(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        for lead in leads:
            assert lead.detail_url is not None
            assert "google.com/maps/place" in lead.detail_url

    def test_city_and_state_set(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        for lead in leads:
            assert lead.city == "Austin"
            assert lead.state == "TX"

    def test_categories_extracted(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        joes = [l for l in leads if l.name == "Joe's Plumbing"]
        assert len(joes) == 1
        assert "Plumber" in joes[0].categories

    def test_empty_page_returns_no_leads(self, scraper, gmaps_empty_page):
        leads = scraper._parse_search_results(
            gmaps_empty_page, "Austin", "TX"
        )
        assert leads == []

    def test_is_sponsored_false(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        for lead in leads:
            assert lead.is_sponsored is False

    def test_returns_business_lead_instances(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        for lead in leads:
            assert isinstance(lead, BusinessLead)

    def test_no_duplicate_urls(self, scraper, gmaps_page):
        leads = scraper._parse_search_results(gmaps_page, "Austin", "TX")
        urls = [lead.detail_url for lead in leads]
        assert len(urls) == len(set(urls))

    def test_fallback_to_link_parsing(self, scraper, gmaps_link_page):
        leads = scraper._parse_search_results(
            gmaps_link_page, "Austin", "TX"
        )
        assert len(leads) >= 1
        assert leads[0].name == "Link Plumber"

    def test_no_rating_lead(self, scraper, gmaps_no_rating_page):
        leads = scraper._parse_search_results(
            gmaps_no_rating_page, "Austin", "TX"
        )
        assert len(leads) >= 1
        assert leads[0].name == "New Biz"
        assert leads[0].rating is None
        assert leads[0].review_count is None


class TestGoogleMapsHelpers:
    """Tests for private helper methods."""

    def test_extract_phone_parentheses(self):
        assert GoogleMapsScraper._extract_phone("Call (555) 123-4567 now") == "(555) 123-4567"

    def test_extract_phone_plus1(self):
        result = GoogleMapsScraper._extract_phone("Phone: +1 555-123-4567")
        assert result is not None
        assert "555" in result

    def test_extract_phone_no_match(self):
        assert GoogleMapsScraper._extract_phone("No phone") is None

    def test_extract_address_valid(self):
        text = "Joe's Plumbing\n123 Main Street\nAustin TX"
        assert GoogleMapsScraper._extract_address(text) == "123 Main Street"

    def test_extract_address_no_match(self):
        assert GoogleMapsScraper._extract_address("No address") is None

    def test_is_sponsored_true(self):
        assert GoogleMapsScraper._is_sponsored("Sponsored listing here") is True

    def test_is_sponsored_false(self):
        assert GoogleMapsScraper._is_sponsored("Regular business") is False

    def test_extract_categories(self):
        cats = GoogleMapsScraper._extract_categories("Plumber and HVAC services")
        assert "Plumber" in cats
        assert "HVAC" in cats

    def test_extract_categories_none(self):
        cats = GoogleMapsScraper._extract_categories("Some random text")
        assert cats == []
