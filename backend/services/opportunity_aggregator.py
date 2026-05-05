"""Convert ProcessedLead (cold) and DirectLead (direct) rows into a unified
Opportunity shape for the Pulse UI."""
from __future__ import annotations

import re
from typing import Any

from src.core.models import DirectLead, Opportunity, Stage, OpportunityType


# Map legacy outreach_status values to canonical Stage values.
_STAGE_ALIASES: dict[str, str] = {
    "new": Stage.NEW.value,
    "queued": Stage.NEW.value,
    "researching": Stage.RESEARCHING.value,
    "contacted": Stage.CONTACTED.value,
    "replied": Stage.REPLIED.value,
    "meeting": Stage.MEETING.value,
    "won": Stage.WON.value,
    "converted": Stage.WON.value,
    "lost": Stage.LOST.value,
    "passed": Stage.LOST.value,
}


def _normalize_stage(raw: str | None) -> str:
    if not raw:
        return Stage.NEW.value
    return _STAGE_ALIASES.get(raw.lower().strip(), Stage.NEW.value)


def _priority_from_score(score: int) -> str:
    if score >= 60:
        return "hot"
    if score >= 35:
        return "warm"
    return "cold"


# Sources we consider "direct leads" (jobs/gigs) vs "cold prospects" (local biz).
# Used by estimate_value_usd as a baseline.
_DIRECT_SOURCES = {"reddit", "linkedin", "linkedin_posts", "indeed", "twitter", "clutch", "goodfirms", "tanit"}

# Baseline $ value when no budget signal is available.
_BASELINE_VALUE: dict[tuple[str, str], int] = {
    # (kind, priority): usd
    ("direct", "hot"): 2500,
    ("direct", "warm"): 1500,
    ("direct", "cold"): 800,
    ("cold", "hot"): 4000,
    ("cold", "warm"): 2000,
    ("cold", "cold"): 1000,
}


# Matches plain numbers (with optional thousands separators) optionally preceded
# by $ or followed by USD / k suffix.  We intentionally keep this simple and
# apply range-filtering (100–500 000) to weed out false positives.
# Group 1: $-prefixed number (e.g. $3,000 or $3000 or $1500)
# Group 2: number followed by USD or k suffix (e.g. 2000 USD, 5k)
_DOLLAR_PATTERN = re.compile(
    r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)"   # $3,000  or  $3000  or  $1500
    r"|(\d{1,3}(?:,\d{3})+|\d+)\s*(?:usd\b|k\b)",  # 2000 USD  or  5k
    re.IGNORECASE,
)


def estimate_value_usd(budget_signal: str, source: str, priority: str) -> int:
    """Best-effort dollar estimate for an opportunity.

    1. If `budget_signal` contains a recognizable dollar amount, parse it.
    2. Otherwise fall back to a baseline keyed by source-kind and priority.
    """
    if budget_signal:
        candidates: list[int] = []
        for m in _DOLLAR_PATTERN.finditer(budget_signal):
            # group 1 → $-prefixed, group 2 → number-with-suffix
            raw = (m.group(1) or m.group(2)).replace(",", "")
            try:
                n = int(raw)
            except ValueError:
                continue
            # Check for 'k' suffix right after the match
            tail = budget_signal[m.end(): m.end() + 2].lower()
            if tail.startswith("k"):
                n *= 1000
            # Also handle the 'k' already captured in group 2 suffix
            full_match = m.group(0).lower()
            if full_match.endswith("k"):
                n *= 1000
            if 100 <= n <= 500_000:
                candidates.append(n)
        if candidates:
            return max(candidates)

    kind = "direct" if source.lower() in _DIRECT_SOURCES else "cold"
    return _BASELINE_VALUE.get((kind, priority), 1000)


def direct_lead_to_opportunity(lead: DirectLead, source_file: str) -> Opportunity:
    """Convert a DirectLead dataclass into an Opportunity."""
    priority = _priority_from_score(lead.relevance_score)
    return Opportunity(
        id=lead.lead_id,
        type=OpportunityType.DIRECT.value,
        source=lead.source,
        title=lead.title,
        description=lead.description or "",
        url=lead.url,
        posted_date=lead.posted_date.isoformat() if lead.posted_date else None,
        company_name=lead.company_name or "",
        location=lead.location or "",
        contact_email=lead.contact_email or "",
        contact_phone=lead.contact_phone or "",
        score=int(lead.relevance_score or 0),
        priority=priority,
        stage=_normalize_stage(lead.outreach_status),
        estimated_value_usd=estimate_value_usd(lead.budget_signal, lead.source, priority),
        matched_skills=list(lead.matched_skills or []),
        budget_signal=lead.budget_signal or "",
        urgency_signal=lead.urgency_signal or "",
        pain_tags=[],
        notes=lead.notes or "",
        source_file=source_file,
        raw_lead_id=lead.lead_id,
    )


def cold_row_to_opportunity(row: dict[str, Any], source_file: str) -> Opportunity:
    """Convert a row dict (as read from the cold outreach Excel files) into an Opportunity."""
    score = int(row.get("Total_Score") or 0)
    priority = (row.get("Priority") or _priority_from_score(score)).lower()
    pain_tags_str = row.get("Pain_Tags_Str") or ""
    pain_tags = [t.strip() for t in pain_tags_str.split(",") if t.strip()]
    city = row.get("City") or ""
    state = row.get("State") or ""
    location = ", ".join(p for p in [city, state] if p)

    return Opportunity(
        id=str(row.get("Lead_ID") or ""),
        type=OpportunityType.COLD.value,
        source=row.get("Source") or "directory",
        title=row.get("Business_Name") or "",
        description=row.get("Offer_Reasoning") or "",
        url=row.get("Website") or "",
        posted_date=None,
        company_name=row.get("Business_Name") or "",
        location=location,
        contact_email=row.get("Email") or "",
        contact_phone=row.get("Phone") or "",
        score=score,
        priority=priority,
        stage=_normalize_stage(row.get("Outreach_Status")),
        estimated_value_usd=estimate_value_usd("", row.get("Source") or "google_maps", priority),
        matched_skills=[],
        budget_signal="",
        urgency_signal="",
        pain_tags=pain_tags,
        notes=row.get("Notes") or "",
        source_file=source_file,
        raw_lead_id=str(row.get("Lead_ID") or ""),
    )
