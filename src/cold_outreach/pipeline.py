"""Cold-outreach scrape pipeline — Supabase-backed.

Per-niche / per-location scrape across YellowPages / Manta / BBB / Yelp /
Google Maps → dedup against existing cold opportunities → audit + score →
extract emails (4-layer extractor) → bulk-upsert into the `opportunities`
table. Returns the list of opportunity IDs written.
"""
from __future__ import annotations

import logging

from src.cold_outreach.auditor import WebsiteAuditor
from src.cold_outreach.email_extractor import EmailExtractor
from src.cold_outreach.scorer import LeadScorer, create_processed_lead
from src.cold_outreach.scrapers.bbb import BBBScraper
from src.cold_outreach.scrapers.google_maps import GoogleMapsScraper
from src.cold_outreach.scrapers.manta import MantaScraper
from src.cold_outreach.scrapers.yellowpages import YellowPagesScraper
from src.cold_outreach.scrapers.yelp import YelpScraper
from src.core.config import settings
from src.core.models import BusinessLead
from src.core.scraper_engine import ScraperEngine

from backend.services.email_verifier import verify as verify_email
from backend.services.opportunities_store import (
    cold_lead_to_row,
    existing_business_keys,
    upsert,
)

logger = logging.getLogger(__name__)

SCRAPER_CLASSES = {
    "google_maps": GoogleMapsScraper,
    "yelp": YelpScraper,
    "yellowpages": YellowPagesScraper,
    "bbb": BBBScraper,
    "manta": MantaScraper,
}


class ColdOutreachPipeline:
    """Orchestrates the full cold outreach pipeline."""

    def __init__(self, engine: ScraperEngine | None = None):
        self.engine = engine or ScraperEngine()
        self.scorer = LeadScorer()
        self.auditor = WebsiteAuditor()
        self.email_extractor = EmailExtractor(self.engine)

    async def run(
        self,
        locations: list[str],
        niches: list[str],
        max_results: int = 20,
        skip_scrapers: list[str] | None = None,
        skip_audit: bool = False,
        fetch_emails: bool = True,
        fetch_details: bool = True,
        progress_callback=None,
        scan_id: str | None = None,
    ) -> list[str]:
        """Scrape, score, enrich, and persist. Returns opportunity IDs written."""
        skip = set(skip_scrapers or [])
        existing = existing_business_keys()
        all_ids: list[str] = []

        for location in locations:
            city, state = self._parse_location(location)
            for niche in niches:
                if progress_callback:
                    progress_callback(f"Scraping {niche} in {city}, {state}...")

                # 1. Scrape every keyword variant per non-category source.
                # Google/Yelp use category IDs internally; YP/BBB/Manta search
                # by free text and benefit from each variant.
                raw_leads: list[BusinessLead] = []
                niche_keywords = settings.search.niches.get(niche, [niche]) or [niche]
                category_sources = {"google_maps", "yelp"}

                for name, cls in SCRAPER_CLASSES.items():
                    if name in skip:
                        continue
                    try:
                        scraper = cls(self.engine)
                        terms = (
                            niche_keywords[:1]
                            if name in category_sources
                            else niche_keywords
                        )
                        for search_term in terms:
                            leads = await scraper.search(
                                search_term, city, state, max_results
                            )
                            raw_leads.extend(leads)
                            logger.info(
                                f"[{name}] '{search_term}' -> {len(leads)} leads"
                            )
                    except Exception as e:
                        logger.error(f"[{name}] Scraper failed: {e}")

                # 2. Deduplicate against existing + within-batch.
                unique_leads = self._deduplicate(raw_leads, existing)
                logger.info(f"Unique leads after dedup: {len(unique_leads)}")

                # Track within-run keys so subsequent niches/locations don't re-add.
                for lead in unique_leads:
                    existing.add(self._lead_key(lead))

                # 3. Fetch details (website URLs) for sources that gate them.
                if fetch_details:
                    for scraper_name, cls in SCRAPER_CLASSES.items():
                        if scraper_name in skip:
                            continue
                        scraper = cls(self.engine)
                        if hasattr(scraper, "get_details"):
                            for lead in unique_leads:
                                if (
                                    lead.source == scraper_name
                                    and not lead.website
                                    and lead.detail_url
                                ):
                                    try:
                                        lead = await scraper.get_details(lead)
                                    except Exception:
                                        pass

                # 4. Audit + score → ProcessedLead. Pair with BusinessLead so
                # step 5's email extractor can pass detail_url + name.
                pairs: list[tuple[BusinessLead, object]] = []
                for lead in unique_leads:
                    audit_result = None
                    if not skip_audit and lead.website:
                        try:
                            audit_result = self.auditor.audit(lead.website)
                        except Exception:
                            pass

                    scoring = self.scorer.score_business(
                        website_audit=audit_result.__dict__ if audit_result else None,
                        rating=lead.rating,
                        review_count=lead.review_count or 0,
                        has_website=bool(lead.website),
                    )

                    pl = create_processed_lead(scoring_result=scoring, niche=niche)
                    pl.name = lead.name
                    pl.address = lead.address or ""
                    pl.city = lead.city
                    pl.state = lead.state
                    pl.phone = lead.phone or ""
                    pl.website = lead.website or ""
                    pl.source = lead.source
                    if lead.source == "google_maps":
                        pl.google_rating = lead.rating
                        pl.google_review_count = lead.review_count or 0
                    elif lead.source == "yelp":
                        pl.yelp_rating = lead.rating
                        pl.yelp_review_count = lead.review_count or 0

                    pairs.append((lead, pl))

                # 5. Email extraction (4-layer) + SMTP-handshake verification.
                if fetch_emails:
                    found = 0
                    verified = 0
                    for lead, pl in pairs:
                        if pl.email:
                            continue
                        if not pl.website and not lead.detail_url:
                            continue
                        result = await self.email_extractor.extract_async(
                            pl.website,
                            business_name=pl.name,
                            detail_url=lead.detail_url or "",
                        )
                        if result.email:
                            pl.email = result.email
                            pl.email_source = result.source
                            pl.email_confidence = result.confidence
                            found += 1
                            # Verify before we ever try to send to it. Bouncing
                            # 2%+ of a campaign destroys the sender domain.
                            try:
                                vr = verify_email(result.email)
                                pl.email_verification_status = vr.status
                                if vr.status in ("valid", "catch_all"):
                                    verified += 1
                            except Exception as e:
                                logger.debug(f"Verify failed for {result.email}: {e}")
                    logger.info(
                        f"Email extraction: {found}/{len(pairs)} extracted, "
                        f"{verified} safe-to-send"
                    )

                # 6. Persist to Supabase.
                if pairs:
                    rows = [
                        cold_lead_to_row(lead, pl, niche=niche, scan_id=scan_id)
                        for lead, pl in pairs
                    ]
                    upsert(rows)
                    logger.info(
                        f"Persisted {len(rows)} cold leads "
                        f"({niche} / {city}, {state}) to Supabase"
                    )
                    all_ids.extend(r["id"] for r in rows)

        return all_ids

    # ------------------------------------------------------------------

    def _parse_location(self, location: str) -> tuple[str, str]:
        parts = [p.strip() for p in location.split(",")]
        city = parts[0] if parts else ""
        state = parts[1] if len(parts) > 1 else ""
        return city, state

    @staticmethod
    def _lead_key(lead: BusinessLead) -> str:
        return (
            f"{(lead.name or '').strip().lower()}|"
            f"{(lead.city or '').strip().lower()}|"
            f"{(lead.state or '').strip().lower()}"
        )

    def _deduplicate(
        self, leads: list[BusinessLead], existing: set[str]
    ) -> list[BusinessLead]:
        seen = set(existing)
        unique: list[BusinessLead] = []
        for lead in leads:
            if lead.is_sponsored:
                continue
            key = self._lead_key(lead)
            if key not in seen:
                seen.add(key)
                unique.append(lead)
        return unique
