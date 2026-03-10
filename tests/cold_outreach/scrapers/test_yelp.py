"""Tests for the Yelp scraper (cold_outreach)."""

import pytest
from scrapling.parser import Adaptor

from src.cold_outreach.scrapers.yelp import YelpScraper
from src.core.models import BusinessLead

# ---------------------------------------------------------------------------
# Realistic mock HTML that mirrors Yelp search result structure
# ---------------------------------------------------------------------------

MOCK_YELP_HTML = """
<html>
<body>
<div class="search-results">

  <div class="listing" data-testid="serp-ia-card">
    <div class="listing-content">
      <a href="/biz/joes-plumbing-austin" class="business-link">
        Joe's Plumbing
      </a>
      <div class="details">
        <span class="rating">4.5 star rating</span>
        <span class="reviews">(127 reviews)</span>
        <span class="phone">(512) 555-1234</span>
        <p class="snippet">Excellent plumbing services in the Austin area with over twenty years of experience.</p>
      </div>
    </div>
  </div>

  <div class="listing" data-testid="serp-ia-card">
    <div class="listing-content">
      <a href="/biz/abc-heating-austin" class="business-link">
        ABC Heating & Cooling
      </a>
      <div class="details">
        <span class="rating">3.8 star rating</span>
        <span class="reviews">(45 reviews)</span>
        <span class="phone">(512) 555-5678</span>
        <p class="snippet">Professional HVAC installation and repair services for the Austin metro area.</p>
      </div>
    </div>
  </div>

  <div class="listing sponsored" data-testid="serp-ia-card">
    <div class="listing-content">
      <span class="ad-label">Sponsored</span>
      <a href="/biz/ad-company-austin" class="business-link">
        Sponsored Company
      </a>
      <div class="details">
        <span class="phone">(512) 555-0000</span>
        <p class="snippet">This is a sponsored advertisement listing that should be filtered out.</p>
      </div>
    </div>
  </div>

  <div class="listing" data-testid="serp-ia-card">
    <div class="listing-content">
      <a href="/adredir?redirect=http://example.com" class="business-link">
        Ad Redirect
      </a>
      <div class="details">
        <p class="snippet">This is an ad redirect link that should be filtered out by the scraper.</p>
      </div>
    </div>
  </div>

</div>
</body>
</html>
"""

MOCK_YELP_EMPTY_HTML = """
<html>
<body>
<div class="search-results">
  <p class="no-results">No results for your search.</p>
</div>
</body>
</html>
"""

MOCK_YELP_BLOCKED_HTML = """
<html>
<body>
<div class="captcha-page">
  <h1>Device verification</h1>
  <p>Please verify you're a human to continue using Yelp.</p>
</div>
</body>
</html>
"""

MOCK_YELP_NO_RATING_HTML = """
<html>
<body>
<div class="search-results">
  <div class="listing" data-testid="serp-ia-card">
    <div class="listing-content">
      <a href="/biz/new-biz-austin" class="business-link">
        New Business
      </a>
      <div class="details">
        <span class="phone">(512) 555-9999</span>
        <p class="snippet">A brand new business with no reviews or ratings yet available on Yelp.</p>
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
    """YelpScraper with a dummy engine (not used in parse tests)."""
    return YelpScraper(engine=None)


@pytest.fixture
def yelp_page():
    return Adaptor(MOCK_YELP_HTML, auto_match=False)


@pytest.fixture
def yelp_empty_page():
    return Adaptor(MOCK_YELP_EMPTY_HTML, auto_match=False)


@pytest.fixture
def yelp_blocked_page():
    return Adaptor(MOCK_YELP_BLOCKED_HTML, auto_match=False)


@pytest.fixture
def yelp_no_rating_page():
    return Adaptor(MOCK_YELP_NO_RATING_HTML, auto_match=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestYelpParseSearchResults:
    """Tests for _parse_search_results."""

    def test_extracts_leads_from_results(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        # Should find the two non-sponsored, non-adredir listings
        assert len(leads) >= 2

    def test_lead_has_correct_source(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        for lead in leads:
            assert lead.source == "yelp"

    def test_lead_names_extracted(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Joe's Plumbing" in names
        assert "ABC Heating & Cooling" in names

    def test_sponsored_listings_skipped(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Sponsored Company" not in names

    def test_adredir_links_skipped(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Ad Redirect" not in names

    def test_phone_extraction(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        phones = [lead.phone for lead in leads if lead.phone]
        assert len(phones) >= 1
        for phone in phones:
            assert phone.startswith("(")

    def test_detail_url_is_absolute(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        for lead in leads:
            assert lead.detail_url.startswith("https://www.yelp.com")

    def test_city_and_state_set(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        for lead in leads:
            assert lead.city == "Austin"
            assert lead.state == "TX"

    def test_rating_extracted(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        joes = [l for l in leads if l.name == "Joe's Plumbing"]
        assert len(joes) == 1
        assert joes[0].rating == 4.5

    def test_review_count_extracted(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        joes = [l for l in leads if l.name == "Joe's Plumbing"]
        assert len(joes) == 1
        assert joes[0].review_count == 127

    def test_empty_page_returns_no_leads(self, scraper, yelp_empty_page):
        leads = scraper._parse_search_results(yelp_empty_page, "Austin", "TX")
        assert leads == []

    def test_is_sponsored_false(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        for lead in leads:
            assert lead.is_sponsored is False

    def test_returns_business_lead_instances(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        for lead in leads:
            assert isinstance(lead, BusinessLead)

    def test_no_duplicate_urls(self, scraper, yelp_page):
        leads = scraper._parse_search_results(yelp_page, "Austin", "TX")
        urls = [lead.detail_url for lead in leads]
        assert len(urls) == len(set(urls))

    def test_no_rating_lead(self, scraper, yelp_no_rating_page):
        leads = scraper._parse_search_results(
            yelp_no_rating_page, "Austin", "TX"
        )
        assert len(leads) >= 1
        assert leads[0].name == "New Business"
        assert leads[0].rating is None
        assert leads[0].review_count is None


class TestYelpBlockingDetection:
    """Tests for blocking/CAPTCHA detection."""

    def test_is_blocked_device_verification(self, scraper):
        assert scraper._is_blocked("Device verification required") is True

    def test_is_blocked_captcha(self, scraper):
        assert scraper._is_blocked("Please verify you're a human") is True

    def test_is_blocked_unusual_traffic(self, scraper):
        assert scraper._is_blocked("unusual traffic detected") is True

    def test_is_blocked_access_denied(self, scraper):
        assert scraper._is_blocked("Access denied to this resource") is True

    def test_not_blocked_normal_page(self, scraper):
        assert scraper._is_blocked("Plumbing in Austin, TX - Yelp") is False


class TestYelpHelpers:
    """Tests for private helper methods."""

    def test_extract_phone_valid(self):
        assert YelpScraper._extract_phone("Call (555) 123-4567 today") == "(555) 123-4567"

    def test_extract_phone_no_match(self):
        assert YelpScraper._extract_phone("No phone here") is None

    def test_extract_rating_valid(self):
        assert YelpScraper._extract_rating("4.5 star rating") == 4.5

    def test_extract_rating_no_match(self):
        assert YelpScraper._extract_rating("No rating") is None

    def test_extract_review_count_valid(self):
        assert YelpScraper._extract_review_count("(127 reviews)") == 127

    def test_extract_review_count_no_match(self):
        assert YelpScraper._extract_review_count("No reviews") is None

    def test_unwrap_redirect_url(self):
        redirect_url = "https://www.yelp.com/biz_redir?url=https%3A%2F%2Fexample.com"
        assert YelpScraper._unwrap_redirect_url(redirect_url) == "https://example.com"

    def test_unwrap_redirect_url_no_redirect(self):
        url = "https://www.example.com"
        assert YelpScraper._unwrap_redirect_url(url) == url
