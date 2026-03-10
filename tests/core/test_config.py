"""Tests for src.core.config module."""

from pathlib import Path

from src.core.config import (
    COLD_OUTPUT_DIR,
    DIRECT_OUTPUT_DIR,
    OUTPUT_DIR,
    DirectLeadSettings,
    ScrapingSettings,
    Settings,
)


def test_settings_has_all_sections():
    """Settings should expose api, search, audit, scoring, direct_leads, scraping."""
    s = Settings()
    assert hasattr(s, "api")
    assert hasattr(s, "search")
    assert hasattr(s, "audit")
    assert hasattr(s, "scoring")
    assert hasattr(s, "direct_leads")
    assert hasattr(s, "scraping")


def test_direct_lead_settings_defaults():
    """DirectLeadSettings should have sensible defaults."""
    d = DirectLeadSettings()
    assert "python" in d.your_skills
    assert "react" in d.your_skills
    assert "web app" in d.your_services
    assert "mvp" in d.your_services
    assert d.your_hourly_rate == 75
    assert d.your_min_budget == 500


def test_scraping_settings_defaults():
    """ScrapingSettings should default to no proxy and 3 concurrent scrapers."""
    sc = ScrapingSettings()
    assert sc.proxy_url is None
    assert sc.max_concurrent_scrapers == 3


def test_output_dirs_exist():
    """All output directories should be created on import."""
    assert OUTPUT_DIR.is_dir()
    assert COLD_OUTPUT_DIR.is_dir()
    assert DIRECT_OUTPUT_DIR.is_dir()
    # Verify hierarchy
    assert COLD_OUTPUT_DIR.parent == OUTPUT_DIR
    assert DIRECT_OUTPUT_DIR.parent == OUTPUT_DIR
