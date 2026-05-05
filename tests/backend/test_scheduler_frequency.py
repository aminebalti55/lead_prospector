"""Tests for backend.scheduler._parse_frequency (and adjacent logic)."""
from __future__ import annotations

import pytest

from backend.scheduler import Scheduler


def test_hourly():
    s = Scheduler()
    assert s._parse_frequency("hourly") == 1


def test_daily():
    s = Scheduler()
    assert s._parse_frequency("daily") == 24


def test_weekly():
    s = Scheduler()
    assert s._parse_frequency("weekly") == 168


def test_biweekly():
    s = Scheduler()
    assert s._parse_frequency("biweekly") == 336


def test_monthly():
    s = Scheduler()
    assert s._parse_frequency("monthly") == 720


def test_n_hours_shorthand():
    s = Scheduler()
    assert s._parse_frequency("6hours") == 6
    assert s._parse_frequency("12hours") == 12


def test_unknown_defaults_to_24():
    s = Scheduler()
    assert s._parse_frequency("garbage") == 24


def test_case_insensitive():
    s = Scheduler()
    assert s._parse_frequency("WEEKLY") == 168
    assert s._parse_frequency("BiWeekly") == 336
