"""One-shot data migration: Excel + JSON → Supabase.

Reads every existing output file and inserts rows into the corresponding
Supabase tables. Idempotent — uses upsert(on=primary_key) so re-running
the script doesn't create duplicates.

Run with:
    .venv/Scripts/python.exe scripts/migrate_to_supabase.py

Reports per-table inserted / skipped / failed counts at the end.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Project root sits one level above this script.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.supabase_client import get_client


COLD_DIR = PROJECT_ROOT / "output" / "cold"
DIRECT_DIR = PROJECT_ROOT / "output" / "direct"
LEGACY_DIR = PROJECT_ROOT / "output" / "legacy"


def _clean(v: Any) -> Any:
    """Convert pandas / Excel-isms (NaN, NaT) into JSON-friendly None / strings."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.isoformat() if not pd.isna(v) else None
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [x for x in v if x not in (None, "")]
    return v


def _str(v: Any) -> str:
    v = _clean(v)
    return "" if v is None else str(v)


def _maybe_int(v: Any) -> int | None:
    v = _clean(v)
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _maybe_float(v: Any) -> float | None:
    v = _clean(v)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _maybe_bool(v: Any) -> bool | None:
    v = _clean(v)
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if s in ("true", "yes", "1"):
        return True
    if s in ("false", "no", "0"):
        return False
    return None


def _split_pain(s: Any) -> list[str]:
    s = _clean(s)
    if not s:
        return []
    return [t.strip() for t in str(s).split(",") if t.strip()]


def _make_id(source: str, url: str) -> str:
    """Same lead_id formula as DirectLead.__post_init__."""
    return hashlib.sha1(f"{source}|{url}".encode("utf-8")).hexdigest()


def _normalize_stage(raw: str | None) -> str:
    s = (raw or "new").strip().lower()
    return {
        "queued": "new", "converted": "won", "passed": "lost",
    }.get(s, s)


def _priority_from_score(score: int) -> str:
    if score >= 60:
        return "hot"
    if score >= 35:
        return "warm"
    return "cold"


# =============================================================================
# Cold-prospect file → opportunities row
# =============================================================================


def cold_row_to_opp(row: dict, source_file: str) -> dict | None:
    """Cold-pipeline Excel row → opportunities row."""
    name = _str(row.get("Business_Name"))
    if not name:
        return None

    # Build a stable lead_id. Cold rows already have a Lead_ID; reuse it.
    lead_id = _str(row.get("Lead_ID")) or _make_id(
        _str(row.get("Source")) or "directory",
        _str(row.get("Yelp_URL")) or _str(row.get("Website")) or name,
    )

    score = _maybe_int(row.get("Score")) or 0
    priority_raw = _str(row.get("Priority")).lower() or _priority_from_score(score)
    priority = priority_raw if priority_raw in ("hot", "warm", "cold") else "cold"

    return {
        "id": lead_id,
        "type": "cold",
        "source": _str(row.get("Source")) or "directory",
        "lead_subtype": "prospect",  # cold leads are prospects, not job posts
        "title": name,
        "description": _str(row.get("Offer_Reasoning")),
        "url": _str(row.get("Website")) or _str(row.get("Yelp_URL")),
        "company_name": name,
        "company_website": _str(row.get("Website")),
        "location": ", ".join([p for p in [_str(row.get("City")), _str(row.get("State"))] if p]),
        "city": _str(row.get("City")),
        "state": _str(row.get("State")),
        "niche": _str(row.get("Niche")),
        "contact_email": _str(row.get("Email")),
        "contact_phone": _str(row.get("Phone")),
        "email_source": _str(row.get("Email_Source")),
        "email_confidence": _str(row.get("Email_Confidence")),
        "score": score,
        "priority": priority,
        "stage": _normalize_stage(_str(row.get("Outreach_Status"))),
        "estimated_value_usd": 2000,  # default cold-prospect estimate
        "pain_tags": _split_pain(row.get("Pain_Tags")),
        "has_website": bool(_str(row.get("Website"))),
        "has_ssl": _maybe_bool(row.get("Has_SSL")),
        "has_booking_cta": _maybe_bool(row.get("Has_Booking_CTA")),
        "has_contact_form": _maybe_bool(row.get("Has_Contact_Form")),
        "is_mobile_friendly": _maybe_bool(row.get("Mobile_Friendly")),
        "page_load_time_ms": _maybe_int(row.get("Page_Load_ms")),
        "ops_pain_count": _maybe_int(row.get("Ops_Pain_Mentions")) or 0,
        "conversion_pain_count": _maybe_int(row.get("Conversion_Pain_Mentions")) or 0,
        "negative_review_count": _maybe_int(row.get("Negative_Reviews")) or 0,
        "google_rating": _maybe_float(row.get("Google_Rating")),
        "google_review_count": _maybe_int(row.get("Google_Reviews")),
        "yelp_rating": _maybe_float(row.get("Yelp_Rating")),
        "yelp_review_count": _maybe_int(row.get("Yelp_Reviews")),
        "notes": _str(row.get("Notes")),
        "owner": _str(row.get("Owner")),
        "last_contacted": _clean(row.get("Last_Contacted")),
        "follow_up_date": _clean(row.get("Follow_Up_Date")),
        "source_file": source_file,
    }


# =============================================================================
# Direct-lead file → opportunities row
# =============================================================================


def direct_row_to_opp(row: dict, source_file: str) -> dict | None:
    title = _str(row.get("Title"))
    url = _str(row.get("URL"))
    if not title and not url:
        return None

    source = _str(row.get("Source"))
    lead_id = _str(row.get("Lead_ID")) or _make_id(source, url)
    score = _maybe_int(row.get("Relevance_Score")) or 0
    priority = _priority_from_score(score)

    return {
        "id": lead_id,
        "type": "direct",
        "source": source,
        "lead_subtype": _str(row.get("Lead_Subtype")) or "hiring",
        "title": title,
        "description": _str(row.get("Description")),
        "url": url,
        "posted_date": _clean(row.get("Posted_Date")),
        "company_name": _str(row.get("Company")),
        "company_website": _str(row.get("Company_Website")),
        "location": _str(row.get("Location")),
        "contact_name": _str(row.get("Contact_Name")),
        "contact_email": _str(row.get("Contact_Email")),
        "contact_phone": _str(row.get("Contact_Phone")),
        "score": score,
        "priority": priority,
        "stage": _normalize_stage(_str(row.get("Outreach_Status"))),
        "estimated_value_usd": 1500 if priority == "hot" else 800,
        "matched_skills": _split_pain(row.get("Matched_Skills")),
        "budget_signal": _str(row.get("Budget_Signal")),
        "urgency_signal": _str(row.get("Urgency_Signal")),
        "notes": _str(row.get("Notes")),
        "source_file": source_file,
    }


# =============================================================================
# Migration
# =============================================================================


def migrate_excel_files(client, directory: Path, converter) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    if not directory.exists():
        return 0, 0
    for xlsx in sorted(directory.glob("*.xlsx")):
        try:
            df = pd.read_excel(xlsx)
        except Exception as e:
            print(f"  ! could not read {xlsx.name}: {e}")
            continue
        rows: list[dict] = []
        for _, raw in df.iterrows():
            opp = converter(raw.to_dict(), xlsx.name)
            if opp:
                rows.append(opp)
            else:
                skipped += 1
        if not rows:
            continue
        # Upsert in chunks of 100 — Supabase REST limit on payload size.
        for i in range(0, len(rows), 100):
            chunk = rows[i : i + 100]
            try:
                client.table("opportunities").upsert(
                    chunk, on_conflict="id"
                ).execute()
                inserted += len(chunk)
            except Exception as e:
                print(f"  ! upsert chunk failed for {xlsx.name}: {e}")
                skipped += len(chunk)
        print(f"  + {xlsx.name}: {len(rows)} rows queued")
    return inserted, skipped


def migrate_scans(client) -> int:
    scans_file = DIRECT_DIR / "scans.json"
    if not scans_file.exists():
        return 0
    try:
        scans = json.loads(scans_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ! scans.json parse failed: {e}")
        return 0

    rows: list[dict] = []
    for s in scans:
        legacy_id = s.get("id")
        if not legacy_id:
            continue
        rows.append({
            # Legacy IDs are 8-char hex; we store them as a deterministic UUID
            # by padding to 32 hex chars then formatting. Avoids gen_random_uuid
            # collisions while preserving the human-readable suffix.
            "id": _legacy_id_to_uuid(legacy_id),
            "type": "direct",
            "status": s.get("status") or "completed",
            "sources": s.get("sources") or [],
            "keywords": s.get("keywords") or [],
            "max_results": s.get("max_results") or 50,
            "progress": s.get("progress") or 0,
            "leads_found": s.get("leads_found") or 0,
            "logs": s.get("logs") or [],
            "error": s.get("error"),
            "output_files": s.get("output_files") or [],
            "created_at": s.get("created_at"),
            "started_at": s.get("started_at"),
            "finished_at": s.get("finished_at"),
        })
    if not rows:
        return 0
    try:
        client.table("scans").upsert(rows, on_conflict="id").execute()
    except Exception as e:
        print(f"  ! scans upsert failed: {e}")
        return 0
    return len(rows)


def migrate_saved_searches(client) -> int:
    f = DIRECT_DIR / "saved_searches.json"
    if not f.exists():
        return 0
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ! saved_searches.json parse failed: {e}")
        return 0

    rows: list[dict] = []
    for s in data:
        legacy_id = s.get("id")
        if not legacy_id:
            continue
        rows.append({
            "id": _legacy_id_to_uuid(legacy_id),
            "name": s.get("name") or "Untitled search",
            "type": "direct",
            "keywords": s.get("keywords") or [],
            "sources": s.get("sources") or [],
            "frequency": s.get("frequency") or "daily",
            "max_results": s.get("max_results") or 50,
            "is_paused": bool(s.get("is_paused")),
            "last_run_at": s.get("last_run_at"),
        })
    if not rows:
        return 0
    try:
        client.table("saved_searches").upsert(rows, on_conflict="id").execute()
    except Exception as e:
        print(f"  ! saved_searches upsert failed: {e}")
        return 0
    return len(rows)


def _legacy_id_to_uuid(legacy_id: str) -> str:
    """Convert short legacy IDs like '9d0a4635' into deterministic UUIDs so
    we don't lose the link between Excel-era references and Supabase rows."""
    h = hashlib.md5(legacy_id.encode("utf-8")).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# =============================================================================
# Entrypoint
# =============================================================================


def main():
    client = get_client()

    print(">> Migrating cold-prospect leads (Excel)…")
    cold_in, cold_skip = migrate_excel_files(client, COLD_DIR, cold_row_to_opp)
    if LEGACY_DIR.exists():
        legacy_in, legacy_skip = migrate_excel_files(client, LEGACY_DIR, cold_row_to_opp)
        cold_in += legacy_in
        cold_skip += legacy_skip

    print(">> Migrating direct (job) leads (Excel)…")
    direct_in, direct_skip = migrate_excel_files(client, DIRECT_DIR, direct_row_to_opp)

    print(">> Migrating scan history…")
    scans_in = migrate_scans(client)

    print(">> Migrating saved searches…")
    searches_in = migrate_saved_searches(client)

    print()
    print("=" * 56)
    print(f"  Cold opportunities inserted/upserted:   {cold_in}")
    print(f"  Direct opportunities inserted/upserted: {direct_in}")
    print(f"  Scans inserted/upserted:                {scans_in}")
    print(f"  Saved searches inserted/upserted:       {searches_in}")
    print(f"  Skipped rows (missing required fields): {cold_skip + direct_skip}")
    print("=" * 56)


if __name__ == "__main__":
    main()
