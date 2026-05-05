"""
Cold Outreach Pipeline (v2)

Orchestrates the full cold outreach lead generation pipeline:
scrape -> deduplicate -> audit -> score -> extract emails -> export.
"""

import logging
from datetime import datetime

from src.core.scraper_engine import ScraperEngine
from src.core.models import BusinessLead
from src.core.config import settings, COLD_OUTPUT_DIR
from src.core.storage import get_existing_businesses
from src.cold_outreach.scrapers.yellowpages import YellowPagesScraper
from src.cold_outreach.scrapers.manta import MantaScraper
from src.cold_outreach.scrapers.bbb import BBBScraper
from src.cold_outreach.scrapers.yelp import YelpScraper
from src.cold_outreach.scrapers.google_maps import GoogleMapsScraper
from src.cold_outreach.auditor import WebsiteAuditor, ReviewAnalyzer
from src.cold_outreach.scorer import LeadScorer, create_processed_lead
from src.cold_outreach.email_extractor import EmailExtractor
from src.export.exporter import LeadExporter

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
        self.exporter = LeadExporter(output_dir=COLD_OUTPUT_DIR)

    async def run(
        self,
        locations: list[str],
        niches: list[str],
        max_results: int = 20,
        skip_scrapers: list[str] | None = None,
        skip_audit: bool = False,
        fetch_emails: bool = False,
        fetch_details: bool = True,
        progress_callback=None,
    ) -> list[str]:
        """Run the full cold outreach pipeline. Returns list of output file paths."""
        skip = set(skip_scrapers or [])
        existing = get_existing_businesses()
        all_output_files: list[str] = []

        for location in locations:
            city, state = self._parse_location(location)
            for niche in niches:
                if progress_callback:
                    progress_callback(f"Scraping {niche} in {city}, {state}...")

                # 1. Scrape from all sources, across every keyword variant in
                # the niche. Google/Yelp use category IDs internally so they
                # only need one canonical pass; YP/BBB/Manta search by free
                # text and benefit from each variant ("plumber" misses leads
                # that "drain cleaning" or "pipe repair" find).
                raw_leads: list[BusinessLead] = []
                niche_keywords = settings.search.niches.get(niche, [niche]) or [niche]
                category_sources = {"google_maps", "yelp"}

                for name, cls in SCRAPER_CLASSES.items():
                    if name in skip:
                        continue
                    try:
                        scraper = cls(self.engine)
                        # Category-driven sources only need the canonical term once.
                        terms = (
                            niche_keywords[:1]
                            if name in category_sources
                            else niche_keywords
                        )
                        # Each keyword gets full max_results breadth; dedup
                        # collapses overlaps across variants.
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

                # 2. Deduplicate
                unique_leads = self._deduplicate(raw_leads, existing)
                logger.info(f"Unique leads after dedup: {len(unique_leads)}")

                # 3. Fetch details (websites) if requested
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

                # 4. Audit + Score
                processed = []
                for lead in unique_leads:
                    audit_result = None
                    if not skip_audit and lead.website:
                        try:
                            audit_result = self.auditor.audit(lead.website)
                        except Exception:
                            pass

                    scoring = self.scorer.score_business(
                        website_audit=(
                            audit_result.__dict__ if audit_result else None
                        ),
                        rating=lead.rating,
                        review_count=lead.review_count or 0,
                        has_website=bool(lead.website),
                    )

                    pl = create_processed_lead(
                        scoring_result=scoring, niche=niche
                    )
                    # Copy fields from BusinessLead
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

                    processed.append(pl)

                # 5. Extract emails if requested
                if fetch_emails:
                    for pl in processed:
                        if pl.website and not pl.email:
                            result = self.email_extractor.extract(pl.website)
                            if result.email:
                                pl.email = result.email
                                pl.email_source = result.source
                                pl.email_confidence = result.confidence

                # 6. Export
                if processed:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{niche}_{city}_{state}_{timestamp}"
                    paths = self.exporter.export(
                        processed, filename, format="xlsx"
                    )
                    all_output_files.extend([str(p) for p in paths])
                    logger.info(f"Exported {len(processed)} leads to {paths}")

        return all_output_files

    def _parse_location(self, location: str) -> tuple[str, str]:
        """Parse 'City, ST' into (city, state)."""
        parts = [p.strip() for p in location.split(",")]
        city = parts[0] if parts else ""
        state = parts[1] if len(parts) > 1 else ""
        return city, state

    def _deduplicate(
        self, leads: list[BusinessLead], existing: set[str]
    ) -> list[BusinessLead]:
        """Remove duplicates based on name|city|state."""
        seen = set(existing)
        unique: list[BusinessLead] = []
        for lead in leads:
            if lead.is_sponsored:
                continue
            key = f"{lead.name.lower().strip()}|{lead.city.lower().strip()}|{lead.state.lower().strip()}"
            if key not in seen:
                seen.add(key)
                unique.append(lead)
        return unique
