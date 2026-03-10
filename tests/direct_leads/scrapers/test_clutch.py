"""Tests for ClutchScraper (Task 19) - mock HTML parsing."""

import asyncio
import pytest
from unittest.mock import MagicMock

from src.direct_leads.scrapers.clutch import ClutchScraper, BASE_URL
from src.core.scraper_engine import ScraperEngine


def _run(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_mock_card(company_name, description, location, href):
    """Create a mock card element with nested CSS selectors."""
    card = MagicMock()

    name_el = MagicMock()
    name_el.text = company_name
    name_el.attrib = {"href": href}

    tagline_el = MagicMock()
    tagline_el.text = description

    loc_el = MagicMock()
    loc_el.text = location

    def card_css(selector):
        if "company_info a" in selector or "company_name" in selector:
            return [name_el] if company_name else []
        if "company_info__wrap" in selector or "provider-info__description" in selector:
            return [tagline_el] if description else []
        if "locality" in selector or "provider-info__location" in selector:
            return [loc_el] if location else []
        return []

    card.css = card_css
    return card


@pytest.fixture
def engine():
    return MagicMock(spec=ScraperEngine)


@pytest.fixture
def scraper(engine):
    return ClutchScraper(engine)


class TestClutchScraper:
    def test_parses_company_cards(self, scraper, engine):
        card1 = _make_mock_card("Acme Dev", "Full-stack agency", "New York, NY", "/profile/acme-dev")
        card2 = _make_mock_card("Beta Corp", "Mobile development", "Austin, TX", "/profile/beta-corp")

        mock_response = MagicMock()
        mock_response.css = lambda sel: [card1, card2] if "provider-row" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["python"], max_results=20))

        assert len(leads) == 2
        assert leads[0].company_name == "Acme Dev"
        assert leads[0].source == "clutch"
        assert leads[1].company_name == "Beta Corp"

    def test_lead_url_constructed(self, scraper, engine):
        card = _make_mock_card("Acme Dev", "Agency", "NYC", "/profile/acme-dev")
        mock_response = MagicMock()
        mock_response.css = lambda sel: [card] if "provider-row" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["web"], max_results=20))
        assert leads[0].url == f"{BASE_URL}/profile/acme-dev"

    def test_absolute_url_kept(self, scraper, engine):
        card = _make_mock_card("Acme", "Desc", "NYC", "https://clutch.co/profile/acme")
        mock_response = MagicMock()
        mock_response.css = lambda sel: [card] if "provider-row" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["dev"], max_results=20))
        assert leads[0].url == "https://clutch.co/profile/acme"

    def test_skips_cards_without_name(self, scraper, engine):
        card = _make_mock_card("", "Some description", "Location", "/profile/x")
        mock_response = MagicMock()
        mock_response.css = lambda sel: [card] if "provider-row" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["test"], max_results=20))
        assert len(leads) == 0

    def test_handles_empty_response(self, scraper, engine):
        engine.fetch.return_value = None

        leads = _run(scraper.search(["python"], max_results=20))
        assert leads == []

    def test_handles_fetch_error(self, scraper, engine):
        engine.fetch.side_effect = Exception("Connection error")

        leads = _run(scraper.search(["python"], max_results=20))
        assert leads == []

    def test_respects_max_results(self, scraper, engine):
        cards = [_make_mock_card(f"Company {i}", "Desc", "Loc", f"/p/{i}") for i in range(10)]
        mock_response = MagicMock()
        mock_response.css = lambda sel: cards if "provider-row" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["test"], max_results=3))
        assert len(leads) <= 3

    def test_source_name(self, scraper):
        assert scraper.SOURCE_NAME == "clutch"
