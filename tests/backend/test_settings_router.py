"""Tests for backend.routers.settings."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_settings_returns_full_shape(client):
    res = client.get("/api/settings")
    assert res.status_code == 200
    body = res.json()
    for top in ("profile", "email", "scraping"):
        assert top in body
    for k in ("name", "skills", "services", "hourly_rate", "min_budget"):
        assert k in body["profile"]
    for k in ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "sender_name", "from_email"):
        assert k in body["email"]


def test_put_settings_round_trip(client, tmp_path, monkeypatch):
    """Save profile fields, get back what we saved (except password is masked)."""
    from backend.services import settings_store
    monkeypatch.setattr(settings_store, "_SETTINGS_FILE", tmp_path / "settings.json")

    payload = {
        "profile": {"name": "Amine", "skills": ["react", "ts"], "services": ["landing"],
                    "hourly_rate": 100, "min_budget": 500},
        "email": {"smtp_host": "smtp.x.com", "smtp_port": 465, "smtp_user": "u",
                  "smtp_password": "newpass", "sender_name": "A", "from_email": "u@x.com"},
        "scraping": {"proxy_url": "http://proxy", "max_concurrent": 3},
    }
    res = client.put("/api/settings", json=payload)
    assert res.status_code == 200

    res = client.get("/api/settings")
    body = res.json()
    assert body["profile"]["name"] == "Amine"
    assert body["profile"]["hourly_rate"] == 100
    assert body["email"]["smtp_user"] == "u"
    assert body["email"]["smtp_password"] == "••••••••"  # Masked
    assert body["scraping"]["proxy_url"] == "http://proxy"
