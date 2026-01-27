#!/usr/bin/env python3
"""
Lead Prospector - Main Entry Point
Orchestrates the full lead generation and scoring pipeline.
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from typing import Optional

# Fix Windows console encoding for Unicode characters (emojis in business names)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Python < 3.7

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from src.config import settings, validate_api_keys, get_missing_keys, OUTPUT_DIR
from src.apis.google_places import GooglePlacesClient, GooglePlaceBusiness
from src.apis.yelp import YelpClient, YelpBusiness
from src.audit.website_auditor import WebsiteAuditor, WebsiteAuditResult, ReviewAnalyzer
from src.scoring.scorer import LeadScorer, ProcessedLead, create_processed_lead
from src.export.exporter import LeadExporter

# Web scrapers (free alternative to paid APIs)
from src.scrapers import (
    GoogleMapsScraper,
    YelpScraper,
    YellowPagesScraper,
    BBBScraper,
    MantaScraper,
    BusinessLead,
    RateLimiter,
    EmailExtractor,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            PROJECT_ROOT
            / "logs"
            / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
console = Console()


class LeadProspector:
    """Main orchestrator for lead prospecting pipeline."""

    def __init__(self):
        self.scorer = LeadScorer()
        self.review_analyzer = ReviewAnalyzer()
        self.exporter = LeadExporter()
        self.last_output_files: list[Path] = []

        # Business deduplication
        self.seen_businesses: dict[
            str, ProcessedLead
        ] = {}  # key: normalized name+address

    async def run(
        self,
        locations: list[str],
        niches: list[str] = None,
        skip_audit: bool = False,
        skip_reviews: bool = False,
        output_format: str = "both",
        use_scrapers: bool = False,
        skip_scrapers: list[str] = None,
        fetch_details: bool = False,
        fetch_emails: bool = False,
        max_results: int = 20,
    ) -> list[ProcessedLead]:
        """
        Run the full lead prospecting pipeline.

        Args:
            locations: List of location strings (e.g., ["Austin, TX", "Houston, TX"])
            niches: List of niches to search (default: all configured niches)
            skip_audit: Skip website auditing (faster but less data)
            skip_reviews: Skip review fetching (faster but less data)
            output_format: Output format (csv, xlsx, both)
            use_scrapers: Use free web scraping instead of paid APIs
            max_results: Maximum results per scraper per location (default: 20)

        Returns:
            List of ProcessedLead objects
        """
        niches = niches or list(settings.search.niches.keys())

        mode_text = (
            "[bold magenta]SCRAPING MODE[/bold magenta] (Free)"
            if use_scrapers
            else "[bold green]API MODE[/bold green] (Paid)"
        )
        console.print(
            Panel.fit(
                f"[bold blue]Lead Prospector[/bold blue]\n"
                f"Mode: {mode_text}\n"
                f"Locations: {', '.join(locations)}\n"
                f"Niches: {', '.join(niches)}\n"
                f"Website Audit: {'Enabled' if not skip_audit else 'Disabled'}\n"
                f"Review Analysis: {'Enabled' if not skip_reviews else 'Disabled'}\n"
                f"Email Extraction: {'Enabled' if fetch_emails else 'Disabled'}",
                title="Configuration",
            )
        )

        # Check API keys (only required if not using scrapers)
        if not use_scrapers:
            api_status = validate_api_keys()
            if not any([api_status["google_places"], api_status["yelp"]]):
                console.print(
                    "[bold red]Error:[/bold red] No API keys configured. Please set GOOGLE_PLACES_API_KEY or YELP_API_KEY in .env"
                )
                console.print(
                    "[yellow]Tip:[/yellow] Use --scrape flag to use free web scraping instead of paid APIs"
                )
                return []
        else:
            api_status = {"google_places": False, "yelp": False}
            console.print("[cyan]Using web scrapers (no API keys required)[/cyan]\n")

        all_leads = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            total_tasks = len(locations) * len(niches)
            main_task = progress.add_task("[cyan]Processing...", total=total_tasks)

            for location in locations:
                for niche in niches:
                    progress.update(
                        main_task,
                        description=f"[cyan]Searching {niche} in {location}...",
                    )

                    if use_scrapers:
                        # Use free web scrapers
                        scraped_leads = await self._fetch_from_scrapers(
                            niche,
                            location,
                            progress,
                            skip_scrapers=skip_scrapers,
                            fetch_details=fetch_details,
                            max_results=max_results,
                        )
                        active_scrapers = 5 - len(skip_scrapers or [])
                        console.print(
                            f"  [magenta]Scrapers:[/magenta] Found {len(scraped_leads)} businesses from {active_scrapers} sources"
                        )

                        # Merge scraped leads (handles BusinessLead objects)
                        merged = self._merge_scraped_businesses(scraped_leads, niche)
                        console.print(
                            f"  [blue]Merged:[/blue] {len(merged)} unique businesses"
                        )
                    else:
                        # Use paid APIs
                        google_businesses = []
                        yelp_businesses = []

                        if api_status["google_places"]:
                            google_businesses = await self._fetch_google_places(
                                niche, location, not skip_reviews
                            )
                            console.print(
                                f"  [green]Google Places:[/green] Found {len(google_businesses)} businesses"
                            )

                        if api_status["yelp"]:
                            yelp_businesses = await self._fetch_yelp(
                                niche, location, not skip_reviews
                            )
                            console.print(
                                f"  [green]Yelp:[/green] Found {len(yelp_businesses)} businesses"
                            )

                        # Merge and deduplicate
                        merged = self._merge_businesses(
                            google_businesses, yelp_businesses, niche
                        )
                        console.print(
                            f"  [blue]Merged:[/blue] {len(merged)} unique businesses"
                        )

                    # Audit websites and score
                    if not skip_audit:
                        progress.update(
                            main_task,
                            description=f"[cyan]Auditing websites for {niche} in {location}...",
                        )

                    leads = await self._process_businesses(
                        merged, niche, skip_audit, progress
                    )

                    all_leads.extend(leads)
                    progress.advance(main_task)

        # Final deduplication across all locations
        unique_leads = list(self.seen_businesses.values())

        # Sort by score
        unique_leads.sort(key=lambda x: x.total_score, reverse=True)

        # Email extraction phase
        if fetch_emails and unique_leads:
            console.print(
                f"\n[cyan]Extracting emails for {len(unique_leads)} leads...[/cyan]"
            )
            unique_leads = await self._extract_emails_for_leads(unique_leads)

        # Export results
        if unique_leads:
            console.print(
                f"\n[bold green]Found {len(unique_leads)} total leads[/bold green]"
            )

            output_files = self.exporter.export(
                unique_leads, filename="lead_prospects", format=output_format
            )
            self.last_output_files = output_files

            console.print("\n[bold]Output files:[/bold]")
            for f in output_files:
                console.print(f"  [cyan]{f}[/cyan]")

            # Show summary
            self._print_summary(unique_leads)
        else:
            console.print(
                "[yellow]No leads found. Check your API keys and search parameters.[/yellow]"
            )
            self.last_output_files = []

        return unique_leads

    async def _fetch_google_places(
        self, niche: str, location: str, fetch_details: bool
    ) -> list[GooglePlaceBusiness]:
        """Fetch businesses from Google Places API."""
        try:
            async with GooglePlacesClient() as client:
                return await client.search_niche(
                    niche, location, fetch_details=fetch_details
                )
        except Exception as e:
            logger.error(f"Error fetching from Google Places: {e}")
            return []

    async def _fetch_yelp(
        self, niche: str, location: str, fetch_reviews: bool
    ) -> list[YelpBusiness]:
        """Fetch businesses from Yelp API."""
        try:
            async with YelpClient() as client:
                return await client.search_niche(
                    niche, location, fetch_reviews=fetch_reviews
                )
        except Exception as e:
            logger.error(f"Error fetching from Yelp: {e}")
            return []

    async def _fetch_from_scrapers(
        self,
        niche: str,
        location: str,
        progress: Progress,
        skip_scrapers: list[str] = None,
        fetch_details: bool = False,
        max_results: int = 20,
    ) -> list[BusinessLead]:
        """
        Fetch businesses from all 5 web scrapers.

        Uses Google Maps, Yelp, YellowPages, BBB, and Manta scrapers
        with rate limiting to avoid detection.

        Args:
            skip_scrapers: List of scraper names to skip (e.g., ["yelp", "manta"])
            fetch_details: If True, fetch website URLs from detail pages for scrapers
                          that don't include them in search results (BBB, Yelp)
            max_results: Maximum results per scraper (default: 20)
        """
        # Parse location into city and state
        parts = location.split(",")
        city = parts[0].strip()
        state = parts[1].strip() if len(parts) > 1 else ""

        rate_limiter = RateLimiter()
        all_leads: list[BusinessLead] = []

        scrapers = [
            ("Google Maps", "google_maps", GoogleMapsScraper(rate_limiter)),
            ("Yelp", "yelp", YelpScraper(rate_limiter)),
            ("YellowPages", "yellowpages", YellowPagesScraper(rate_limiter)),
            ("BBB", "bbb", BBBScraper(rate_limiter)),
            ("Manta", "manta", MantaScraper(rate_limiter)),
        ]

        # Filter out skipped scrapers
        skip_scrapers = skip_scrapers or []
        skip_names = [
            s.lower().replace(" ", "").replace("_", "") for s in skip_scrapers
        ]

        if skip_names:
            original_count = len(scrapers)
            scrapers = [
                (name, step_name, scraper)
                for name, step_name, scraper in scrapers
                if name.lower().replace(" ", "") not in skip_names
            ]
            skipped_count = original_count - len(scrapers)
            if skipped_count > 0:
                console.print(
                    f"    [dim yellow]Skipping {skipped_count} scraper(s): {', '.join(skip_scrapers)}[/dim yellow]"
                )

        # Get progress tracker if available (injected from run_manager)
        tracker = getattr(self, "_progress_tracker", None)
        total_scrapers = len(scrapers)
        completed_scrapers = 0

        for name, step_name, scraper in scrapers:
            # Update progress tracker - starting scraper
            if tracker:
                try:
                    await tracker.update_step(
                        f"Scrape {step_name}", f"Searching {name}..."
                    )
                    # Calculate progress: 10% base + up to 60% for scraping phase
                    scrape_progress = 10 + int(
                        (completed_scrapers / total_scrapers) * 60
                    )
                    await tracker.set_progress(scrape_progress)
                except Exception as e:
                    logger.debug(f"Progress tracker update failed: {e}")

            try:
                async with scraper:
                    leads = await scraper.search(
                        business_type=niche, city=city, state=state, max_results=max_results
                    )
                    console.print(f"    [dim]{name}:[/dim] {len(leads)} results")

                    # Update progress tracker with leads found
                    if tracker:
                        try:
                            await tracker.increment_leads(len(leads))
                            await tracker.complete_step(
                                f"Scrape {step_name}",
                                f"Found {len(leads)} leads",
                                len(leads),
                            )
                        except Exception as e:
                            logger.debug(f"Progress tracker update failed: {e}")

                    # Fetch details for leads without websites if requested
                    if fetch_details and name in ("BBB", "Yelp"):
                        leads_needing_details = [
                            lead
                            for lead in leads
                            if not lead.website
                            and lead.detail_url
                            and not lead.is_sponsored
                        ]
                        if leads_needing_details:
                            console.print(
                                f"    [dim cyan]Fetching details for {len(leads_needing_details)} {name} leads...[/dim cyan]"
                            )
                            for lead in leads_needing_details:
                                try:
                                    await scraper.get_details(lead)
                                except Exception as detail_err:
                                    logger.debug(
                                        f"Failed to get details for {lead.name}: {detail_err}"
                                    )

                    all_leads.extend(leads)
            except Exception as e:
                logger.warning(f"Error scraping {name}: {e}")
                console.print(f"    [dim red]{name}:[/dim red] Failed - {e}")

                # Mark step as failed in progress tracker
                if tracker:
                    try:
                        await tracker.fail_step(f"Scrape {step_name}", str(e))
                    except Exception as te:
                        logger.debug(f"Progress tracker update failed: {te}")

            completed_scrapers += 1

        # Update final scraping progress
        if tracker:
            try:
                await tracker.set_progress(70)  # 70% after scraping complete
            except Exception as e:
                logger.debug(f"Progress tracker update failed: {e}")

        return all_leads

    def _merge_scraped_businesses(
        self, leads: list[BusinessLead], niche: str
    ) -> list[dict]:
        """
        Merge and deduplicate scraped BusinessLead objects.

        Converts to the same format as _merge_businesses() for compatibility
        with _process_businesses().

        Returns list of dicts with 'scraped' key containing list of BusinessLead objects.
        """
        merged = {}

        for lead in leads:
            # Skip sponsored/promoted results
            if lead.is_sponsored:
                continue

            # Create full address for deduplication
            full_address = (
                f"{lead.address or ''}, {lead.city or ''}, {lead.state or ''}"
            )
            key = self._normalize_business_key(lead.name, full_address)

            if key in merged:
                # Add to existing entry (multi-source match)
                merged[key]["scraped"].append(lead)
            else:
                # Check for fuzzy name match
                name_key = self._normalize_name(lead.name)
                matched = False
                for existing_key in merged:
                    if name_key in existing_key:
                        merged[existing_key]["scraped"].append(lead)
                        matched = True
                        break

                if not matched:
                    merged[key] = {
                        "google": None,
                        "yelp": None,
                        "scraped": [lead],
                        "niche": niche,
                    }

        return list(merged.values())

    def _merge_businesses(
        self,
        google_businesses: list[GooglePlaceBusiness],
        yelp_businesses: list[YelpBusiness],
        niche: str,
    ) -> list[dict]:
        """
        Merge and deduplicate businesses from multiple sources.

        Returns list of dicts with 'google' and 'yelp' keys.
        """
        merged = {}

        # Index Google businesses
        for biz in google_businesses:
            key = self._normalize_business_key(biz.name, biz.address)
            merged[key] = {"google": biz, "yelp": None, "niche": niche}

        # Match and add Yelp businesses
        for biz in yelp_businesses:
            full_address = f"{biz.address}, {biz.city}, {biz.state}"
            key = self._normalize_business_key(biz.name, full_address)

            if key in merged:
                merged[key]["yelp"] = biz
            else:
                # Try fuzzy match on name only
                name_key = self._normalize_name(biz.name)
                matched = False
                for existing_key in merged:
                    if name_key in existing_key:
                        merged[existing_key]["yelp"] = biz
                        matched = True
                        break

                if not matched:
                    merged[key] = {"google": None, "yelp": biz, "niche": niche}

        return list(merged.values())

    def _normalize_business_key(self, name: str, address: str) -> str:
        """Create a normalized key for deduplication."""
        name_norm = self._normalize_name(name)
        addr_norm = "".join(c for c in address.lower() if c.isalnum())[:30]
        return f"{name_norm}_{addr_norm}"

    def _normalize_name(self, name: str) -> str:
        """Normalize business name for matching."""
        # Remove common suffixes and normalize
        name = name.lower()
        for suffix in ["llc", "inc", "corp", "co", "ltd", "company"]:
            name = name.replace(suffix, "")
        return "".join(c for c in name if c.isalnum())[:30]

    async def _process_businesses(
        self,
        merged_businesses: list[dict],
        niche: str,
        skip_audit: bool,
        progress: Progress,
    ) -> list[ProcessedLead]:
        """Process merged businesses: audit, analyze, score."""
        leads = []

        async with WebsiteAuditor() as auditor:
            for biz_data in merged_businesses:
                google_biz = biz_data.get("google")
                yelp_biz = biz_data.get("yelp")
                scraped_leads = biz_data.get(
                    "scraped", []
                )  # List of BusinessLead objects

                # Get website URL (check API sources first, then scraped)
                website = None
                if google_biz and google_biz.website:
                    website = google_biz.website
                elif not website:
                    # Try to get website from scraped leads
                    for sl in scraped_leads:
                        if sl.website:
                            website = sl.website
                            break

                # Audit website
                audit_result = None
                if not skip_audit and website:
                    try:
                        audit_result = await auditor.audit_website(website)
                    except Exception as e:
                        logger.warning(f"Failed to audit {website}: {e}")

                # Analyze reviews (only available from API sources)
                all_reviews = []
                if google_biz and google_biz.reviews:
                    all_reviews.extend(google_biz.reviews)
                if yelp_biz and yelp_biz.reviews:
                    all_reviews.extend(yelp_biz.reviews)

                review_analysis = None
                if all_reviews:
                    review_analysis = self.review_analyzer.analyze_reviews(all_reviews)

                # Score the business - combine data from all sources
                rating = None
                review_count = 0

                # Priority: API sources first
                if google_biz:
                    rating = google_biz.rating
                    review_count += google_biz.review_count or 0
                if yelp_biz:
                    rating = rating or yelp_biz.rating
                    review_count += yelp_biz.review_count or 0

                # Fallback to scraped data
                if rating is None and scraped_leads:
                    # Use highest rating from scraped sources
                    scraped_ratings = [sl.rating for sl in scraped_leads if sl.rating]
                    if scraped_ratings:
                        rating = max(scraped_ratings)
                    # Sum review counts from scraped sources
                    for sl in scraped_leads:
                        review_count += sl.review_count or 0

                scoring_result = self.scorer.score_business(
                    website_audit=asdict(audit_result) if audit_result else None,
                    review_analysis=review_analysis,
                    rating=rating,
                    review_count=review_count,
                    has_website=bool(website),
                )

                # Create processed lead
                if google_biz or yelp_biz:
                    # Use existing API-based lead creation
                    lead = create_processed_lead(
                        google_business=google_biz,
                        yelp_business=yelp_biz,
                        website_audit=audit_result,
                        review_analysis=review_analysis,
                        scoring_result=scoring_result,
                        niche=niche,
                    )
                elif scraped_leads:
                    # Create lead from scraped data
                    lead = self._create_lead_from_scraped(
                        scraped_leads=scraped_leads,
                        website_audit=audit_result,
                        scoring_result=scoring_result,
                        niche=niche,
                    )
                else:
                    continue

                # Deduplicate
                key = self._normalize_business_key(lead.name, lead.address)
                if key not in self.seen_businesses:
                    self.seen_businesses[key] = lead
                    leads.append(lead)

                # Rate limiting
                await asyncio.sleep(0.2)

        return leads

    def _create_lead_from_scraped(
        self,
        scraped_leads: list[BusinessLead],
        website_audit: Optional[WebsiteAuditResult],
        scoring_result,  # ScoringResult dataclass
        niche: str,
    ) -> ProcessedLead:
        """
        Create a ProcessedLead from scraped BusinessLead objects.

        Combines data from multiple scraper sources into a single lead.
        """
        # Use the first scraped lead as the base
        primary = scraped_leads[0]

        # Collect all sources
        sources = list(set(sl.source for sl in scraped_leads))

        # Get best data from all scraped leads
        name = primary.name
        phone = next((sl.phone for sl in scraped_leads if sl.phone), None)
        website = next((sl.website for sl in scraped_leads if sl.website), None)
        address = primary.address or ""
        city = primary.city or ""
        state = primary.state or ""
        full_address = f"{address}, {city}, {state}".strip(", ")

        # Get highest rating and total reviews
        ratings = [sl.rating for sl in scraped_leads if sl.rating]
        rating = max(ratings) if ratings else None
        review_count = sum(sl.review_count or 0 for sl in scraped_leads)

        # Collect extra data from all sources
        extra_data = {}
        for sl in scraped_leads:
            if sl.extra_data:
                extra_data.update(sl.extra_data)

        # Extract BBB data if available
        bbb_rating = extra_data.get("bbb_rating")
        bbb_accredited = extra_data.get("accredited", False)
        complaint_count = extra_data.get("complaint_count", 0)

        # Build categories list
        categories = []
        for sl in scraped_leads:
            if sl.categories:
                categories.extend(sl.categories)
        categories = list(set(categories))

        # Create ProcessedLead
        return ProcessedLead(
            # Basic info
            name=name,
            phone=phone or "",
            website=website or "",
            address=full_address,
            city=city,
            state=state,
            niche=niche,
            source="scraped",
            # Ratings
            google_rating=None,
            google_review_count=0,
            yelp_rating=rating,  # Use scraped rating as yelp_rating field
            yelp_review_count=review_count,
            # Scoring
            total_score=scoring_result.total_score,
            priority=scoring_result.priority.value,
            pain_tags=scoring_result.pain_tags,
            pain_tags_str=", ".join(scoring_result.pain_tags),
            recommended_offer=scoring_result.recommended_offer.value,
            offer_reasoning=scoring_result.offer_reasoning,
            # Website audit data
            has_ssl=website_audit.has_ssl if website_audit else False,
            has_booking_cta=website_audit.has_booking_cta if website_audit else False,
            has_contact_form=website_audit.has_contact_form if website_audit else False,
            is_mobile_friendly=website_audit.is_mobile_friendly
            if website_audit
            else True,
            page_load_time_ms=website_audit.page_load_time_ms
            if website_audit
            else None,
            # Score breakdown
            website_score=scoring_result.website_score,
            conversion_score=scoring_result.conversion_score,
            ops_score=scoring_result.ops_score,
            reputation_score=scoring_result.reputation_score,
        )

    def _print_summary(self, leads: list[ProcessedLead]):
        """Print a summary table of results."""
        # Priority breakdown
        hot = sum(1 for l in leads if l.priority == "hot")
        warm = sum(1 for l in leads if l.priority == "warm")
        cold = sum(1 for l in leads if l.priority == "cold")

        console.print("\n")
        summary_table = Table(title="Lead Summary")
        summary_table.add_column("Priority", style="cyan")
        summary_table.add_column("Count", justify="right")
        summary_table.add_row("[bold red]HOT[/bold red]", str(hot))
        summary_table.add_row("[bold yellow]WARM[/bold yellow]", str(warm))
        summary_table.add_row("COLD", str(cold))
        summary_table.add_row("[bold]Total[/bold]", str(len(leads)))
        console.print(summary_table)

        # Top 5 hot leads
        if hot > 0:
            console.print("\n[bold]Top Hot Leads:[/bold]")
            hot_leads = [l for l in leads if l.priority == "hot"][:5]

            leads_table = Table()
            leads_table.add_column("Business", style="cyan")
            leads_table.add_column("Score", justify="right")
            leads_table.add_column("Offer", style="green")
            leads_table.add_column("Pain Tags")

            for lead in hot_leads:
                leads_table.add_row(
                    lead.name[:40],
                    str(lead.total_score),
                    lead.recommended_offer.replace("_", " ").title(),
                    lead.pain_tags_str[:50],
                )

            console.print(leads_table)

    async def _extract_emails_for_leads(
        self, leads: list[ProcessedLead]
    ) -> list[ProcessedLead]:
        """
        Extract email addresses for all leads with websites.

        Uses EmailExtractor to scrape emails from business websites.
        """
        leads_with_websites = [l for l in leads if l.website]
        leads_without_websites = [l for l in leads if not l.website]

        console.print(
            f"  [dim]{len(leads_with_websites)} leads have websites, "
            f"{len(leads_without_websites)} do not[/dim]"
        )

        if not leads_with_websites:
            return leads

        extracted_count = 0
        tracker = getattr(self, "_progress_tracker", None)
        
        # Update progress tracker for email phase
        if tracker:
            try:
                await tracker.set_phase("Email Extraction", f"Extracting emails from {len(leads_with_websites)} websites...")
                await tracker.set_progress(75)
            except Exception as e:
                logger.debug(f"Progress tracker update failed: {e}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Extracting emails...", total=len(leads_with_websites)
            )

            async with EmailExtractor() as extractor:
                for i, lead in enumerate(leads_with_websites):
                    try:
                        result = await extractor.extract_email(lead.website, lead.name)
                        if result and result.email:
                            lead.email = result.email
                            lead.email_source = result.source
                            lead.email_confidence = result.confidence
                            extracted_count += 1
                            progress.update(
                                task, description=f"[cyan]Found: {result.email}[/cyan]"
                            )
                            
                            # Update progress tracker
                            if tracker:
                                try:
                                    await tracker.increment_emails(1)
                                    await tracker.update_step(f"Email extraction", f"Found: {result.email}")
                                except Exception:
                                    pass
                        else:
                            progress.update(
                                task,
                                description=f"[dim]No email: {lead.name[:30]}[/dim]",
                            )
                    except Exception as e:
                        logger.debug(f"Email extraction failed for {lead.website}: {e}")

                    progress.advance(task)
                    
                    # Update progress percentage (75-95% for email extraction)
                    if tracker:
                        try:
                            email_progress = 75 + int((i / len(leads_with_websites)) * 20)
                            await tracker.set_progress(email_progress)
                        except Exception:
                            pass

                    # Rate limiting
                    await asyncio.sleep(0.5)

        console.print(
            f"  [green]Extracted {extracted_count} emails "
            f"from {len(leads_with_websites)} websites[/green]"
        )
        
        # Update final progress
        if tracker:
            try:
                await tracker.set_progress(95)
                await tracker.update_step("Email extraction", f"Completed - {extracted_count} emails found")
            except Exception:
                pass

        # Combine and return
        return leads_with_websites + leads_without_websites


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Lead Prospector - Find and score local business leads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using paid APIs (requires API keys)
  python main.py --locations "Austin, TX" "Houston, TX"
  python main.py --locations "Miami, FL" --niches plumbing dental
  
  # Using FREE web scraping (no API keys needed!)
  python main.py --locations "Austin, TX" --scrape
  python main.py --locations "Seattle, WA" --scrape --niches plumbing --output csv
        """,
    )

    parser.add_argument(
        "--locations",
        "-l",
        nargs="+",
        required=True,
        help="Locations to search (e.g., 'Austin, TX' 'Houston, TX')",
    )

    parser.add_argument(
        "--niches",
        "-n",
        nargs="+",
        choices=["plumbing", "dental", "pest_control"],
        default=["plumbing", "dental", "pest_control"],
        help="Niches to search (default: all)",
    )

    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help="Skip website auditing (faster but less data)",
    )

    parser.add_argument(
        "--skip-reviews",
        action="store_true",
        help="Skip fetching reviews (faster but less data)",
    )

    parser.add_argument(
        "--output",
        "-o",
        choices=["csv", "xlsx", "both"],
        default="both",
        help="Output format (default: both)",
    )

    parser.add_argument(
        "--scrape",
        "-s",
        action="store_true",
        help="Use free web scraping instead of paid APIs (Google Maps, Yelp, YellowPages, BBB, Manta)",
    )

    parser.add_argument(
        "--skip-scrapers",
        nargs="+",
        default=[],
        help="Skip specific scrapers (e.g., --skip-scrapers yelp manta)",
    )

    parser.add_argument(
        "--fetch-details",
        action="store_true",
        help="Fetch website URLs from detail pages for scrapers that don't include them in search results (BBB, Yelp). Slower but more complete data.",
    )

    parser.add_argument(
        "--fetch-emails",
        action="store_true",
        help="Extract email addresses from business websites after scraping. Adds Email, Email_Source, Email_Confidence columns to output.",
    )

    args = parser.parse_args()

    # Check for missing API keys (only warn if not using scrape mode)
    if not args.scrape:
        missing = get_missing_keys()
        if missing:
            console.print(
                f"[yellow]Warning:[/yellow] Missing API keys: {', '.join(missing)}"
            )
            console.print("Set them in .env file or as environment variables.")
            console.print(
                "[cyan]Tip:[/cyan] Use --scrape flag to use free web scraping instead!\n"
            )

    # Run the prospector
    prospector = LeadProspector()

    try:
        asyncio.run(
            prospector.run(
                locations=args.locations,
                niches=args.niches,
                skip_audit=args.skip_audit,
                skip_reviews=args.skip_reviews,
                output_format=args.output,
                use_scrapers=args.scrape,
                skip_scrapers=args.skip_scrapers,
                fetch_details=args.fetch_details,
                fetch_emails=args.fetch_emails,
            )
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Unhandled exception")
        sys.exit(1)


if __name__ == "__main__":
    main()
