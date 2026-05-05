"""Hub dashboard aggregations: pipeline stats, scraper pulse status, recent activity.

Pure functions over storage data — easy to unit test, no I/O."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


# Stage groupings — must match src/core/models.py Stage enum
_PIPELINE_STAGES = {"new", "researching", "contacted", "replied", "meeting"}
_CONTACTED_OR_LATER = {"contacted", "replied", "meeting", "won"}
_RESPONDED = {"replied", "meeting", "won"}

# Sources we always show in the Pulse Bar / Scraper Status (even if idle).
_KNOWN_DIRECT_SOURCES = ["reddit", "linkedin", "linkedin_posts", "indeed", "twitter", "clutch", "goodfirms"]
_KNOWN_COLD_SOURCES = ["google_maps", "yelp", "bbb", "yellowpages", "manta"]


def compute_stats(opportunities: list[dict]) -> dict[str, Any]:
    """Compute money-first stats for the Hub hero + secondary cards."""
    pipeline_total = 0
    won_total = 0
    this_week_total = 0
    count_pipeline = 0
    count_won = 0
    contacted_or_later = 0
    responded = 0

    week_ago = datetime.now() - timedelta(days=7)

    for o in opportunities:
        stage = o.get("stage") or "new"
        value = int(o.get("estimated_value_usd") or 0)

        if stage in _PIPELINE_STAGES:
            pipeline_total += value
            count_pipeline += 1
            posted = o.get("posted_date")
            if posted:
                try:
                    if datetime.fromisoformat(posted) >= week_ago:
                        this_week_total += value
                except (ValueError, TypeError):
                    pass

        if stage == "won":
            won_total += value
            count_won += 1

        if stage in _CONTACTED_OR_LATER:
            contacted_or_later += 1
            if stage in _RESPONDED:
                responded += 1

    response_rate = (responded / contacted_or_later) if contacted_or_later else 0.0

    return {
        "pipeline_total_usd": pipeline_total,
        "won_total_usd": won_total,
        "this_week_usd": this_week_total,
        "response_rate": round(response_rate, 4),
        "count_total": len(opportunities),
        "count_pipeline": count_pipeline,
        "count_won": count_won,
    }


def compute_pulse_status(scans: list[dict], opportunities: list[dict]) -> list[dict[str, Any]]:
    """Per-source live status for the Pulse Bar + Scraper Status Grid.

    Returns one dict per source with: source, status (live|idle|error), label, last_fetch, today_count.
    """
    today = datetime.now().date()

    # Today's catch by source from opportunities
    today_count: dict[str, int] = {}
    for o in opportunities:
        posted = o.get("posted_date")
        if not posted:
            continue
        try:
            if datetime.fromisoformat(posted).date() == today:
                src = o.get("source") or ""
                today_count[src] = today_count.get(src, 0) + 1
        except (ValueError, TypeError):
            continue

    # Per-source state derived from scans (most recent wins per source)
    per_source: dict[str, dict[str, Any]] = {}
    # Sort scans newest first so first-seen-per-source is the most recent.
    scans_sorted = sorted(
        scans,
        key=lambda s: s.get("finished_at") or s.get("started_at") or s.get("created_at") or "",
        reverse=True,
    )
    for scan in scans_sorted:
        for src in scan.get("sources") or []:
            if src in per_source:
                continue
            status_str = scan.get("status") or ""
            if status_str == "running":
                per_source[src] = {"status": "live", "label": "scraping"}
            elif status_str == "failed":
                per_source[src] = {"status": "error", "label": scan.get("error") or "blocked"}
            elif status_str == "completed":
                per_source[src] = {"status": "idle", "label": "idle"}
            else:
                per_source[src] = {"status": "idle", "label": status_str or "idle"}
            per_source[src]["last_fetch"] = scan.get("finished_at") or scan.get("started_at")

    # Build the final list — every known source plus any extras seen in scans.
    all_sources = list(_KNOWN_DIRECT_SOURCES) + list(_KNOWN_COLD_SOURCES)
    for s in per_source:
        if s not in all_sources:
            all_sources.append(s)

    out = []
    for src in all_sources:
        state = per_source.get(src, {"status": "idle", "label": "idle", "last_fetch": None})
        out.append({
            "source": src,
            "status": state["status"],
            "label": state["label"],
            "last_fetch": state.get("last_fetch"),
            "today_count": today_count.get(src, 0),
        })
    return out


def compute_activity(scans: list[dict], opportunities: list[dict], limit: int = 30) -> list[dict[str, Any]]:
    """Recent activity feed. Mixes scan events and lead-added events, sorted by time desc."""
    events: list[dict] = []

    for scan in scans:
        ts = scan.get("finished_at") or scan.get("started_at") or scan.get("created_at")
        if not ts:
            continue
        kind = "scan_completed" if scan.get("status") == "completed" else (
            "scan_failed" if scan.get("status") == "failed" else "scan_running"
        )
        events.append({
            "id": f"scan_{scan.get('id', '')}",
            "kind": kind,
            "ts": ts,
            "sources": scan.get("sources") or [],
            "keywords": scan.get("keywords") or [],
            "leads_found": scan.get("leads_found") or 0,
            "error": scan.get("error"),
        })

    # Lead-added events from opportunities with posted_date
    for o in opportunities:
        posted = o.get("posted_date")
        if not posted:
            continue
        events.append({
            "id": f"lead_{o.get('id', '')}",
            "kind": "lead_added",
            "ts": posted,
            "title": o.get("title") or "",
            "source": o.get("source") or "",
            "value_usd": int(o.get("estimated_value_usd") or 0),
            "priority": o.get("priority") or "cold",
        })

    events.sort(key=lambda e: e["ts"], reverse=True)
    return events[:limit]
