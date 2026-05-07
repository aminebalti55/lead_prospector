"""Cold-outreach router — Supabase-backed.

- POST /scans       create + dispatch a cold scrape job
- GET  /scans       list recent scan records
- GET  /scans/{id}  one scan
- GET  /leads       all cold opportunities
- GET  /leads/{id}  one
- PATCH /leads/{id} partial update (notes, stage, owner, …)
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from backend.services import scans_store
from backend.services.supabase_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cold", tags=["cold-outreach"])


_DEFAULT_NICHES = ["plumbing"]
_DEFAULT_SCRAPERS = ["google_maps", "yelp", "yellowpages", "bbb", "manta"]


# Display labels for the predefined niche dictionary in src.core.config.
# These power the cold-scan niche picker in the UI.
_NICHE_DISPLAY = {
    "plumbing": {"label": "Plumbing", "tier": 1, "category": "Home services"},
    "hvac": {"label": "HVAC", "tier": 1, "category": "Home services"},
    "roofing": {"label": "Roofing", "tier": 1, "category": "Home services"},
    "pest_control": {"label": "Pest control", "tier": 1, "category": "Home services"},
    "dental": {"label": "Dental clinic", "tier": 1, "category": "Healthcare"},
    "cosmetic_dentist": {"label": "Cosmetic dentist", "tier": 1, "category": "Healthcare"},
    "med_spa": {"label": "Med spa", "tier": 1, "category": "Healthcare"},
    "personal_injury_lawyer": {"label": "Personal injury lawyer", "tier": 1, "category": "Legal"},
    "real_estate": {"label": "Real estate", "tier": 2, "category": "Other"},
    "auto_repair": {"label": "Auto repair", "tier": 2, "category": "Other"},
}


@router.get("/niches")
async def list_niches() -> dict:
    """Predefined niches for cold outreach. UI uses these in the niche picker."""
    from src.core.config import settings
    out = []
    for key, keywords in (settings.search.niches or {}).items():
        meta = _NICHE_DISPLAY.get(key, {"label": key.title(), "tier": 3, "category": "Other"})
        out.append({
            "key": key,
            "label": meta["label"],
            "tier": meta["tier"],
            "category": meta["category"],
            "keywords": list(keywords or []),
        })
    out.sort(key=lambda n: (n["tier"], n["category"], n["label"]))
    return {"niches": out}


# ── Scan endpoints ────────────────────────────────────────────────────


@router.post("/scans")
async def create_scan(body: dict):
    locations = body.get("locations") or []
    niches = body.get("niches") or _DEFAULT_NICHES
    if not locations:
        raise HTTPException(
            status_code=400,
            detail="At least one location is required (e.g. 'Austin, TX').",
        )

    scan = scans_store.create({
        "type": "cold",
        "status": "queued",
        "sources": _DEFAULT_SCRAPERS,
        "locations": locations,
        "niches": niches,
        "max_results": int(body.get("max_results") or 20),
    })

    asyncio.create_task(_execute_scan(scan["id"], {
        "locations": locations,
        "niches": niches,
        "skip_scrapers": body.get("skip_scrapers") or [],
        "skip_audit": bool(body.get("skip_audit") or False),
        "fetch_emails": bool(body.get("fetch_emails", True)),
        "fetch_details": bool(body.get("fetch_details", True)),
        "max_results": int(body.get("max_results") or 20),
    }))

    return {"scan_id": scan["id"], "status": "queued", "message": "Scan started"}


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str):
    s = scans_store.get(scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    return s


@router.get("/scans")
async def list_scans():
    return {"scans": scans_store.list_all(limit=50)}


# ── Scan execution (background task) ────────────────────────────────


async def _execute_scan(scan_id: str, params: dict) -> None:
    scans_store.mark_running(scan_id)
    locations = params["locations"]
    niches = params["niches"]
    scans_store.set_phase(
        scan_id,
        f"Scraping {len(niches)} niche(s) across {len(locations)} location(s)…",
        progress=10,
    )

    try:
        from src.cold_outreach.pipeline import ColdOutreachPipeline

        pipeline = ColdOutreachPipeline()

        def on_progress(msg: str):
            scans_store.append_log(scan_id, msg)
            logger.info(f"[COLD-SCAN {scan_id}] {msg}")
            # Promote pipeline events into structured phase updates.
            low = msg.lower()
            if low.startswith("scraping "):
                # "Scraping plumbing in Austin, TX..."
                scans_store.set_phase(scan_id, msg.rstrip(".…"), progress=20)
            elif "email extraction:" in low:
                # "Email extraction: 26/76 extracted, 8 safe-to-send"
                scans_store.set_phase(scan_id, msg, progress=85)
            elif "persisted" in low and "to supabase" in low:
                scans_store.set_phase(scan_id, "Persisting to database", progress=95)

        ids = await pipeline.run(
            locations=locations,
            niches=niches,
            max_results=params["max_results"],
            skip_scrapers=params.get("skip_scrapers") or [],
            skip_audit=params.get("skip_audit") or False,
            fetch_emails=params.get("fetch_emails", True),
            fetch_details=params.get("fetch_details", True),
            progress_callback=on_progress,
            scan_id=scan_id,
        )

        # How many of those have an email? Useful surfacing for the UI.
        emails_count = 0
        if ids:
            resp = (
                get_client()
                .table("opportunities")
                .select("id", count="exact")
                .in_("id", ids[:200])  # PostgREST `in` cap is generous; chunk just in case
                .neq("contact_email", "")
                .execute()
            )
            emails_count = resp.count or 0

        scans_store.mark_completed(
            scan_id, leads_found=len(ids), emails_extracted=emails_count
        )
        scans_store.set_phase(
            scan_id,
            f"Done — {len(ids)} prospects, {emails_count} with email",
            progress=100,
        )
        scans_store.append_log(
            scan_id,
            f"Done — {len(ids)} prospects persisted, {emails_count} with email.",
        )
        logger.info(f"[COLD-SCAN {scan_id}] Completed: {len(ids)} leads")

    except Exception as e:
        logger.error(f"[COLD-SCAN {scan_id}] Failed: {e}", exc_info=True)
        scans_store.mark_failed(scan_id, str(e))
        scans_store.append_log(scan_id, f"Error: {e}")


# ── Lead endpoints ────────────────────────────────────────────────────


@router.get("/leads")
async def list_cold_leads():
    resp = (
        get_client()
        .table("opportunities")
        .select(
            "id, source, title, description, url, "
            "contact_email, contact_phone, email_source, email_confidence, "
            "stage, score, priority, "
            "company_name, location, city, state, niche, "
            "pain_tags, has_website, has_ssl, "
            "google_rating, google_review_count, yelp_rating, yelp_review_count",
            count="exact",
        )
        .eq("type", "cold")
        .order("score", desc=True)
        .limit(500)
        .execute()
    )
    return {"leads": resp.data or [], "total": resp.count or 0}


@router.get("/leads/{lead_id}")
async def get_cold_lead(lead_id: str):
    resp = (
        get_client()
        .table("opportunities")
        .select("*")
        .eq("id", lead_id)
        .eq("type", "cold")
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Lead not found")
    return rows[0]


@router.patch("/leads/{lead_id}")
async def update_cold_lead(lead_id: str, body: dict):
    allowed = {
        "stage", "notes", "owner", "last_contacted", "follow_up_date",
        "contact_email", "contact_phone",
    }
    payload = {k: v for k, v in body.items() if k in allowed}
    if not payload:
        return {"ok": True}
    resp = (
        get_client()
        .table("opportunities")
        .update(payload)
        .eq("id", lead_id)
        .eq("type", "cold")
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"ok": True}
