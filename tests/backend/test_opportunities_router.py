"""Tests for backend.routers.opportunities."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_opportunities_returns_envelope(client):
    """Endpoint always returns {opportunities, total, filters_applied}."""
    res = client.get("/api/opportunities")
    assert res.status_code == 200
    body = res.json()
    assert "opportunities" in body
    assert "total" in body
    assert isinstance(body["opportunities"], list)


def test_list_opportunities_supports_type_filter(client):
    res = client.get("/api/opportunities?type=direct")
    assert res.status_code == 200
    for opp in res.json()["opportunities"]:
        assert opp["type"] == "direct"

    res = client.get("/api/opportunities?type=cold")
    assert res.status_code == 200
    for opp in res.json()["opportunities"]:
        assert opp["type"] == "cold"


def test_list_opportunities_supports_priority_filter(client):
    res = client.get("/api/opportunities?priority=hot")
    assert res.status_code == 200
    for opp in res.json()["opportunities"]:
        assert opp["priority"] == "hot"


def test_list_opportunities_supports_search(client):
    """Search matches title, company_name, source, location case-insensitively."""
    res = client.get("/api/opportunities?q=webflow")
    assert res.status_code == 200
    # Don't assert results exist (depends on test data) — only that the call succeeds.


def test_list_opportunities_default_sort_is_score_desc(client):
    res = client.get("/api/opportunities?limit=10")
    body = res.json()
    opps = body["opportunities"]
    if len(opps) >= 2:
        for a, b in zip(opps, opps[1:]):
            assert a["score"] >= b["score"]


def test_get_single_opportunity_404_for_unknown(client):
    res = client.get("/api/opportunities/__no_such_id__")
    assert res.status_code == 404


def test_patch_stage_validates_enum(client):
    res = client.patch("/api/opportunities/__some_id__/stage", json={"stage": "made_up_stage"})
    assert res.status_code == 422  # pydantic validation error
