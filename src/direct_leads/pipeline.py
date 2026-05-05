import logging
from datetime import datetime
from pathlib import Path
import pandas as pd

from src.core.scraper_engine import ScraperEngine
from src.core.models import DirectLead
from src.core.config import settings, DIRECT_OUTPUT_DIR
from src.core.storage import get_existing_direct_lead_urls
from src.direct_leads.matcher import RelevanceMatcher
from src.direct_leads.enricher import LeadEnricher
from src.direct_leads.scrapers.reddit import RedditScraper
from src.direct_leads.scrapers.indeed import IndeedScraper
from src.direct_leads.scrapers.linkedin_jobs import LinkedInJobsScraper
from src.direct_leads.scrapers.clutch import ClutchScraper
from src.direct_leads.scrapers.goodfirms import GoodFirmsScraper
from src.direct_leads.scrapers.twitter import TwitterScraper
from src.direct_leads.scrapers.linkedin_posts import LinkedInPostsScraper
from src.direct_leads.scrapers.tanit import TanitScraper
from src.direct_leads.scrapers.remoteok import RemoteOKScraper

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
    ) -> list[str]:
        """Run the direct leads pipeline. Returns list of output file paths."""
        active_sources = sources or list(SCRAPER_CLASSES.keys())
        existing_urls = get_existing_direct_lead_urls()
        source_configs = source_configs or {}

        # 1. Scrape from selected sources concurrently (bounded by semaphore)
        import asyncio
        max_concurrent = max(1, int(getattr(settings.scraping, "max_concurrent_scrapers", 3) or 3))
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

        # 2. Deduplicate
        unique = self._deduplicate(all_leads, existing_urls)
        logger.info(f"Unique leads after dedup: {len(unique)}")

        # 3. Score with matcher
        for lead in unique:
            hours_ago = None
            if lead.posted_date:
                delta = datetime.now(tz=lead.posted_date.tzinfo) - lead.posted_date if lead.posted_date.tzinfo else datetime.now() - lead.posted_date
                hours_ago = delta.total_seconds() / 3600

            lead.relevance_score = self.matcher.score(
                description=f"{lead.title} {lead.description}",
                posted_hours_ago=hours_ago,
                has_budget=bool(lead.budget_signal),
                has_contact=bool(lead.contact_email or lead.contact_phone),
                is_remote="remote" in (lead.location or "").lower(),
            )
            lead.matched_skills = self.matcher.get_matched_skills(f"{lead.title} {lead.description}")
            lead.budget_signal = self._detect_budget(lead.description) or ""
            lead.urgency_signal = self._detect_urgency(lead.description) or ""

        # 4. Enrich (company info)
        if progress_callback:
            progress_callback("Enriching leads...")
        unique = self.enricher.enrich_many(unique)

        # 5. Sort by relevance
        unique.sort(key=lambda l: l.relevance_score, reverse=True)

        # 6. Export
        if unique:
            return self._export(unique, keywords)
        return []

    def _deduplicate(self, leads: list[DirectLead], existing_urls: set[str]) -> list[DirectLead]:
        seen = set(existing_urls)
        unique = []
        for lead in leads:
            if lead.url and lead.url not in seen:
                seen.add(lead.url)
                unique.append(lead)
        return unique

    def _detect_budget(self, text: str) -> str | None:
        import re
        text = text.lower()
        amounts = re.findall(r'\$[\d,]+', text)
        if amounts:
            for a in amounts:
                val = int(a.replace("$", "").replace(",", ""))
                if val >= 5000:
                    return "high"
                elif val >= 1000:
                    return "medium"
                else:
                    return "low"
        if any(w in text for w in ["budget", "pay well", "competitive rate"]):
            return "medium"
        return None

    def _detect_urgency(self, text: str) -> str | None:
        text = text.lower()
        if any(w in text for w in ["asap", "urgent", "immediately", "this week"]):
            return "urgent"
        if any(w in text for w in ["soon", "next week", "within a month"]):
            return "normal"
        return None

    def _export(self, leads: list[DirectLead], keywords: list[str]) -> list[str]:
        """Export direct leads to Excel."""
        DIRECT_OUTPUT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        kw_slug = "_".join(keywords[:3]).replace(" ", "-")[:30]
        filename = f"direct_{kw_slug}_{timestamp}.xlsx"
        path = DIRECT_OUTPUT_DIR / filename

        records = []
        for lead in leads:
            priority = self.matcher.get_priority(lead.relevance_score)
            records.append({
                "Lead_ID": lead.lead_id,
                "Priority": priority.upper(),
                "Relevance_Score": lead.relevance_score,
                "Source": lead.source,
                "Title": lead.title,
                "Description": lead.description[:500],
                "URL": lead.url,
                "Posted_Date": lead.posted_date.isoformat() if lead.posted_date else "",
                "Company": lead.company_name or "",
                "Company_Website": lead.company_website or "",
                "Location": lead.location or "",
                "Contact_Name": lead.contact_name or "",
                "Contact_Email": lead.contact_email or "",
                "Contact_Phone": lead.contact_phone or "",
                "Budget_Signal": lead.budget_signal or "",
                "Urgency_Signal": lead.urgency_signal or "",
                "Matched_Skills": ", ".join(lead.matched_skills),
                "Outreach_Status": lead.outreach_status,
                "Notes": lead.notes or "",
            })

        df = pd.DataFrame(records)
        priority_order = {"HOT": 0, "WARM": 1, "COLD": 2}
        df["_order"] = df["Priority"].map(lambda x: priority_order.get(x, 3))
        df = df.sort_values(["_order", "Relevance_Score"], ascending=[True, False]).drop("_order", axis=1)

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Leads", index=False)
            # Auto-adjust column widths
            ws = writer.sheets["Leads"]
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col))
                from openpyxl.utils import get_column_letter
                ws.column_dimensions[get_column_letter(idx + 1)].width = min(max_len + 2, 50)

        logger.info(f"Exported {len(leads)} direct leads to {path}")
        return [str(path)]
