"""Tests for backend.services.settings_store."""
from __future__ import annotations

import json

import pytest

from backend.services import settings_store


@pytest.fixture
def tmp_settings_file(tmp_path, monkeypatch):
    p = tmp_path / "settings.json"
    monkeypatch.setattr(settings_store, "_SETTINGS_FILE", p)
    return p


def test_get_returns_defaults_when_no_file(tmp_settings_file):
    s = settings_store.get_masked()
    assert s["profile"]["name"] == ""
    assert s["email"]["smtp_host"] == "smtp.gmail.com"
    assert s["email"]["smtp_port"] == 587
    assert s["email"]["smtp_password"] == ""  # No password set → empty
    assert s["scraping"]["max_concurrent"] == 5


def test_save_persists_and_get_masks_password(tmp_settings_file):
    settings_store.save({
        "profile": {"name": "Amine", "skills": ["react"], "services": [], "hourly_rate": 75, "min_budget": 0},
        "email": {"smtp_host": "smtp.gmail.com", "smtp_port": 587, "smtp_user": "a@b.com",
                  "smtp_password": "secret123", "sender_name": "Amine", "from_email": "a@b.com"},
        "scraping": {"proxy_url": None, "max_concurrent": 5},
    })
    raw = json.loads(tmp_settings_file.read_text())
    assert raw["email"]["smtp_password"] == "secret123"  # Stored unmasked

    masked = settings_store.get_masked()
    assert masked["profile"]["name"] == "Amine"
    assert masked["email"]["smtp_password"] == "••••••••"  # Masked on read


def test_save_preserves_password_when_incoming_is_mask_placeholder(tmp_settings_file):
    """PUT with the mask placeholder must NOT overwrite the real password."""
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "real_secret", "sender_name": "x", "from_email": "x"},
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "••••••••", "sender_name": "x", "from_email": "x"},  # Mask placeholder
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    raw = json.loads(tmp_settings_file.read_text())
    assert raw["email"]["smtp_password"] == "real_secret"  # Preserved


def test_save_preserves_password_when_incoming_is_empty(tmp_settings_file):
    """PUT with empty password must NOT overwrite the real password."""
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "real_secret", "sender_name": "x", "from_email": "x"},
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "", "sender_name": "x", "from_email": "x"},  # Empty
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    raw = json.loads(tmp_settings_file.read_text())
    assert raw["email"]["smtp_password"] == "real_secret"


def test_get_raw_returns_actual_password(tmp_settings_file):
    """get_raw is for backend use only (e.g., outreach send) — returns real password."""
    settings_store.save({
        "profile": {"name": "X", "skills": [], "services": [], "hourly_rate": 0, "min_budget": 0},
        "email": {"smtp_host": "x", "smtp_port": 1, "smtp_user": "x",
                  "smtp_password": "real", "sender_name": "x", "from_email": "x"},
        "scraping": {"proxy_url": None, "max_concurrent": 1},
    })
    raw = settings_store.get_raw()
    assert raw["email"]["smtp_password"] == "real"


def test_corrupted_file_returns_defaults(tmp_settings_file):
    tmp_settings_file.write_text("{not valid json")
    s = settings_store.get_masked()
    assert s["profile"]["name"] == ""
    assert s["email"]["smtp_host"] == "smtp.gmail.com"
