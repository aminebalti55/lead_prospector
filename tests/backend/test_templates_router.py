"""Tests for backend.routers.templates."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_templates(client):
    res = client.get("/api/templates")
    assert res.status_code == 200
    body = res.json()
    assert "templates" in body
    assert isinstance(body["templates"], list)
    assert len(body["templates"]) >= 4  # Seeds


def test_get_one_template(client):
    res = client.get("/api/templates/initial")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "initial"
    assert body["name"] == "Initial Outreach"


def test_get_unknown_404(client):
    res = client.get("/api/templates/nonexistent_xxxxx")
    assert res.status_code == 404


def test_create_template(client):
    payload = {"name": "Test create", "subject": "S", "body": "B"}
    res = client.post("/api/templates", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Test create"
    new_id = body["id"]
    # Cleanup
    client.delete(f"/api/templates/{new_id}")


def test_update_template(client):
    created = client.post("/api/templates", json={"name": "Orig", "subject": "S", "body": "B"}).json()
    res = client.put(f"/api/templates/{created['id']}", json={"name": "Updated", "subject": "S2", "body": "B2"})
    assert res.status_code == 200
    assert res.json()["name"] == "Updated"
    # Cleanup
    client.delete(f"/api/templates/{created['id']}")


def test_update_unknown_404(client):
    res = client.put("/api/templates/nonexistent", json={"name": "X", "subject": "X", "body": "X"})
    assert res.status_code == 404


def test_delete_template(client):
    created = client.post("/api/templates", json={"name": "ToDelete", "subject": "S", "body": "B"}).json()
    res = client.delete(f"/api/templates/{created['id']}")
    assert res.status_code == 200
    res = client.get(f"/api/templates/{created['id']}")
    assert res.status_code == 404
