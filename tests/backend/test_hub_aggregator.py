"""Tests for backend.services.hub_aggregator."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.services.hub_aggregator import (
    compute_stats,
    compute_pulse_status,
    compute_activity,
)


def _opp(stage="new", value=1000, posted_date=None, type_="direct", source="reddit", title="t"):
    """Helper to build an opportunity-shaped dict."""
    return {
        "id": f"id_{title}_{stage}_{value}",
        "type": type_,
        "source": source,
        "title": title,
        "stage": stage,
        "estimated_value_usd": value,
        "score": 50,
        "priority": "warm",
        "posted_date": posted_date,
        "company_name": "",
        "location": "",
        "matched_skills": [],
    }


def test_stats_pipeline_sums_active_stages():
    opps = [
        _opp(stage="new", value=1000),
        _opp(stage="contacted", value=2000),
        _opp(stage="meeting", value=3000),
        _opp(stage="won", value=4000),       # excluded (closed)
        _opp(stage="lost", value=5000),       # excluded (closed)
    ]
    stats = compute_stats(opps)
    assert stats["pipeline_total_usd"] == 6000
    assert stats["won_total_usd"] == 4000


def test_stats_response_rate():
    """Replied/meeting/won as % of contacted-or-later."""
    opps = [
        _opp(stage="new"),       # not in denominator
        _opp(stage="contacted"), # denominator
        _opp(stage="contacted"), # denominator
        _opp(stage="replied"),   # denominator + numerator
        _opp(stage="meeting"),   # denominator + numerator
        _opp(stage="won"),       # denominator + numerator
        _opp(stage="lost"),      # not in denominator
    ]
    stats = compute_stats(opps)
    # 5 in denominator (contacted, contacted, replied, meeting, won), 3 in numerator
    assert stats["response_rate"] == pytest.approx(0.6, abs=0.001)


def test_stats_response_rate_zero_when_no_contacts():
    stats = compute_stats([_opp(stage="new"), _opp(stage="new")])
    assert stats["response_rate"] == 0.0


def test_stats_this_week_sums_recent_pipeline_only():
    now = datetime.now()
    recent = (now - timedelta(days=2)).isoformat()
    old = (now - timedelta(days=10)).isoformat()
    opps = [
        _opp(stage="new", value=500, posted_date=recent),       # included
        _opp(stage="contacted", value=700, posted_date=recent), # included
        _opp(stage="new", value=1000, posted_date=old),         # excluded (old)
        _opp(stage="won", value=2000, posted_date=recent),      # excluded (won)
    ]
    stats = compute_stats(opps)
    assert stats["this_week_usd"] == 1200


def test_stats_count_breakdown():
    opps = [
        _opp(stage="new"),
        _opp(stage="new"),
        _opp(stage="contacted"),
        _opp(stage="won"),
    ]
    stats = compute_stats(opps)
    assert stats["count_total"] == 4
    assert stats["count_pipeline"] == 3
    assert stats["count_won"] == 1


def test_pulse_status_returns_known_sources_with_idle_default():
    """Always return entries for ALL known direct + cold sources, even if no activity."""
    pulse = compute_pulse_status(scans=[], opportunities=[])
    sources = {p["source"] for p in pulse}
    # Direct sources
    for s in ["reddit", "linkedin", "indeed", "twitter", "clutch", "goodfirms"]:
        assert s in sources
    # Cold sources
    for s in ["google_maps", "yelp", "bbb", "yellowpages", "manta"]:
        assert s in sources
    # All idle when there's no scan history
    assert all(p["status"] == "idle" for p in pulse)


def test_pulse_status_running_for_active_scan():
    scans = [
        {
            "id": "s1",
            "status": "running",
            "sources": ["reddit"],
            "started_at": datetime.now().isoformat(),
            "leads_found": 0,
        }
    ]
    pulse = compute_pulse_status(scans=scans, opportunities=[])
    reddit = next(p for p in pulse if p["source"] == "reddit")
    assert reddit["status"] == "live"
    assert reddit["label"] == "scraping"


def test_pulse_status_failed_for_recent_failed_scan():
    scans = [
        {
            "id": "s1",
            "status": "failed",
            "sources": ["tanit"],
            "finished_at": datetime.now().isoformat(),
            "error": "blocked",
            "leads_found": 0,
        }
    ]
    # tanit isn't in known list — it'll appear because it was in a scan
    pulse = compute_pulse_status(scans=scans, opportunities=[])
    tanit = next((p for p in pulse if p["source"] == "tanit"), None)
    assert tanit is not None
    assert tanit["status"] == "error"
    assert tanit["label"] == "blocked"


def test_pulse_status_today_count_from_opportunities():
    today = datetime.now().isoformat()
    opps = [
        _opp(source="reddit", posted_date=today, title="a"),
        _opp(source="reddit", posted_date=today, title="b"),
        _opp(source="linkedin", posted_date=today, title="c"),
    ]
    pulse = compute_pulse_status(scans=[], opportunities=opps)
    reddit = next(p for p in pulse if p["source"] == "reddit")
    linkedin = next(p for p in pulse if p["source"] == "linkedin")
    assert reddit["today_count"] == 2
    assert linkedin["today_count"] == 1


def test_activity_includes_scan_completed():
    finish_time = datetime.now().isoformat()
    scans = [
        {
            "id": "s1",
            "status": "completed",
            "sources": ["reddit"],
            "keywords": ["webflow"],
            "leads_found": 5,
            "finished_at": finish_time,
        }
    ]
    activity = compute_activity(scans=scans, opportunities=[], limit=10)
    assert len(activity) >= 1
    e = activity[0]
    assert e["kind"] == "scan_completed"
    assert e["leads_found"] == 5
    assert "reddit" in e["sources"]


def test_activity_sorted_by_timestamp_desc_and_limited():
    now = datetime.now()
    scans = [
        {"id": "s1", "status": "completed", "sources": ["reddit"], "keywords": ["a"], "leads_found": 1, "finished_at": (now - timedelta(hours=2)).isoformat()},
        {"id": "s2", "status": "completed", "sources": ["linkedin"], "keywords": ["b"], "leads_found": 2, "finished_at": (now - timedelta(hours=1)).isoformat()},
        {"id": "s3", "status": "completed", "sources": ["indeed"], "keywords": ["c"], "leads_found": 3, "finished_at": now.isoformat()},
    ]
    activity = compute_activity(scans=scans, opportunities=[], limit=2)
    assert len(activity) == 2
    # Most recent first
    assert activity[0]["id"].endswith("s3")
    assert activity[1]["id"].endswith("s2")


def test_stats_handles_none_value():
    """Opportunities with estimated_value_usd=None should not crash, contribute 0."""
    opps = [
        _opp(stage="new", value=None),
        _opp(stage="contacted", value=None),
        _opp(stage="contacted", value=2000),
    ]
    stats = compute_stats(opps)
    assert stats["pipeline_total_usd"] == 2000  # only the third opp counts
    assert stats["count_pipeline"] == 3


def test_pulse_status_handles_scan_with_no_sources():
    """Scan dict missing 'sources' key (or with None/[]) should not crash."""
    scans = [
        {"id": "s1", "status": "running"},  # no sources key at all
        {"id": "s2", "status": "completed", "sources": None},
        {"id": "s3", "status": "completed", "sources": []},
    ]
    pulse = compute_pulse_status(scans=scans, opportunities=[])
    # All known sources still present, all idle
    assert any(p["source"] == "reddit" for p in pulse)
    assert all(p["status"] == "idle" for p in pulse)
