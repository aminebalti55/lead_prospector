"""Tests for IndeedScraper (Task 17) - mock HTML parsing."""

import asyncio
from datetime import datetime, timedelta

import pytest
from unittest.mock import MagicMock

from src.direct_leads.scrapers.indeed import IndeedScraper
from src.core.scraper_engine import ScraperEngine


def _run(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_mock_card(title, href, company=None, location=None, snippet=None, date_text=None):
    """Create a mock Indeed job card element."""
    card = MagicMock()

    title_el = MagicMock()
    title_el.get_all_text.return_value = title
    title_el.attrib = {"href": href}

    company_el = None
    if company:
        company_el = MagicMock()
        company_el.get_all_text.return_value = company

    loc_el = None
    if location:
        loc_el = MagicMock()
        loc_el.get_all_text.return_value = location

    desc_el = None
    if snippet:
        desc_el = MagicMock()
        desc_el.get_all_text.return_value = snippet

    date_el = None
    if date_text:
        date_el = MagicMock()
        date_el.get_all_text.return_value = date_text

    def css_first(selector):
        if "jobTitle" in selector or "jcs-JobTitle" in selector or selector == "h2 a":
            return title_el if title else None
        if "1h7lukg" in selector or "companyName" in selector or "company-name" in selector:
            return company_el
        if "1restlb" in selector or "companyLocation" in selector or "text-location" in selector:
            return loc_el
        if "9446fg" in selector or "job-snippet" in selector or "jobCardShelfContainer" in selector:
            return desc_el
        if "date" in selector or "qvloho" in selector:
            return date_el
        return None

    card.css_first = css_first
    return card


@pytest.fixture
def engine():
    return MagicMock(spec=ScraperEngine)


@pytest.fixture
def scraper(engine):
    return IndeedScraper(engine)


class TestIndeedParseResults:
    def test_parses_job_cards(self, scraper, engine):
        card1 = _make_mock_card(
            "Python Developer", "/rc/clk?jk=abc123",
            company="Acme Inc", location="Remote", snippet="Build APIs", date_text="3 days ago"
        )
        card2 = _make_mock_card(
            "React Freelancer", "/rc/clk?jk=def456",
            company="Beta Corp", location="New York, NY", snippet="Frontend work"
        )

        mock_response = MagicMock()
        mock_response.css = lambda sel: [card1, card2] if "job_seen_beacon" in sel else []
        engine.fetch_with_retry.return_value = mock_response

        leads = _run(scraper.search(["python"], max_results=20))

        assert len(leads) == 2
        assert leads[0].title == "Python Developer"
        assert leads[0].source == "indeed"
        assert leads[0].company_name == "Acme Inc"
        assert leads[0].location == "Remote"
        assert leads[0].url == "https://www.indeed.com/rc/clk?jk=abc123"
        assert leads[1].title == "React Freelancer"

    def test_constructs_relative_url(self, scraper):
        card = _make_mock_card("Dev", "/rc/clk?jk=abc", company="Co")
        mock_page = MagicMock()
        mock_page.css = lambda sel: [card] if "job_seen_beacon" in sel else []

        leads = scraper._parse_results(mock_page)
        assert leads[0].url == "https://www.indeed.com/rc/clk?jk=abc"

    def test_keeps_absolute_url(self, scraper):
        card = _make_mock_card("Dev", "https://indeed.com/viewjob?jk=abc", company="Co")
        mock_page = MagicMock()
        mock_page.css = lambda sel: [card] if "job_seen_beacon" in sel else []

        leads = scraper._parse_results(mock_page)
        assert leads[0].url == "https://indeed.com/viewjob?jk=abc"

    def test_skips_cards_without_title(self, scraper):
        card = MagicMock()
        card.css_first = lambda sel: None  # no title element

        mock_page = MagicMock()
        mock_page.css = lambda sel: [card] if "job_seen_beacon" in sel else []

        leads = scraper._parse_results(mock_page)
        assert len(leads) == 0

    def test_uses_title_as_description_fallback(self, scraper):
        card = _make_mock_card("Fullstack Dev", "/job/123", company="X Corp")
        mock_page = MagicMock()
        mock_page.css = lambda sel: [card] if "job_seen_beacon" in sel else []

        leads = scraper._parse_results(mock_page)
        assert leads[0].description == "Fullstack Dev"

    def test_handles_empty_response(self, scraper, engine):
        engine.fetch_with_retry.return_value = None

        leads = _run(scraper.search(["python"], max_results=20))
        assert leads == []

    def test_handles_fetch_error(self, scraper, engine):
        engine.fetch_with_retry.side_effect = Exception("Timeout")

        leads = _run(scraper.search(["python"], max_results=20))
        assert leads == []

    def test_respects_max_results(self, scraper, engine):
        cards = [_make_mock_card(f"Job {i}", f"/j/{i}", company=f"Co{i}") for i in range(10)]
        mock_response = MagicMock()
        mock_response.css = lambda sel: cards if "job_seen_beacon" in sel else []
        engine.fetch_with_retry.return_value = mock_response

        leads = _run(scraper.search(["test"], max_results=3))
        assert len(leads) <= 3

    def test_fallback_css_selectors(self, scraper):
        """Test that fallback selectors (resultContent) are used."""
        card = _make_mock_card("Dev", "/j/1", company="X")
        mock_page = MagicMock()

        # First selector returns empty, second returns cards
        def css_side_effect(sel):
            if "resultContent" in sel:
                return [card]
            return []

        mock_page.css = css_side_effect

        leads = scraper._parse_results(mock_page)
        assert len(leads) == 1


class TestIndeedParseDate:
    def test_parse_today(self, scraper):
        result = scraper._parse_date("Today")
        assert result is not None
        assert result.date() == datetime.now().date()

    def test_parse_just_posted(self, scraper):
        result = scraper._parse_date("Just posted")
        assert result is not None
        assert result.date() == datetime.now().date()

    def test_parse_days_ago(self, scraper):
        result = scraper._parse_date("3 days ago")
        assert result is not None
        expected = (datetime.now() - timedelta(days=3)).date()
        assert result.date() == expected

    def test_parse_hours_ago(self, scraper):
        result = scraper._parse_date("5 hours ago")
        assert result is not None
        # Should be within ~5 hours of now
        diff = datetime.now() - result
        assert 4 * 3600 <= diff.total_seconds() <= 6 * 3600

    def test_parse_empty_string(self, scraper):
        assert scraper._parse_date("") is None

    def test_parse_unknown_format(self, scraper):
        assert scraper._parse_date("sometime last week") is None

    def test_source_name(self, scraper):
        assert scraper.SOURCE_NAME == "indeed"
