import pytest
from src.core.scraper_engine import ScraperEngine, RateLimiter


def test_fetcher_map_completeness():
    engine = ScraperEngine()
    expected = {
        "google_maps", "yelp", "bbb", "yellowpages", "manta",
        "indeed", "linkedin", "clutch", "goodfirms", "twitter", "reddit",
    }
    assert set(engine.FETCHER_MAP.keys()) == expected


def test_google_maps_uses_dynamic():
    engine = ScraperEngine()
    assert engine.FETCHER_MAP["google_maps"] == "dynamic"


def test_yellowpages_uses_http():
    engine = ScraperEngine()
    assert engine.FETCHER_MAP["yellowpages"] == "http"


def test_yelp_uses_stealth():
    engine = ScraperEngine()
    assert engine.FETCHER_MAP["yelp"] == "stealth"


def test_rate_limiter_can_make_request():
    limiter = RateLimiter()
    assert limiter.can_make_request("google_maps") is True


def test_rate_limiter_records_request():
    limiter = RateLimiter()
    limiter.record_request("google_maps")
    assert limiter.get_requests_in_last_hour("google_maps") == 1


def test_rate_limiter_unknown_source():
    limiter = RateLimiter()
    assert limiter.can_make_request("unknown_source") is True


def test_get_fetcher_returns_correct_types():
    from scrapling import Fetcher, StealthyFetcher, DynamicFetcher
    engine = ScraperEngine()
    assert engine._get_fetcher("yellowpages") == Fetcher
    assert engine._get_fetcher("yelp") == StealthyFetcher
    assert engine._get_fetcher("google_maps") == DynamicFetcher
