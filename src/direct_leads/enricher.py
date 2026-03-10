import re
import logging
from scrapling import Fetcher
from src.core.models import DirectLead

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,15}')
EXCLUDED_EMAIL_DOMAINS = {"example.com", "email.com", "domain.com", "yoursite.com", "sentry.io", "wixpress.com", "googleapis.com"}


class LeadEnricher:
    """Enriches DirectLead objects with company contact info from their websites."""

    def __init__(self):
        self.fetcher = Fetcher()

    def enrich(self, lead: DirectLead) -> DirectLead:
        """Enrich a lead with company website data."""
        if not lead.company_website:
            return lead

        url = lead.company_website
        if not url.startswith("http"):
            url = f"https://{url}"

        try:
            page = self.fetcher.get(url)
            if not page:
                return lead

            html = str(page)
            text = page.get_all_text() if hasattr(page, 'get_all_text') else html

            # Extract email
            if not lead.contact_email:
                emails = self._find_emails(html)
                if emails:
                    lead.contact_email = emails[0]

            # Extract phone
            if not lead.contact_phone:
                phones = PHONE_REGEX.findall(text)
                if phones:
                    # Filter to likely US numbers (10+ digits)
                    for p in phones:
                        digits = re.sub(r'\D', '', p)
                        if len(digits) >= 10:
                            lead.contact_phone = p.strip()
                            break

            # Detect company size from text clues
            if not lead.company_size:
                lead.company_size = self._detect_size(text) or ""

        except Exception as e:
            logger.debug(f"Enrichment failed for {lead.company_website}: {e}")

        return lead

    def enrich_many(self, leads: list[DirectLead]) -> list[DirectLead]:
        """Enrich multiple leads."""
        for lead in leads:
            self.enrich(lead)
        return leads

    def _find_emails(self, html: str) -> list[str]:
        raw = EMAIL_REGEX.findall(html)
        valid = []
        for email in raw:
            email = email.lower().strip()
            domain = email.split("@")[1] if "@" in email else ""
            if domain in EXCLUDED_EMAIL_DOMAINS:
                continue
            if email.endswith((".png", ".jpg", ".gif", ".css", ".js")):
                continue
            valid.append(email)
        return list(dict.fromkeys(valid))

    def _detect_size(self, text: str) -> str | None:
        text = text.lower()
        if any(w in text for w in ["enterprise", "fortune 500", "1000+ employees", "global team"]):
            return "enterprise"
        if any(w in text for w in ["mid-size", "200+ employees", "500 employees", "growing team"]):
            return "mid"
        if any(w in text for w in ["small team", "10+ employees", "50 employees", "boutique"]):
            return "small"
        if any(w in text for w in ["startup", "founded in 202", "early stage", "seed", "series a"]):
            return "startup"
        return None
