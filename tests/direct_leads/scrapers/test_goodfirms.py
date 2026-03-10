"""Tests for GoodFirmsScraper (Task 20) - mock HTML parsing."""

import asyncio
import pytest
from unittest.mock import MagicMock

from src.direct_leads.scrapers.goodfirms import GoodFirmsScraper, BASE_URL
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

    desc_el = MagicMock()
    desc_el.text = description

    loc_el = MagicMock()
    loc_el.text = location

    def card_css(selector):
        if "firm-name" in selector or "company-name" in selector:
            return [name_el] if company_name else []
        if "h3 a" in selector:
            return [name_el] if company_name else []
        if "firm-desc" in selector or "company-description" in selector:
            return [desc_el] if description else []
        if "firm-location" in selector or "location" in selector:
            return [loc_el] if location else []
        return []

    card.css = card_css
    return card


@pytest.fixture
def engine():
    return MagicMock(spec=ScraperEngine)


@pytest.fixture
def scraper(engine):
    return GoodFirmsScraper(engine)


class TestGoodFirmsScraper:
    def test_parses_firm_cards(self, scraper, engine):
        card1 = _make_mock_card("Alpha Solutions", "Web development", "London, UK", "/company/alpha")
        card2 = _make_mock_card("Omega Tech", "Mobile apps", "Berlin, DE", "/company/omega")

        mock_response = MagicMock()
        mock_response.css = lambda sel: [card1, card2] if "firm-card" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["python"], max_results=20))

        assert len(leads) == 2
        assert leads[0].company_name == "Alpha Solutions"
        assert leads[0].source == "goodfirms"
        assert leads[1].company_name == "Omega Tech"

    def test_lead_url_constructed(self, scraper, engine):
        card = _make_mock_card("Alpha", "Desc", "London", "/company/alpha")
        mock_response = MagicMock()
        mock_response.css = lambda sel: [card] if "firm-card" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["web"], max_results=20))
        assert leads[0].url == f"{BASE_URL}/company/alpha"

    def test_absolute_url_preserved(self, scraper, engine):
        card = _make_mock_card("Test", "Desc", "NYC", "https://www.goodfirms.co/company/test")
        mock_response = MagicMock()
        mock_response.css = lambda sel: [card] if "firm-card" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["dev"], max_results=20))
        assert leads[0].url == "https://www.goodfirms.co/company/test"

    def test_skips_cards_without_name(self, scraper, engine):
        card = _make_mock_card("", "Description", "Location", "/company/x")
        mock_response = MagicMock()
        mock_response.css = lambda sel: [card] if "firm-card" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["test"], max_results=20))
        assert len(leads) == 0

    def test_handles_empty_response(self, scraper, engine):
        engine.fetch.return_value = None

        leads = _run(scraper.search(["python"], max_results=20))
        assert leads == []

    def test_handles_fetch_error(self, scraper, engine):
        engine.fetch.side_effect = Exception("Timeout")

        leads = _run(scraper.search(["python"], max_results=20))
        assert leads == []

    def test_respects_max_results(self, scraper, engine):
        cards = [_make_mock_card(f"Firm {i}", "Desc", "Loc", f"/c/{i}") for i in range(10)]
        mock_response = MagicMock()
        mock_response.css = lambda sel: cards if "firm-card" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["test"], max_results=3))
        assert len(leads) <= 3

    def test_description_truncated(self, scraper, engine):
        long_desc = "x" * 5000
        card = _make_mock_card("Firm", long_desc, "Loc", "/c/firm")
        mock_response = MagicMock()
        mock_response.css = lambda sel: [card] if "firm-card" in sel else []
        engine.fetch.return_value = mock_response

        leads = _run(scraper.search(["test"], max_results=20))
        assert len(leads[0].description) <= 2000

    def test_source_name(self, scraper):
        assert scraper.SOURCE_NAME == "goodfirms"
