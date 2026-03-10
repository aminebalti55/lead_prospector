"""Tests for TwitterScraper (Task 21) - mock HTML parsing."""

import asyncio

import pytest
from unittest.mock import MagicMock

from src.direct_leads.scrapers.twitter import TwitterScraper
from src.core.scraper_engine import ScraperEngine


def _run(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_mock_tweet(text, username="@user", href="/user/status/123"):
    """Create a mock Nitter tweet element."""
    tweet = MagicMock()

    content_el = MagicMock()
    content_el.get_all_text.return_value = text

    username_el = MagicMock()
    username_el.get_all_text.return_value = username

    link_el = MagicMock()
    link_el.attrib = {"href": href}

    def css_first(selector):
        if "tweet-content" in selector:
            return content_el
        if selector == "p":
            return content_el
        if "username" in selector:
            return username_el
        if "tweet-link" in selector:
            return link_el
        if "status" in selector:
            return link_el
        if "tweet-date" in selector or selector == "time":
            return None
        return None

    tweet.css_first = css_first
    return tweet


@pytest.fixture
def engine():
    return MagicMock(spec=ScraperEngine)


@pytest.fixture
def scraper(engine):
    return TwitterScraper(engine)


class TestTwitterParseNitter:
    def test_parses_tweets(self, scraper):
        tweet1 = _make_mock_tweet(
            "Looking for a Python developer for freelance project",
            username="@techrecruiter",
            href="/techrecruiter/status/111"
        )
        tweet2 = _make_mock_tweet(
            "Need a React contractor ASAP",
            username="@startup_ceo",
            href="/startup_ceo/status/222"
        )

        mock_page = MagicMock()
        mock_page.css = lambda sel: [tweet1, tweet2] if "timeline-item" in sel else []

        leads = scraper._parse_nitter(mock_page, "https://nitter.net")

        assert len(leads) == 2
        assert leads[0].source == "twitter"
        assert leads[0].contact_name == "@techrecruiter"
        assert leads[0].url == "https://twitter.com/techrecruiter/status/111"
        assert "Python developer" in leads[0].description
        assert leads[1].contact_name == "@startup_ceo"

    def test_truncates_long_title(self, scraper):
        long_text = "A" * 200
        tweet = _make_mock_tweet(long_text, username="@user", href="/user/status/1")

        mock_page = MagicMock()
        mock_page.css = lambda sel: [tweet] if "timeline-item" in sel else []

        leads = scraper._parse_nitter(mock_page, "https://nitter.net")
        assert len(leads[0].title) == 103  # 100 chars + "..."
        assert leads[0].title.endswith("...")

    def test_short_title_no_ellipsis(self, scraper):
        tweet = _make_mock_tweet("Short tweet", username="@u", href="/u/status/1")

        mock_page = MagicMock()
        mock_page.css = lambda sel: [tweet] if "timeline-item" in sel else []

        leads = scraper._parse_nitter(mock_page, "https://nitter.net")
        assert leads[0].title == "Short tweet"

    def test_constructs_twitter_url_from_relative_href(self, scraper):
        tweet = _make_mock_tweet("Hiring!", username="@boss", href="/boss/status/999")

        mock_page = MagicMock()
        mock_page.css = lambda sel: [tweet] if "timeline-item" in sel else []

        leads = scraper._parse_nitter(mock_page, "https://nitter.net")
        assert leads[0].url == "https://twitter.com/boss/status/999"

    def test_keeps_absolute_url(self, scraper):
        tweet = _make_mock_tweet("Hiring!", username="@boss", href="https://twitter.com/boss/status/999")

        mock_page = MagicMock()
        mock_page.css = lambda sel: [tweet] if "timeline-item" in sel else []

        leads = scraper._parse_nitter(mock_page, "https://nitter.net")
        assert leads[0].url == "https://twitter.com/boss/status/999"

    def test_skips_tweets_without_content(self, scraper):
        tweet = MagicMock()
        tweet.css_first = lambda sel: None

        mock_page = MagicMock()
        mock_page.css = lambda sel: [tweet] if "timeline-item" in sel else []

        leads = scraper._parse_nitter(mock_page, "https://nitter.net")
        assert len(leads) == 0

    def test_handles_empty_page(self, scraper):
        mock_page = MagicMock()
        mock_page.css = lambda sel: []

        leads = scraper._parse_nitter(mock_page, "https://nitter.net")
        assert leads == []

    def test_fallback_css_selectors(self, scraper):
        """Test that fallback selector (tweet-body) is used."""
        tweet = _make_mock_tweet("Need dev", username="@x", href="/x/status/1")
        mock_page = MagicMock()

        def css_side_effect(sel):
            if "tweet-body" in sel:
                return [tweet]
            return []

        mock_page.css = css_side_effect

        leads = scraper._parse_nitter(mock_page, "https://nitter.net")
        assert len(leads) == 1


class TestTwitterSearch:
    def test_search_returns_leads(self, scraper, engine):
        tweet = _make_mock_tweet("Need Python dev", username="@hr", href="/hr/status/1")
        mock_response = MagicMock()
        mock_response.css = lambda sel: [tweet] if "timeline-item" in sel else []
        engine.fetch_with_retry.return_value = mock_response

        leads = _run(scraper.search(["python"], max_results=20))
        assert len(leads) >= 1
        assert leads[0].source == "twitter"

    def test_handles_all_instances_failing(self, scraper, engine):
        engine.fetch_with_retry.side_effect = Exception("Connection error")

        leads = _run(scraper.search(["python"], max_results=20))
        assert leads == []

    def test_respects_max_results(self, scraper, engine):
        tweets = [_make_mock_tweet(f"Tweet {i}", f"@u{i}", f"/u{i}/status/{i}") for i in range(10)]
        mock_response = MagicMock()
        mock_response.css = lambda sel: tweets if "timeline-item" in sel else []
        engine.fetch_with_retry.return_value = mock_response

        leads = _run(scraper.search(["test"], max_results=3))
        assert len(leads) <= 3

    def test_source_name(self, scraper):
        assert scraper.SOURCE_NAME == "twitter"

    def test_location_default(self, scraper):
        tweet = _make_mock_tweet("Hiring!", username="@x", href="/x/status/1")
        mock_page = MagicMock()
        mock_page.css = lambda sel: [tweet] if "timeline-item" in sel else []

        leads = scraper._parse_nitter(mock_page, "https://nitter.net")
        assert leads[0].location == "Unknown"
