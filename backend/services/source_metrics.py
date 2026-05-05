"""Per-source metrics: status, today's count, 7-day series, last error.

Pure functions over scans + opportunities — easy to unit test, no I/O."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _parse_iso(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def compute_seven_day_series(source: str, opportunities: list[dict]) -> list[int]:
    """Return [count_6d_ago, ..., count_today] — 7 ints, today last."""
    today = datetime.now(timezone.utc).date()
    counts = [0] * 7
    for o in opportunities:
        if o.get("source") != source:
            continue
        parsed = _parse_iso(o.get("posted_date"))
        if not parsed:
            continue
        delta = (today - parsed.date()).days
        if 0 <= delta <= 6:
            counts[6 - delta] += 1
    return counts


def compute_source_summary(
    source: str,
    scans: list[dict],
    opportunities: list[dict],
    enabled: bool,
) -> dict[str, Any]:
    """Combined per-source summary: status, last_fetch, today's metrics, 7-day series."""
    today = datetime.now(timezone.utc).date()

    # Today's catch
    today_count = 0
    today_value = 0
    for o in opportunities:
        if o.get("source") != source:
            continue
        parsed = _parse_iso(o.get("posted_date"))
        if parsed and parsed.date() == today:
            today_count += 1
            today_value += int(o.get("estimated_value_usd") or 0)

    # Most recent scan touching this source
    matching = [s for s in scans if source in (s.get("sources") or [])]
    matching.sort(
        key=lambda s: s.get("finished_at") or s.get("started_at") or s.get("created_at") or "",
        reverse=True,
    )
    most_recent = matching[0] if matching else None

    if most_recent is None:
        status = "idle"
        label = "idle"
        last_fetch = None
        last_error = None
    else:
        scan_status = most_recent.get("status") or ""
        if scan_status == "running":
            status, label = "live", "scraping"
        elif scan_status == "failed":
            status, label = "error", most_recent.get("error") or "blocked"
        else:
            status, label = "idle", "idle"
        last_fetch = most_recent.get("finished_at") or most_recent.get("started_at")
        last_error = most_recent.get("error") if scan_status == "failed" else None

    return {
        "source": source,
        "enabled": bool(enabled),
        "status": status,
        "label": label,
        "last_fetch": last_fetch,
        "last_error": last_error,
        "today_count": today_count,
        "today_value_usd": today_value,
        "seven_day_series": compute_seven_day_series(source, opportunities),
    }
