"""Tests for RedditScraper (Task 16) - mock JSON parsing."""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from src.direct_leads.scrapers.reddit import RedditScraper, SUBREDDITS
from src.core.scraper_engine import ScraperEngine


MOCK_REDDIT_JSON = json.dumps({
    "data": {
        "children": [
            {
                "data": {
                    "title": "[Hiring] Python Developer for SaaS Project",
                    "selftext": "We need a senior Python developer with FastAPI experience. Budget $5000. Remote OK.",
                    "permalink": "/r/forhire/comments/abc123/hiring_python_developer/",
                    "created_utc": 1700000000,
                    "author": "test_user",
                    "link_flair_text": "Hiring",
                }
            },
            {
                "data": {
                    "title": "Looking for React dev",
                    "selftext": "Need help building a dashboard.",
                    "permalink": "/r/forhire/comments/def456/looking_for_react_dev/",
                    "created_utc": 1700001000,
                    "author": "another_user",
                    "link_flair_text": "For Hire",
                }
            },
            {
                "data": {
                    "title": "My portfolio showcase",
                    "selftext": "Check out my work.",
                    "permalink": "/r/forhire/comments/ghi789/my_portfolio/",
                    "created_utc": 1700002000,
                    "author": "showcase_user",
                    "link_flair_text": "Portfolio",
                }
            },
        ]
    }
})


def _run(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def engine():
    return ScraperEngine()


@pytest.fixture
def scraper(engine):
    return RedditScraper(engine)


class TestRedditScraper:
    def test_parses_hiring_posts(self, scraper):
        mock_response = MagicMock()
        mock_response.get_all_text.return_value = MOCK_REDDIT_JSON
        mock_response.__bool__ = lambda self: True

        with patch("src.direct_leads.scrapers.reddit.Fetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get.return_value = mock_response

            leads = _run(scraper.search(["python"], max_results=20))

        # Each subreddit call returns 2 matching posts (Hiring + For Hire flairs),
        # the Portfolio post is filtered out. Multiple subreddits produce duplicates.
        assert len(leads) >= 2
        assert all(lead.source == "reddit" for lead in leads)

    def test_lead_fields_populated(self, scraper):
        mock_response = MagicMock()
        mock_response.get_all_text.return_value = MOCK_REDDIT_JSON
        mock_response.__bool__ = lambda self: True

        with patch("src.direct_leads.scrapers.reddit.Fetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get.return_value = mock_response

            leads = _run(scraper.search(["python"], max_results=20))

        lead = leads[0]
        assert lead.source == "reddit"
        assert "Python Developer" in lead.title
        assert lead.contact_name == "test_user"
        assert lead.location == "Remote"
        assert "reddit.com" in lead.url
        assert isinstance(lead.posted_date, datetime)

    def test_respects_max_results(self, scraper):
        mock_response = MagicMock()
        mock_response.get_all_text.return_value = MOCK_REDDIT_JSON
        mock_response.__bool__ = lambda self: True

        with patch("src.direct_leads.scrapers.reddit.Fetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get.return_value = mock_response

            leads = _run(scraper.search(["python"], max_results=1))

        assert len(leads) <= 1

    def test_handles_empty_response(self, scraper):
        mock_response = MagicMock()
        mock_response.get_all_text.return_value = json.dumps({"data": {"children": []}})
        mock_response.__bool__ = lambda self: True

        with patch("src.direct_leads.scrapers.reddit.Fetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get.return_value = mock_response

            leads = _run(scraper.search(["python"], max_results=20))

        assert leads == []

    def test_handles_fetch_error(self, scraper):
        with patch("src.direct_leads.scrapers.reddit.Fetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get.side_effect = Exception("Network error")

            leads = _run(scraper.search(["python"], max_results=20))

        assert leads == []

    def test_filters_by_hiring_flair_and_title(self, scraper):
        """Posts with [hiring] in title should also be included."""
        data = json.dumps({
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "[Hiring] Need a web developer",
                            "selftext": "Details here.",
                            "permalink": "/r/forhire/comments/xyz/hiring_web_dev/",
                            "created_utc": 1700000000,
                            "author": "poster",
                            "link_flair_text": "",
                        }
                    }
                ]
            }
        })
        mock_response = MagicMock()
        mock_response.get_all_text.return_value = data
        mock_response.__bool__ = lambda self: True

        with patch("src.direct_leads.scrapers.reddit.Fetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get.return_value = mock_response

            leads = _run(scraper.search(["web"], max_results=20))

        assert len(leads) >= 1
        assert "[Hiring]" in leads[0].title

    def test_source_name(self, scraper):
        assert scraper.SOURCE_NAME == "reddit"

    def test_subreddits_defined(self):
        assert "forhire" in SUBREDDITS
        assert "hiring" in SUBREDDITS
