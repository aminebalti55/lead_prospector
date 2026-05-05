"""Tests for src.direct_leads.scrapers.tanit.

We test the parsing logic against a fixture HTML so the test suite never
hits Cloudflare. The fetch path is exercised via integration / smoke testing.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from src.direct_leads.scrapers.tanit import TanitScraper, parse_listing_html


# Real two-card fixture captured live (annotations stripped for compactness).
# First card is featured; second is not.
FIXTURE_HTML = """
<div class="results">
  <article id="1999931" class="media well listing-item listing-item__jobs listing-item__featured">
    <div class="media-left listing-item__logo">
      <a href="https://www.tanitjobs.com/job/1999931/un-e-ingenieur-npi/?backPage=1&amp;searchID=1777993961.5545">
        <img class="profile__img-company" src="https://www.tanitjobs.com/files/pictures/2025/04/21/Logo-CMR.png" alt="CMR GROUP">
      </a>
    </div>
    <div class="media-body">
      <div class="media-heading listing-item__title">
        <a href="https://www.tanitjobs.com/job/1999931/un-e-ingenieur-npi/?backPage=1&amp;searchID=1777993961.5545" class="link">
          Un(e) Ingénieur NPI
        </a>
      </div>
      <div class="listing-item__info clearfix">
        <span class="listing-item-info-company">CMR GROUP - </span>
        <span class="listing-item-info-location">Mghira, Ben Arous, Tunisie</span>
      </div>
      <div class="listing-item__desc hidden-sm hidden-xs">
        Fondé à Marseille en 1959, le Groupe CMR est un spécialiste de la gestion de l'énergie : de l'assemblage de faisceaux électriques complexes pour des moteurs à la conception de capteurs pour...
      </div>
    </div>
  </article>

  <article id="1999900" class="media well listing-item listing-item__jobs">
    <div class="media-left listing-item__logo">
      <a href="https://www.tanitjobs.com/job/1999900/developpeur-react-junior/?backPage=2&amp;searchID=99.99">
        <img class="profile__img-company" src="https://www.tanitjobs.com/files/pictures/2025/05/01/logo.png" alt="Acme Tech">
      </a>
    </div>
    <div class="media-body">
      <div class="media-heading listing-item__title">
        <a href="https://www.tanitjobs.com/job/1999900/developpeur-react-junior/?backPage=2&amp;searchID=99.99" class="link">
          Développeur React Junior
        </a>
      </div>
      <div class="listing-item__info clearfix">
        <span class="listing-item-info-company">Acme Tech - </span>
        <span class="listing-item-info-location">Tunis, Tunisie</span>
      </div>
      <div class="listing-item__desc hidden-sm hidden-xs">
        Nous recherchons un développeur React junior pour rejoindre notre équipe à Tunis.
      </div>
    </div>
  </article>
</div>
"""


def test_parse_listing_html_returns_two_leads():
    leads = parse_listing_html(FIXTURE_HTML)
    assert len(leads) == 2


def test_parse_extracts_title_correctly():
    leads = parse_listing_html(FIXTURE_HTML)
    # First is featured — title gets "[Featured] " prefix
    assert leads[0].title == "[Featured] Un(e) Ingénieur NPI"
    assert leads[1].title == "Développeur React Junior"


def test_parse_extracts_company_strips_trailing_dash():
    leads = parse_listing_html(FIXTURE_HTML)
    assert leads[0].company_name == "CMR GROUP"
    assert leads[1].company_name == "Acme Tech"


def test_parse_extracts_location():
    leads = parse_listing_html(FIXTURE_HTML)
    assert leads[0].location == "Mghira, Ben Arous, Tunisie"
    assert leads[1].location == "Tunis, Tunisie"


def test_parse_extracts_description():
    leads = parse_listing_html(FIXTURE_HTML)
    assert "Groupe CMR" in leads[0].description
    assert "développeur React junior" in leads[1].description


def test_parse_extracts_url_strips_session_params():
    """URLs must not contain ?backPage=... or &searchID=... so dedup works across runs."""
    leads = parse_listing_html(FIXTURE_HTML)
    assert leads[0].url == "https://www.tanitjobs.com/job/1999931/un-e-ingenieur-npi/"
    assert leads[1].url == "https://www.tanitjobs.com/job/1999900/developpeur-react-junior/"


def test_parse_returns_empty_on_garbage_html():
    leads = parse_listing_html("<html><body>nothing here</body></html>")
    assert leads == []


def test_parse_handles_missing_optional_fields():
    minimal = """
    <article id="1" class="listing-item__jobs">
      <div class="listing-item__title"><a href="https://www.tanitjobs.com/job/1/x/" class="link">Just a title</a></div>
    </article>
    """
    leads = parse_listing_html(minimal)
    assert len(leads) == 1
    assert leads[0].title == "Just a title"
    assert leads[0].company_name == ""
    assert leads[0].location == ""
    assert leads[0].description == ""


def test_lead_source_is_tanit():
    leads = parse_listing_html(FIXTURE_HTML)
    assert all(lead.source == "tanit" for lead in leads)


def _make_fake_engine():
    """ScraperEngine mock with a working rate_limiter (no-op async waits)."""
    fake_engine = MagicMock()
    async def _wait_async(source): pass
    fake_engine.rate_limiter.wait_async = _wait_async
    fake_engine.rate_limiter.record_request = MagicMock()
    return fake_engine


def test_search_calls_stealthy_fetcher_with_correct_url(monkeypatch):
    """Mock StealthyFetcher.async_fetch to verify URL + Cloudflare-bypass kwargs."""
    from src.direct_leads.scrapers import tanit as tanit_mod
    fake_response = MagicMock()
    fake_response.html_content = FIXTURE_HTML
    fake_response.body = FIXTURE_HTML.encode("utf-8")
    fake_response.get_all_text = MagicMock(return_value=FIXTURE_HTML)

    called = {}
    async def fake_fetch(url, **kwargs):
        called["url"] = url
        called["kwargs"] = kwargs
        return fake_response

    monkeypatch.setattr(tanit_mod.StealthyFetcher, "async_fetch", fake_fetch)

    scraper = TanitScraper(_make_fake_engine())
    leads = asyncio.get_event_loop().run_until_complete(
        scraper.search(keywords=["react"], max_results=20)
    )

    assert "tanitjobs.com/jobs" in called["url"]
    assert "q=react" in called["url"]
    assert called["kwargs"].get("solve_cloudflare") is True
    assert len(leads) == 2  # From fixture


def test_search_paginates_when_max_results_exceeds_one_page(monkeypatch):
    """With max_results=50, scraper requests at least 3 pages (50/23 = ceil(2.17) = 3)."""
    from src.direct_leads.scrapers import tanit as tanit_mod
    fake_response = MagicMock()
    fake_response.html_content = FIXTURE_HTML
    fake_response.body = FIXTURE_HTML.encode("utf-8")
    fake_response.get_all_text = MagicMock(return_value=FIXTURE_HTML)

    page_calls: list[str] = []
    async def fake_fetch(url, **kwargs):
        page_calls.append(url)
        return fake_response

    monkeypatch.setattr(tanit_mod.StealthyFetcher, "async_fetch", fake_fetch)

    scraper = TanitScraper(_make_fake_engine())
    asyncio.get_event_loop().run_until_complete(
        scraper.search(keywords=["react"], max_results=50)
    )

    # 50/23 = ceil(2.17) → 3 pages requested
    assert len(page_calls) == 3
    # Last URL should contain page=3
    assert "page=3" in page_calls[-1]
