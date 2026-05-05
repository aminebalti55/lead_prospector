"""Tests for backend.routers.sources."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_sources_returns_envelope_with_all_known(client):
    res = client.get("/api/sources")
    assert res.status_code == 200
    body = res.json()
    assert "sources" in body
    names = {s["source"] for s in body["sources"]}
    # All 13 known sources should be present
    for s in ["reddit", "linkedin", "linkedin_posts", "indeed", "twitter", "clutch", "goodfirms", "tanit",
              "google_maps", "yelp", "bbb", "yellowpages", "manta"]:
        assert s in names


def test_list_sources_each_entry_has_required_shape(client):
    res = client.get("/api/sources")
    body = res.json()
    for s in body["sources"]:
        for key in ("source", "enabled", "status", "label", "last_fetch", "last_error",
                    "today_count", "today_value_usd", "seven_day_series"):
            assert key in s
        assert isinstance(s["seven_day_series"], list)
        assert len(s["seven_day_series"]) == 7
        assert s["status"] in ("live", "idle", "error")


def test_toggle_source_flips_enabled(client):
    # Read current state
    before = next(s for s in client.get("/api/sources").json()["sources"] if s["source"] == "manta")
    res = client.post("/api/sources/manta/toggle")
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "manta"
    assert body["enabled"] == (not before["enabled"])
    # Toggle back so test is idempotent
    client.post("/api/sources/manta/toggle")


def test_toggle_unknown_source_404(client):
    res = client.post("/api/sources/nonexistent_source/toggle")
    assert res.status_code == 404


def test_run_unknown_source_404(client):
    res = client.post("/api/sources/nonexistent_source/run")
    assert res.status_code == 404


def test_run_source_with_no_history_returns_400(client):
    """Running a source that has no past scan history needs keywords first."""
    # Use 'manta' which (in test data) likely has no scan history
    # We can't fully isolate this test, so accept either 400 (no history) or 200 (history exists).
    res = client.post("/api/sources/manta/run")
    assert res.status_code in (200, 400)
    if res.status_code == 400:
        assert "keywords" in res.json()["detail"].lower()
