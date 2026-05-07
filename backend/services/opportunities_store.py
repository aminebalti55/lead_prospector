"""Opportunities — Supabase-backed write helpers used by the scrape pipelines.

The opportunities router handles reads + stage updates; this module handles
the bulk insert path that pipelines use to persist newly-scraped leads.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Iterable

from src.core.models import BusinessLead, DirectLead, ProcessedLead

from backend.services.supabase_client import get_client


_CHUNK = 100


def _stable_id(source: str, url: str) -> str:
    """Same formula as DirectLead.__post_init__ — sha1(source|url)."""
    return hashlib.sha1(f"{source}|{url}".encode("utf-8")).hexdigest()


def _priority_from_score(score: int) -> str:
    if score >= 60:
        return "hot"
    if score >= 35:
        return "warm"
    return "cold"


def direct_lead_to_row(lead: DirectLead, scan_id: str | None = None) -> dict[str, Any]:
    score = int(lead.relevance_score or 0)
    return {
        "id": lead.lead_id,
        "type": "direct",
        "source": lead.source,
        "lead_subtype": lead.lead_subtype or "hiring",
        "title": lead.title or "",
        "description": (lead.description or "")[:8000],
        "url": lead.url or "",
        "posted_date": lead.posted_date.isoformat() if lead.posted_date else None,
        "company_name": lead.company_name or "",
        "company_website": lead.company_website or "",
        "company_size": lead.company_size or "",
        "location": lead.location or "",
        "contact_name": lead.contact_name or "",
        "contact_email": lead.contact_email or "",
        "contact_phone": lead.contact_phone or "",
        "score": score,
        "priority": _priority_from_score(score),
        "stage": (lead.outreach_status or "new"),
        "estimated_value_usd": 1500 if score >= 60 else 800,
        "matched_skills": list(lead.matched_skills or []),
        "budget_signal": lead.budget_signal or "",
        "urgency_signal": lead.urgency_signal or "",
        "notes": lead.notes or "",
        "scan_id": scan_id,
    }


def cold_lead_to_row(
    business: BusinessLead,
    processed: ProcessedLead,
    niche: str,
    scan_id: str | None = None,
) -> dict[str, Any]:
    """Pair a BusinessLead (scrape source) with the matching ProcessedLead
    (audit + score) into a single opportunities row."""
    src = business.source or "directory"
    url = (business.website or "").strip() or (business.detail_url or "").strip()
    lead_id = _stable_id(src, url or business.name)
    score = int(processed.total_score or 0)
    return {
        "id": lead_id,
        "type": "cold",
        "source": src,
        "lead_subtype": "prospect",
        "title": business.name or "",
        "description": processed.offer_reasoning or "",
        "url": business.website or "",
        "company_name": business.name or "",
        "company_website": business.website or "",
        "location": ", ".join(p for p in [business.city, business.state] if p),
        "city": business.city or "",
        "state": business.state or "",
        "niche": niche,
        "contact_email": processed.email or "",
        "contact_phone": business.phone or "",
        "email_source": processed.email_source or "",
        "email_confidence": processed.email_confidence or "",
        "email_verification_status": processed.email_verification_status or None,
        "score": score,
        "priority": (processed.priority or _priority_from_score(score)),
        "stage": (processed.outreach_status or "new"),
        "estimated_value_usd": 2000,
        "pain_tags": list(processed.pain_tags or []),
        "has_website": bool(business.website),
        "has_ssl": processed.has_ssl,
        "has_booking_cta": processed.has_booking_cta,
        "has_contact_form": processed.has_contact_form,
        "is_mobile_friendly": processed.is_mobile_friendly,
        "page_load_time_ms": processed.page_load_time_ms,
        "ops_pain_count": int(processed.ops_pain_count or 0),
        "conversion_pain_count": int(processed.conversion_pain_count or 0),
        "negative_review_count": int(processed.negative_review_count or 0),
        "google_rating": processed.google_rating,
        "google_review_count": int(processed.google_review_count or 0),
        "yelp_rating": processed.yelp_rating,
        "yelp_review_count": int(processed.yelp_review_count or 0),
        "notes": processed.notes or "",
        "scan_id": scan_id,
    }


def upsert(rows: Iterable[dict[str, Any]]) -> int:
    """Bulk-upsert opportunities. Returns count successfully written.
    Idempotent — re-running a scan that finds the same leads doesn't
    duplicate them, just refreshes mutable fields like score / contact info."""
    rows = [r for r in rows if r and r.get("id")]
    if not rows:
        return 0
    client = get_client()
    written = 0
    for i in range(0, len(rows), _CHUNK):
        chunk = rows[i:i + _CHUNK]
        client.table("opportunities").upsert(chunk, on_conflict="id").execute()
        written += len(chunk)
    return written


def existing_urls(source: str | None = None) -> set[str]:
    """Set of URLs already in opportunities — used by direct-leads pipeline
    to skip leads we already have. Source filter narrows to the scrape's
    own-source range so unrelated sources don't suppress matches."""
    client = get_client()
    q = client.table("opportunities").select("url")
    if source:
        q = q.eq("source", source)
    resp = q.execute()
    return {r["url"] for r in (resp.data or []) if r.get("url")}


def existing_business_keys() -> set[str]:
    """Returns name|city|state lower-cased keys for all cold opportunities —
    used by the cold pipeline's deduper."""
    resp = get_client().table("opportunities").select(
        "company_name, city, state"
    ).eq("type", "cold").execute()
    out: set[str] = set()
    for r in resp.data or []:
        name = (r.get("company_name") or "").strip().lower()
        city = (r.get("city") or "").strip().lower()
        state = (r.get("state") or "").strip().lower()
        if name:
            out.add(f"{name}|{city}|{state}")
    return out


def update_stage(opp_id: str, stage: str, *, last_contacted: bool = False) -> None:
    payload: dict[str, Any] = {"stage": stage}
    if last_contacted:
        payload["last_contacted"] = datetime.utcnow().isoformat()
    get_client().table("opportunities").update(payload).eq("id", opp_id).execute()
