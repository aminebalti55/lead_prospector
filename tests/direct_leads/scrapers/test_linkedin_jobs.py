"""Tests for LinkedInJobsScraper (Task 18) - mock HTML parsing."""

import asyncio
from datetime import datetime

import pytest
from unittest.mock import MagicMock

from src.direct_leads.scrapers.linkedin_jobs import LinkedInJobsScraper
from src.core.scraper_engine import ScraperEngine


def _run(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_mock_card(title, href, company=None, location=None, datetime_val=None):
    """Create a mock LinkedIn job card element."""
    card = MagicMock()

    title_el = MagicMock()
    title_el.get_all_text.return_value = title

    link_el = MagicMock()
    link_el.attrib = {"href": href}
    link_el.get_all_text.return_value = title

    company_el = None
    if company:
        company_el = MagicMock()
        company_el.get_all_text.return_value = company

    loc_el = None
    if location:
        loc_el = MagicMock()
        loc_el.get_all_text.return_value = location

    time_el = None
    if datetime_val:
        time_el = MagicMock()
        time_el.attrib = {"datetime": datetime_val}

    def css_first(selector):
        if "base-search-card__title" in selector:
            return title_el if title else None
        if selector == "h3":
            return title_el if title else None
        if "base-card__full-link" in selector:
            return link_el
        if selector == "a":
            return link_el
        if "base-search-card__subtitle" in selector or "hidden-nested-link" in selector:
            return company_el
        if "job-search-card__location" in selector:
            return loc_el
        if selector == "time":
            return time_el
        return None

    card.css_first = css_first
    return card


@pytest.fixture
def engine():
    return MagicMock(spec=ScraperEngine)


@pytest.fixture
def scraper(engine):
    return LinkedInJobsScraper(engine)


class TestLinkedInParseResults:
    def test_parses_job_cards(self, scraper, engine):
        card1 = _make_mock_card(
            "Senior Python Dev", "https://linkedin.com/jobs/view/123",
            company="TechCo", location="San Francisco, CA", datetime_val="2025-01-15"
        )
        card2 = _make_mock_card(
            "Freelance Designer", "https://linkedin.com/jobs/view/456",
            company="DesignHub", location="Remote"
        )

        mock_response = MagicMock()
        mock_response.css = lambda sel: [card1, card2] if "base-card" in sel else []
        mock_response.get_all_text.return_value = "lots of job results here"

        engine.fetch_with_retry.return_value = mock_response

        leads = _run(scraper.search(["python"], max_results=20))

        assert len(leads) == 2
        assert leads[0].title == "Senior Python Dev"
        assert leads[0].source == "linkedin"
        assert leads[0].company_name == "TechCo"
        assert leads[0].location == "San Francisco, CA"
        assert leads[0].url == "https://linkedin.com/jobs/view/123"
        assert leads[1].title == "Freelance Designer"

    def test_parses_datetime(self, scraper):
        card = _make_mock_card(
            "Dev", "https://linkedin.com/jobs/view/1",
            company="Co", datetime_val="2025-06-01"
        )
        mock_page = MagicMock()
        mock_page.css = lambda sel: [card] if "base-card" in sel else []

        leads = scraper._parse_results(mock_page)
        assert leads[0].posted_date is not None
        assert leads[0].posted_date.year == 2025

    def test_skips_cards_without_title(self, scraper):
        card = MagicMock()
        card.css_first = lambda sel: None

        mock_page = MagicMock()
        mock_page.css = lambda sel: [card] if "base-card" in sel else []

        leads = scraper._parse_results(mock_page)
        assert len(leads) == 0

    def test_handles_empty_response(self, scraper, engine):
        engine.fetch_with_retry.return_value = None

        leads = _run(scraper.search(["python"], max_results=20))
        assert leads == []

    def test_handles_fetch_error_with_google_fallback(self, scraper, engine):
        # First call (LinkedIn) fails, second call (Google fallback) also fails
        engine.fetch_with_retry.side_effect = Exception("Blocked")

        leads = _run(scraper.search(["python"], max_results=20))
        assert leads == []

    def test_blocked_detection_triggers_fallback(self, scraper, engine):
        blocked_response = MagicMock()
        blocked_response.get_all_text.return_value = "Sign in Join now to see more"
        blocked_response.css = lambda sel: []

        # Google fallback also returns nothing
        engine.fetch_with_retry.return_value = blocked_response

        leads = _run(scraper.search(["python"], max_results=20))
        # Should not crash, even if fallback yields nothing
        assert isinstance(leads, list)

    def test_respects_max_results(self, scraper, engine):
        cards = [
            _make_mock_card(f"Job {i}", f"https://linkedin.com/jobs/view/{i}", company=f"Co{i}")
            for i in range(10)
        ]
        mock_response = MagicMock()
        mock_response.css = lambda sel: cards if "base-card" in sel else []
        mock_response.get_all_text.return_value = "lots of content here for jobs"

        engine.fetch_with_retry.return_value = mock_response

        leads = _run(scraper.search(["test"], max_results=3))
        assert len(leads) <= 3

    def test_fallback_css_selectors(self, scraper):
        """Test that fallback selectors (result-card) are used."""
        card = _make_mock_card("Dev", "https://linkedin.com/j/1", company="X")
        mock_page = MagicMock()

        def css_side_effect(sel):
            if "result-card" in sel:
                return [card]
            return []

        mock_page.css = css_side_effect

        leads = scraper._parse_results(mock_page)
        assert len(leads) == 1

    def test_parse_time_with_z_suffix(self, scraper):
        time_el = MagicMock()
        time_el.attrib = {"datetime": "2025-03-15T10:00:00Z"}
        result = scraper._parse_time(time_el)
        assert result is not None
        assert result.year == 2025

    def test_parse_time_empty(self, scraper):
        time_el = MagicMock()
        time_el.attrib = {"datetime": ""}
        result = scraper._parse_time(time_el)
        assert result is None

    def test_source_name(self, scraper):
        assert scraper.SOURCE_NAME == "linkedin"
