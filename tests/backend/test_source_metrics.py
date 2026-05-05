"""Tests for backend.services.source_metrics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.services.source_metrics import compute_source_summary, compute_seven_day_series


def _opp(source="reddit", posted_date=None, value=1000, title="t"):
    return {
        "id": f"id_{title}_{posted_date}",
        "source": source,
        "title": title,
        "posted_date": posted_date,
        "estimated_value_usd": value,
    }


def test_seven_day_series_counts_opps_per_day_oldest_first():
    """Series is 7 ints, today at index 6, 6 days ago at index 0."""
    today = datetime.now(timezone.utc).date()
    opps = [
        _opp(source="reddit", posted_date=(datetime.combine(today, datetime.min.time(), timezone.utc)).isoformat()),
        _opp(source="reddit", posted_date=(datetime.combine(today, datetime.min.time(), timezone.utc)).isoformat()),
        _opp(source="reddit", posted_date=(datetime.combine(today - timedelta(days=3), datetime.min.time(), timezone.utc)).isoformat()),
        _opp(source="linkedin", posted_date=(datetime.combine(today - timedelta(days=2), datetime.min.time(), timezone.utc)).isoformat()),
    ]
    series = compute_seven_day_series("reddit", opps)
    assert len(series) == 7
    assert series[6] == 2  # today
    assert series[3] == 1  # 3 days ago
    assert sum(series) == 3  # only the reddit opps


def test_seven_day_series_handles_missing_posted_date():
    series = compute_seven_day_series("reddit", [_opp(source="reddit", posted_date=None)])
    assert series == [0, 0, 0, 0, 0, 0, 0]


def test_seven_day_series_returns_zeros_for_unknown_source():
    series = compute_seven_day_series("does-not-exist", [_opp(source="reddit", posted_date=datetime.now(timezone.utc).isoformat())])
    assert series == [0, 0, 0, 0, 0, 0, 0]


def test_compute_source_summary_combines_state_and_metrics():
    today_iso = datetime.now(timezone.utc).isoformat()
    scans = [
        {"id": "s1", "status": "completed", "sources": ["reddit"], "finished_at": today_iso, "leads_found": 3},
    ]
    opps = [
        _opp(source="reddit", posted_date=today_iso, value=2500),
        _opp(source="reddit", posted_date=today_iso, value=1500),
    ]
    summary = compute_source_summary(
        source="reddit",
        scans=scans,
        opportunities=opps,
        enabled=True,
    )
    assert summary["source"] == "reddit"
    assert summary["enabled"] is True
    assert summary["status"] == "idle"
    assert summary["last_fetch"] == today_iso
    assert summary["today_count"] == 2
    assert summary["today_value_usd"] == 4000
    assert len(summary["seven_day_series"]) == 7
    assert summary["seven_day_series"][6] == 2


def test_compute_source_summary_status_running_when_scan_active():
    summary = compute_source_summary(
        source="reddit",
        scans=[{"id": "s1", "status": "running", "sources": ["reddit"], "started_at": datetime.now(timezone.utc).isoformat()}],
        opportunities=[],
        enabled=True,
    )
    assert summary["status"] == "live"


def test_compute_source_summary_status_error_when_scan_failed():
    summary = compute_source_summary(
        source="reddit",
        scans=[{"id": "s1", "status": "failed", "sources": ["reddit"], "finished_at": datetime.now(timezone.utc).isoformat(), "error": "blocked"}],
        opportunities=[],
        enabled=True,
    )
    assert summary["status"] == "error"
    assert summary["last_error"] == "blocked"


def test_compute_source_summary_disabled():
    summary = compute_source_summary(source="reddit", scans=[], opportunities=[], enabled=False)
    assert summary["enabled"] is False
    assert summary["status"] == "idle"
