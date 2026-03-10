"""Tests for the BBB scraper (cold_outreach)."""

import pytest
from scrapling.parser import Adaptor

from src.cold_outreach.scrapers.bbb import BBBScraper
from src.core.models import BusinessLead

# ---------------------------------------------------------------------------
# Realistic mock HTML that mirrors BBB search result structure
# ---------------------------------------------------------------------------

MOCK_BBB_HTML = """
<html>
<body>
<div class="search-results">

  <div class="result-item" data-id="1">
    <div class="listing-info">
      <a href="/profile/joe-s-plumbing-0123/456" class="business-link">
        Joe's Plumbing
      </a>
      <div class="details">
        <span class="rating-text">BBB Rating: A+</span>
        <span class="accreditation">BBB Accredited Business</span>
        <span class="phone">(512) 555-1234</span>
        <span class="complaints">3 complaints closed in last 3 years</span>
        <span class="started">Business Started: 2005</span>
        <p class="description">Joe's Plumbing has been serving Austin for many years with quality service and expert staff.</p>
      </div>
    </div>
  </div>

  <div class="result-item" data-id="2">
    <div class="listing-info">
      <a href="/profile/abc-heating-0456/789" class="business-link">
        ABC Heating
      </a>
      <div class="details">
        <span class="rating-text">BBB Rating: B</span>
        <span class="phone">(512) 555-5678</span>
        <p class="description">Professional HVAC services for residential and commercial properties in the greater Austin area.</p>
      </div>
    </div>
  </div>

  <div class="result-item ad" data-id="ad1">
    <div class="listing-info">
      <a href="/profile/ad-company-9999/000" class="business-link">
        advertisement: Some Ad Company
      </a>
      <div class="details">
        <span class="phone">(512) 555-0000</span>
        <p class="description">This is a sponsored advertisement listing for a fake company.</p>
      </div>
    </div>
  </div>

</div>
</body>
</html>
"""

MOCK_BBB_EMPTY_HTML = """
<html>
<body>
<div class="search-results">
  <p class="no-results">No results found for your search.</p>
</div>
</body>
</html>
"""

MOCK_BBB_ACCREDITED_HTML = """
<html>
<body>
<div class="search-results">
  <div class="result-item">
    <div class="listing-info">
      <a href="/profile/mega-corp-dallas/111" class="business-link">
        Mega Corp
      </a>
      <div class="details">
        <span class="rating-text">BBB Rating: A-</span>
        <span class="accreditation">Accredited</span>
        <span class="phone">(214) 555-9999</span>
        <span class="complaints">7 complaints closed in last 3 years</span>
        <span class="started">Business Started: 1998</span>
        <p class="description">Mega Corp is a large company with many years of experience in the Dallas area.</p>
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
    """BBBScraper with a dummy engine (not used in parse tests)."""
    return BBBScraper(engine=None)


@pytest.fixture
def bbb_page():
    return Adaptor(MOCK_BBB_HTML, auto_match=False)


@pytest.fixture
def bbb_empty_page():
    return Adaptor(MOCK_BBB_EMPTY_HTML, auto_match=False)


@pytest.fixture
def bbb_accredited_page():
    return Adaptor(MOCK_BBB_ACCREDITED_HTML, auto_match=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBBBParseSearchResults:
    """Tests for _parse_search_results."""

    def test_extracts_leads_from_results(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        # Should find at least the two non-ad listings
        assert len(leads) >= 2

    def test_lead_has_correct_source(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        for lead in leads:
            assert lead.source == "bbb"

    def test_lead_names_extracted(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert "Joe's Plumbing" in names
        assert "ABC Heating" in names

    def test_advertisement_listings_skipped(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        names = [lead.name for lead in leads]
        assert not any("ad company" in n.lower() for n in names)

    def test_phone_extraction(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        phones = [lead.phone for lead in leads if lead.phone]
        assert len(phones) >= 1
        for phone in phones:
            assert phone.startswith("(")

    def test_detail_url_is_absolute(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        for lead in leads:
            assert lead.detail_url.startswith("https://www.bbb.org")

    def test_city_and_state_set(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        for lead in leads:
            assert lead.city == "Austin"
            assert lead.state == "TX"

    def test_bbb_rating_extracted(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        joes = [l for l in leads if l.name == "Joe's Plumbing"]
        assert len(joes) == 1
        assert joes[0].extra_data.get("bbb_rating") == "A+"

    def test_accreditation_extracted(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        joes = [l for l in leads if l.name == "Joe's Plumbing"]
        assert len(joes) == 1
        assert joes[0].extra_data.get("bbb_accredited") is True

    def test_not_accredited(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        abc = [l for l in leads if l.name == "ABC Heating"]
        assert len(abc) == 1
        assert abc[0].extra_data.get("bbb_accredited") is False

    def test_complaints_extracted(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        joes = [l for l in leads if l.name == "Joe's Plumbing"]
        assert len(joes) == 1
        assert joes[0].extra_data.get("complaints_last_3_years") == 3

    def test_year_started_extracted(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        joes = [l for l in leads if l.name == "Joe's Plumbing"]
        assert len(joes) == 1
        assert joes[0].extra_data.get("year_started") == 2005
        assert joes[0].extra_data.get("years_in_business") is not None

    def test_empty_page_returns_no_leads(self, scraper, bbb_empty_page):
        leads = scraper._parse_search_results(bbb_empty_page, "Austin", "TX")
        assert leads == []

    def test_is_sponsored_false(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        for lead in leads:
            assert lead.is_sponsored is False

    def test_returns_business_lead_instances(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        for lead in leads:
            assert isinstance(lead, BusinessLead)

    def test_no_duplicate_urls(self, scraper, bbb_page):
        leads = scraper._parse_search_results(bbb_page, "Austin", "TX")
        urls = [lead.detail_url for lead in leads]
        assert len(urls) == len(set(urls))

    def test_accredited_page_extra_data(self, scraper, bbb_accredited_page):
        leads = scraper._parse_search_results(
            bbb_accredited_page, "Dallas", "TX"
        )
        assert len(leads) >= 1
        mega = leads[0]
        assert mega.extra_data.get("bbb_rating") == "A-"
        assert mega.extra_data.get("bbb_accredited") is True
        assert mega.extra_data.get("complaints_last_3_years") == 7
        assert mega.extra_data.get("year_started") == 1998


class TestBBBHelpers:
    """Tests for private helper methods."""

    def test_extract_phone_valid(self):
        assert BBBScraper._extract_phone("Call (555) 123-4567 today") == "(555) 123-4567"

    def test_extract_phone_no_match(self):
        assert BBBScraper._extract_phone("No phone here") is None

    def test_extract_bbb_rating_aplus(self):
        assert BBBScraper._extract_bbb_rating("BBB Rating: A+") == "A+"

    def test_extract_bbb_rating_b(self):
        assert BBBScraper._extract_bbb_rating("BBB Rating: B") == "B"

    def test_extract_bbb_rating_no_match(self):
        assert BBBScraper._extract_bbb_rating("No rating") is None

    def test_extract_complaints(self):
        text = "5 complaints closed in last 3 years"
        assert BBBScraper._extract_complaints(text) == 5

    def test_extract_complaints_no_match(self):
        assert BBBScraper._extract_complaints("No complaints info") is None

    def test_extract_year_started(self):
        assert BBBScraper._extract_year_started("Business Started: 2010") == 2010

    def test_extract_year_started_no_match(self):
        assert BBBScraper._extract_year_started("No year info") is None
