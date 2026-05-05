"""Tests for backend.services.templates_store."""
from __future__ import annotations

import json

import pytest

from backend.services import templates_store


@pytest.fixture
def tmp_templates_file(tmp_path, monkeypatch):
    p = tmp_path / "email_templates.json"
    monkeypatch.setattr(templates_store, "_TEMPLATES_FILE", p)
    return p


def test_get_all_seeds_defaults_on_first_call(tmp_templates_file):
    """First call should return the 4 hardcoded seed templates."""
    templates = templates_store.get_all()
    assert len(templates) == 4
    ids = {t["id"] for t in templates}
    assert {"initial", "initial_with_review", "followup", "final"}.issubset(ids)


def test_create_template_assigns_id_and_persists(tmp_templates_file):
    t = templates_store.create({"name": "My Template", "subject": "Hi {name}", "body": "Hey {first_name}"})
    assert "id" in t
    assert len(t["id"]) == 8
    assert t["name"] == "My Template"
    # Persists across "process restart"
    all_t = templates_store.get_all()
    assert any(x["id"] == t["id"] for x in all_t)


def test_update_template(tmp_templates_file):
    t = templates_store.create({"name": "Orig", "subject": "Orig subj", "body": "Orig body"})
    updated = templates_store.update(t["id"], {"name": "New", "subject": "New subj", "body": "New body"})
    assert updated["name"] == "New"
    assert updated["subject"] == "New subj"
    fetched = templates_store.get_by_id(t["id"])
    assert fetched["name"] == "New"


def test_update_unknown_returns_none(tmp_templates_file):
    assert templates_store.update("does_not_exist", {"name": "X", "subject": "X", "body": "X"}) is None


def test_delete_template(tmp_templates_file):
    t = templates_store.create({"name": "X", "subject": "X", "body": "X"})
    assert templates_store.delete(t["id"]) is True
    assert templates_store.get_by_id(t["id"]) is None
    # Idempotent: deleting again returns False
    assert templates_store.delete(t["id"]) is False


def test_get_by_id_returns_seed_templates(tmp_templates_file):
    t = templates_store.get_by_id("initial")
    assert t is not None
    assert t["name"] == "Initial Outreach"
