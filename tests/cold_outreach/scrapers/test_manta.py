"""Tests for the Manta scraper (cold_outreach)."""

import pytest
from scrapling.parser import Adaptor

from src.cold_outreach.scrapers.manta import MantaScraper
from src.core.models import BusinessLead

# ---------------------------------------------------------------------------
# Realistic mock HTML that mirrors Manta search result structure
# ---------------------------------------------------------------------------

MOCK_MANTA_HTML = """
<html>
<body>
<div class="search-results">

  <div class="listing-card">
    <a href="/c/acme-roofing-austin-tx" class="listing-link">Acme Roofing</a>
    <div class="listing-details">
      <span class="phone">(512) 555-1234</span>
      <div class="address">100 Congress Ave, Austin, TX 78701</div>
      <span class="claimed-badge">CLAIMED</span>
      <span class="employees">25 employees</span>
      <span class="years">10 years in business</span>
      <p class="description">Professional roofing services for residential and commercial buildings.</p>
    </div>
  </div>

  <div class="listing-card">
    <a href="/c/best-electric-austin-tx" class="listing-link">Best Electric</a>
    <div class="listing-details">
      <span class="phone">(512) 555-5678</span>
      <div class="address">200 Lamar Blvd, Austin, TX 78702</div>
      <p class="description">Licensed electricians serving the greater Austin metropolitan area since 2005.</p>
    </div>
  </div>

  <div class="listing-card promoted">
    <a href="/c/promoted-biz-austin-tx" class="listing-link">Promoted Biz</a>
    <div class="listing-details">
      <span class="promoted-label">Promoted</span>
      <span class="phone">(512) 555-0000</span>
      <p class="description">This is a promoted listing that should be filtered out by the scraper.</p>
    </div>
  </div>

  <div class="listing-card">
    <a href="/category/roofing" class="category-link">Roofing Category</a>
  </div>

</div>
</body>
</html>
"""

MOCK_MANTA_EMPTY_HTML = """
<html>
<body>
<div class="search-results">
  <p class="no-results">No businesses found.</p>
</div>
</body>
</html>
"""

MOCK_MANTA_EXTRA_DATA_HTML = """
<html>
<body>
<div class="search-results">
  <div class="listing-card">
    <a href="/c/mega-corp-dallas-tx" class="listing-link">Mega Corp</a>
    <div class="listing-details">
      <span class="phone">(214) 555-9999</span>
      <div class="address">500 Main St</div>
      <span class="employees">150 employees</span>
      <span class="years">20 years in business</span>
      <span class="claimed-badge">CLAIMED</span>
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
    """MantaScraper with a dummy engine (not used in parse tests)."""
    return MantaScraper(engine=None)


@pytest.fixture
def manta_page():
    return Adaptor(MOCK_MANTA_HTML, auto_match=False)


@pytest.fixture
def manta_empty_page():
    return Adaptor(MOCK_MANTA_EMPTY_HTML, auto_match=False)


@pytest.fixture
def manta_extra_page():
    return Adaptor(MOCK_MANTA_EXTRA_DATA_HTML, auto_match=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMantaParseSearchResults:
    """Tests for _parse_search_results."""

    def test_extracts_leads(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        # Should find at least the two non-promoted, non-category listings
        assert len(leads) >= 2

    def test_lead_has_correct_source(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        for lead in leads:
            assert lead.source == "manta"

    def test_lead_names_extracted(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Acme Roofing" in names
        assert "Best Electric" in names

    def test_promoted_listings_skipped(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Promoted Biz" not in names

    def test_category_links_skipped(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Roofing Category" not in names

    def test_phone_extraction(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        phones = [lead.phone for lead in leads if lead.phone]
        assert len(phones) >= 1
        for phone in phones:
            assert phone.startswith("(")

    def test_detail_url_is_absolute(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        for lead in leads:
            assert lead.detail_url.startswith("https://www.manta.com")

    def test_city_and_state_set(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        for lead in leads:
            assert lead.city == "Austin"
            assert lead.state == "TX"

    def test_claimed_status(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        acme = [l for l in leads if l.name == "Acme Roofing"]
        assert len(acme) == 1
        assert acme[0].is_claimed is True

    def test_unclaimed_status(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        best = [l for l in leads if l.name == "Best Electric"]
        assert len(best) == 1
        assert best[0].is_claimed is False

    def test_empty_page_returns_no_leads(self, scraper, manta_empty_page):
        leads = scraper._parse_search_results(
            manta_empty_page, "Austin", "TX"
        )
        assert leads == []

    def test_is_sponsored_false(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        for lead in leads:
            assert lead.is_sponsored is False

    def test_returns_business_lead_instances(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        for lead in leads:
            assert isinstance(lead, BusinessLead)

    def test_extra_data_employee_count(self, scraper, manta_extra_page):
        leads = scraper._parse_search_results(
            manta_extra_page, "Dallas", "TX"
        )
        assert len(leads) >= 1
        mega = leads[0]
        assert mega.extra_data.get("employee_count") == 150

    def test_extra_data_years_in_business(self, scraper, manta_extra_page):
        leads = scraper._parse_search_results(
            manta_extra_page, "Dallas", "TX"
        )
        assert len(leads) >= 1
        mega = leads[0]
        assert mega.extra_data.get("years_in_business") == 20

    def test_no_duplicate_urls(self, scraper, manta_page):
        leads = scraper._parse_search_results(manta_page, "Austin", "TX")
        urls = [lead.detail_url for lead in leads]
        assert len(urls) == len(set(urls))


class TestMantaHelpers:
    """Tests for private helper methods."""

    def test_extract_phone_valid(self, scraper):
        assert scraper._extract_phone("Call (512) 555-1234 now") == "(512) 555-1234"

    def test_extract_phone_no_match(self, scraper):
        assert scraper._extract_phone("No phone") is None

    def test_extract_address_valid(self, scraper):
        text = "Acme Roofing\n100 Congress Ave\nAustin TX"
        assert scraper._extract_address(text) == "100 Congress Ave"

    def test_extract_address_no_match(self, scraper):
        assert scraper._extract_address("No address here") is None

    def test_unwrap_redirect_url(self, scraper):
        redirect_url = "https://www.manta.com/urlverify?redirect=https%3A%2F%2Fexample.com"
        assert scraper._unwrap_redirect_url(redirect_url) == "https://example.com"

    def test_unwrap_redirect_url_no_redirect(self, scraper):
        url = "https://www.example.com"
        assert scraper._unwrap_redirect_url(url) == url
