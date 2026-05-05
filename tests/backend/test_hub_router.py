"""Tests for backend.routers.hub."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_hub_stats_returns_required_keys(client):
    res = client.get("/api/hub/stats")
    assert res.status_code == 200
    body = res.json()
    for k in ("pipeline_total_usd", "won_total_usd", "this_week_usd", "response_rate", "count_total", "count_pipeline", "count_won"):
        assert k in body
    assert isinstance(body["pipeline_total_usd"], int)
    assert isinstance(body["response_rate"], (int, float))


def test_hub_activity_returns_list_envelope(client):
    res = client.get("/api/hub/activity")
    assert res.status_code == 200
    body = res.json()
    assert "events" in body
    assert isinstance(body["events"], list)


def test_hub_activity_respects_limit(client):
    res = client.get("/api/hub/activity?limit=5")
    assert res.status_code == 200
    assert len(res.json()["events"]) <= 5


def test_pulse_status_returns_list_envelope(client):
    res = client.get("/api/pulse/status")
    assert res.status_code == 200
    body = res.json()
    assert "sources" in body
    assert isinstance(body["sources"], list)
    # All known direct + cold sources should always be present.
    sources = {s["source"] for s in body["sources"]}
    for s in ["reddit", "linkedin", "google_maps", "yelp"]:
        assert s in sources


def test_pulse_status_each_entry_has_required_shape(client):
    res = client.get("/api/pulse/status")
    body = res.json()
    for s in body["sources"]:
        assert "source" in s
        assert "status" in s
        assert s["status"] in ("live", "idle", "error")
        assert "label" in s
        assert "today_count" in s
        assert "last_fetch" in s  # may be None
