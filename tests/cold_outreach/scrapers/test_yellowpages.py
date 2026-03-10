"""Tests for the YellowPages scraper (cold_outreach)."""

import pytest
from scrapling.parser import Adaptor

from src.cold_outreach.scrapers.yellowpages import YellowPagesScraper
from src.core.models import BusinessLead

# ---------------------------------------------------------------------------
# Realistic mock HTML that mirrors YellowPages search result structure
# ---------------------------------------------------------------------------

MOCK_YP_HTML = """
<html>
<body>
<div class="search-results organic">

  <div class="result" data-listing-id="1">
    <div class="info">
      <div class="info-primary">
        <h2 class="n">
          <a class="business-name" href="/mip/joes-plumbing-123" data-analytics="link">
            <span>Joe's Plumbing</span>
          </a>
        </h2>
        <div class="categories">
          <a href="/austin-tx/plumbing">Plumbing</a>,
          <a href="/austin-tx/water-heaters">Water Heaters</a>
        </div>
        <div class="phones phone primary">(555) 123-4567</div>
        <div class="adr">
          <div class="street-address">123 Main St</div>
          <div class="locality">Austin, TX 78701</div>
        </div>
        <div class="links">
          <a class="track-visit-website" href="https://joesplumbing.com" rel="nofollow">Website</a>
        </div>
        <p class="body">Serving the Austin area for over 20 years with expert plumbing services.</p>
      </div>
    </div>
  </div>

  <div class="result" data-listing-id="2">
    <div class="info">
      <div class="info-primary">
        <h2 class="n">
          <a class="business-name" href="/mip/abc-heating-456" data-analytics="link">
            <span>ABC Heating &amp; Cooling</span>
          </a>
        </h2>
        <div class="categories">
          <a href="/austin-tx/hvac">Heating &amp; Air Conditioning</a>
        </div>
        <div class="phones phone primary">(555) 987-6543</div>
        <div class="adr">
          <div class="street-address">456 Oak Ave</div>
          <div class="locality">Austin, TX 78702</div>
        </div>
        <p class="body">Professional HVAC installation and repair services for homes and businesses.</p>
      </div>
    </div>
  </div>

  <div class="result ad" data-listing-id="ad1">
    <div class="info">
      <div class="info-primary">
        <h2 class="n">
          <a class="business-name" href="/mip/ad-company-789" data-analytics="link">
            <span>Ad Company</span>
          </a>
        </h2>
        <div class="ad-label">Ad</div>
        <div class="phones phone primary">(555) 000-0000</div>
        <p class="body">This is a sponsored advertisement listing that appears at the top of search results.</p>
      </div>
    </div>
  </div>

</div>
</body>
</html>
"""

MOCK_YP_EMPTY_HTML = """
<html>
<body>
<div class="search-results organic">
  <p class="no-results">Sorry, no results found.</p>
</div>
</body>
</html>
"""

MOCK_YP_NO_PHONE_HTML = """
<html>
<body>
<div class="search-results organic">
  <div class="result" data-listing-id="3">
    <div class="info">
      <div class="info-primary">
        <h2 class="n">
          <a class="business-name" href="/mip/no-phone-biz-999" data-analytics="link">
            <span>No Phone Business</span>
          </a>
        </h2>
        <div class="categories">
          <a href="/austin-tx/general">General Contractor</a>
        </div>
        <div class="adr">
          <div class="street-address">789 Elm Dr</div>
          <div class="locality">Austin, TX 78703</div>
        </div>
        <p class="body">A general contracting business providing renovation and construction services in the Austin area.</p>
      </div>
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
    """YellowPagesScraper with a dummy engine (not used in parse tests)."""
    return YellowPagesScraper(engine=None)


@pytest.fixture
def yp_page():
    return Adaptor(MOCK_YP_HTML, auto_match=False)


@pytest.fixture
def yp_empty_page():
    return Adaptor(MOCK_YP_EMPTY_HTML, auto_match=False)


@pytest.fixture
def yp_no_phone_page():
    return Adaptor(MOCK_YP_NO_PHONE_HTML, auto_match=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestYellowPagesParseSearchResults:
    """Tests for _parse_search_results."""

    def test_extracts_leads_from_results(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        # Should find at least the two non-ad listings
        assert len(leads) >= 2

    def test_lead_has_correct_source(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        for lead in leads:
            assert lead.source == "yellowpages"

    def test_lead_names_extracted(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Joe's Plumbing" in names
        assert "ABC Heating & Cooling" in names

    def test_phone_extraction(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        phones = [lead.phone for lead in leads if lead.phone]
        assert len(phones) >= 1
        # Phones should be in normalized format
        for phone in phones:
            assert phone.startswith("(")

    def test_detail_url_is_absolute(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        for lead in leads:
            assert lead.detail_url.startswith("https://www.yellowpages.com")

    def test_city_and_state_set(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        for lead in leads:
            assert lead.city == "Austin"
            assert lead.state == "TX"

    def test_website_extracted_when_present(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        websites = [lead.website for lead in leads if lead.website]
        assert any("joesplumbing.com" in w for w in websites)

    def test_empty_page_returns_no_leads(self, scraper, yp_empty_page):
        leads = scraper._parse_search_results(yp_empty_page, "Austin", "TX")
        assert leads == []

    def test_lead_without_phone(self, scraper, yp_no_phone_page):
        leads = scraper._parse_search_results(
            yp_no_phone_page, "Austin", "TX"
        )
        assert len(leads) >= 1
        assert leads[0].name == "No Phone Business"
        # phone may be None or empty
        assert leads[0].phone is None or leads[0].phone == ""

    def test_is_sponsored_false(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        for lead in leads:
            assert lead.is_sponsored is False

    def test_returns_business_lead_instances(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        for lead in leads:
            assert isinstance(lead, BusinessLead)

    def test_no_duplicate_urls(self, scraper, yp_page):
        leads = scraper._parse_search_results(yp_page, "Austin", "TX")
        urls = [lead.detail_url for lead in leads]
        assert len(urls) == len(set(urls))


class TestYellowPagesHelpers:
    """Tests for private helper methods."""

    def test_extract_phone_valid(self, scraper):
        assert scraper._extract_phone("Call us (555) 123-4567 today") == "(555) 123-4567"

    def test_extract_phone_no_match(self, scraper):
        assert scraper._extract_phone("No phone here") is None

    def test_extract_address_valid(self, scraper):
        text = "Joe's Plumbing\n123 Main Street\nAustin TX"
        assert scraper._extract_address(text) == "123 Main Street"

    def test_extract_address_no_match(self, scraper):
        assert scraper._extract_address("No address") is None
