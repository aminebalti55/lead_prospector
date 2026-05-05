"""Tests for backend.services.source_state."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services import source_state


@pytest.fixture
def tmp_state_file(tmp_path, monkeypatch):
    """Redirect the state file to a temporary location."""
    p = tmp_path / "source_state.json"
    monkeypatch.setattr(source_state, "_STATE_FILE", p)
    return p


def test_unknown_source_defaults_to_enabled(tmp_state_file):
    assert source_state.is_enabled("reddit") is True
    assert source_state.is_enabled("anything") is True


def test_set_enabled_persists(tmp_state_file):
    source_state.set_enabled("reddit", False)
    assert source_state.is_enabled("reddit") is False
    # Persists across "process restart" (re-read from disk)
    raw = json.loads(tmp_state_file.read_text())
    assert raw == {"reddit": False}


def test_toggle_flips_value(tmp_state_file):
    assert source_state.is_enabled("linkedin") is True
    new_value = source_state.toggle("linkedin")
    assert new_value is False
    assert source_state.is_enabled("linkedin") is False
    new_value = source_state.toggle("linkedin")
    assert new_value is True


def test_get_all_returns_explicit_overrides_only(tmp_state_file):
    """get_all returns the dict from disk — defaults are not materialized."""
    assert source_state.get_all() == {}
    source_state.set_enabled("reddit", False)
    source_state.set_enabled("yelp", True)
    assert source_state.get_all() == {"reddit": False, "yelp": True}


def test_corrupted_state_file_returns_empty(tmp_state_file):
    tmp_state_file.write_text("{not valid json")
    assert source_state.get_all() == {}
    assert source_state.is_enabled("reddit") is True
