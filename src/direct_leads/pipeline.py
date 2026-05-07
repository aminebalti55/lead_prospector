"""Direct-leads scrape pipeline — Supabase-backed.

Per-source scrape → dedup against existing opportunities → recency filter →
score with RelevanceMatcher → enrich → bulk-upsert into the `opportunities`
table. Returns the list of opportunity IDs written.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta

from src.core.config import settings
from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine
from src.direct_leads.enricher import LeadEnricher
from src.direct_leads.matcher import RelevanceMatcher
from src.direct_leads.scrapers.clutch import ClutchScraper
from src.direct_leads.scrapers.goodfirms import GoodFirmsScraper
from src.direct_leads.scrapers.indeed import IndeedScraper
from src.direct_leads.scrapers.linkedin_jobs import LinkedInJobsScraper
from src.direct_leads.scrapers.linkedin_posts import LinkedInPostsScraper
from src.direct_leads.scrapers.reddit import RedditScraper
from src.direct_leads.scrapers.remoteok import RemoteOKScraper
from src.direct_leads.scrapers.tanit import TanitScraper
from src.direct_leads.scrapers.twitter import TwitterScraper

from backend.services.opportunities_store import (
    direct_lead_to_row,
    existing_urls,
    upsert,
)

logger = logging.getLogger(__name__)

SCRAPER_CLASSES = {
    "reddit": RedditScraper,
    "indeed": IndeedScraper,
    "linkedin": LinkedInJobsScraper,
    "linkedin_posts": LinkedInPostsScraper,
    "clutch": ClutchScraper,
    "goodfirms": GoodFirmsScraper,
    "twitter": TwitterScraper,
    "tanit": TanitScraper,
    "remoteok": RemoteOKScraper,
}


class DirectLeadsPipeline:
    def __init__(self, engine: ScraperEngine | None = None):
        self.engine = engine or ScraperEngine()
        self.matcher = RelevanceMatcher()
        self.enricher = LeadEnricher()

    async def run(
        self,
        keywords: list[str],
        sources: list[str] | None = None,
        max_results: int = 20,
        progress_callback=None,
        source_configs: dict | None = None,
        scan_id: str | None = None,
    ) -> list[str]:
        """Scrape, score, enrich, and persist. Returns the IDs written to
        Supabase (so the caller can update its scan record's `leads_found`)."""
        active_sources = sources or list(SCRAPER_CLASSES.keys())
        already_have = existing_urls()
        source_configs = source_configs or {}

        max_concurrent = max(1, int(
            getattr(settings.scraping, "max_concurrent_scrapers", 3) or 3
        ))
        sem = asyncio.Semaphore(max_concurrent)

        async def _run_one(source_name: str) -> list[DirectLead]:
            if source_name not in SCRAPER_CLASSES:
                logger.warning(f"Unknown source: {source_name}")
                return []
            async with sem:
                if progress_callback:
                    progress_callback(f"Scanning {source_name}...")
                try:
                    scraper = SCRAPER_CLASSES[source_name](self.engine)
                    config = source_configs.get(source_name, {})
                    search_kwargs = {"keywords": keywords, "max_results": max_results}
                    if config.get("country"):
                        search_kwargs["country"] = config["country"]
                    leads = await scraper.search(**search_kwargs)
                    logger.info(f"[{source_name}] Found {len(leads)} leads")
                    return leads
                except Exception as e:
                    logger.error(f"[{source_name}] Scraper failed: {e}")
                    return []

        results = await asyncio.gather(*[_run_one(s) for s in active_sources])
        all_leads: list[DirectLead] = [lead for batch in results for lead in batch]

        unique = self._deduplicate(all_leads, already_have)
        logger.info(f"Unique leads after dedup: {len(unique)}")

        unique = self._filter_recent(unique)
        logger.info(f"Leads after recency filter: {len(unique)}")

        for lead in unique:
            self._score_lead(lead)

        # Quality gate — drop leads that don't plausibly match the user's
        # skill profile. Without this, weak per-source filters (Tanit's
        # q-param, Indeed's loose keyword matching) flood the inbox with
        # cleaning, sales, and admin jobs.
        min_score = int(getattr(settings.direct_leads, "min_relevance_score", 15) or 15)
        before = len(unique)
        unique = [l for l in unique if l.relevance_score >= min_score]
        dropped = before - len(unique)
        if dropped:
            logger.info(f"Dropped {dropped} low-relevance leads (score < {min_score})")

        if progress_callback:
            progress_callback("Enriching leads...")
        unique = self.enricher.enrich_many(unique)

        unique.sort(key=lambda l: l.relevance_score, reverse=True)

        if not unique:
            return []

        rows = [direct_lead_to_row(l, scan_id=scan_id) for l in unique]
        upsert(rows)
        logger.info(f"Persisted {len(rows)} direct leads to Supabase")
        return [r["id"] for r in rows]

    # ------------------------------------------------------------------

    def _deduplicate(
        self, leads: list[DirectLead], existing: set[str]
    ) -> list[DirectLead]:
        seen = set(existing)
        unique = []
        for lead in leads:
            if lead.url and lead.url not in seen:
                seen.add(lead.url)
                unique.append(lead)
        return unique

    def _filter_recent(self, leads: list[DirectLead]) -> list[DirectLead]:
        max_age = int(getattr(settings.direct_leads, "max_age_days", 30) or 30)
        cutoff = datetime.now() - timedelta(days=max_age)
        kept: list[DirectLead] = []
        dropped = 0
        for lead in leads:
            if lead.posted_date is None:
                kept.append(lead)  # agency listings have no posted_date
                continue
            posted_naive = (
                lead.posted_date.replace(tzinfo=None)
                if lead.posted_date.tzinfo
                else lead.posted_date
            )
            if posted_naive >= cutoff:
                kept.append(lead)
            else:
                dropped += 1
        if dropped:
            logger.info(f"Dropped {dropped} stale leads (>{max_age}d old)")
        return kept

    def _score_lead(self, lead: DirectLead) -> None:
        hours_ago: float | None = None
        if lead.posted_date:
            now = datetime.now(tz=lead.posted_date.tzinfo) if lead.posted_date.tzinfo else datetime.now()
            hours_ago = (now - lead.posted_date).total_seconds() / 3600

        text = f"{lead.title} {lead.description}"
        lead.relevance_score = self.matcher.score(
            description=text,
            posted_hours_ago=hours_ago,
            has_budget=bool(lead.budget_signal),
            has_contact=bool(lead.contact_email or lead.contact_phone),
            is_remote="remote" in (lead.location or "").lower(),
        )
        lead.matched_skills = self.matcher.get_matched_skills(text)
        lead.budget_signal = self._detect_budget(lead.description) or ""
        lead.urgency_signal = self._detect_urgency(lead.description) or ""

    def _detect_budget(self, text: str) -> str | None:
        text = (text or "").lower()
        amounts = re.findall(r"\$[\d,]+", text)
        if amounts:
            for a in amounts:
                val = int(a.replace("$", "").replace(",", ""))
                if val >= 5000:
                    return "high"
                if val >= 1000:
                    return "medium"
                return "low"
        if any(w in text for w in ["budget", "pay well", "competitive rate"]):
            return "medium"
        return None

    def _detect_urgency(self, text: str) -> str | None:
        text = (text or "").lower()
        if any(w in text for w in ["asap", "urgent", "immediately", "this week"]):
            return "urgent"
        if any(w in text for w in ["soon", "next week", "within a month"]):
            return "normal"
        return None
