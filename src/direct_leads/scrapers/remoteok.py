"""RemoteOK scraper — public JSON API.

RemoteOK exposes its full job feed at `https://remoteok.com/api` as a JSON
array. The first element is a metadata stub (`{"legal": "..."}`); the rest
are job objects with stable fields: id, position, company, description,
tags, location, salary_min, salary_max, apply_url, url, date.

No auth, no Cloudflare, no rate-limiting beyond polite use. Filtering is
client-side: we keep entries whose tags or position match any of the user's
search keywords (case-insensitive, word-boundary).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


API_URL = "https://remoteok.com/api"


def _matches_keyword(entry: dict, kw_lower: str) -> bool:
    """True if the keyword appears in tags, position, or description."""
    pattern = re.compile(r"\b" + re.escape(kw_lower) + r"\b", re.IGNORECASE)
    if any(pattern.search(t) for t in (entry.get("tags") or [])):
        return True
    if pattern.search(entry.get("position") or ""):
        return True
    if pattern.search((entry.get("description") or "")[:500]):
        return True
    return False


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _entry_to_lead(entry: dict) -> DirectLead | None:
    position = (entry.get("position") or "").strip()
    if not position:
        return None
    url = (entry.get("url") or entry.get("apply_url") or "").strip()
    if not url:
        return None

    salary_min = entry.get("salary_min") or 0
    salary_max = entry.get("salary_max") or 0
    salary_signal = ""
    if salary_min or salary_max:
        salary_signal = f"${salary_min}-${salary_max}" if salary_max else f"${salary_min}+"

    desc = (entry.get("description") or "")
    # Description is HTML; strip tags lazily for storage.
    desc = re.sub(r"<[^>]+>", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip()[:2000]
    if salary_signal:
        desc = f"[{salary_signal}] {desc}" if desc else f"[{salary_signal}]"

    return DirectLead(
        source="remoteok",
        title=position,
        description=desc,
        url=url,
        company_name=(entry.get("company") or "").strip(),
        location=(entry.get("location") or "Remote").strip() or "Remote",
        posted_date=_parse_date(entry.get("date") or ""),
        budget_signal=salary_signal,
    )


class RemoteOKScraper:
    SOURCE_NAME = "remoteok"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        if not keywords:
            return []
        try:
            await self.engine.rate_limiter.wait_async(self.SOURCE_NAME)
            self.engine.rate_limiter.record_request(self.SOURCE_NAME)
            response = await self.engine.async_fetch_with_retry(API_URL, self.SOURCE_NAME)
        except Exception as e:
            logger.warning(f"[remoteok] fetch failed: {e}")
            return []
        if not response:
            return []

        try:
            body = (
                response.body.decode("utf-8", errors="replace")
                if getattr(response, "body", None)
                else response.get_all_text()
            )
            data = json.loads(body)
        except Exception as e:
            logger.warning(f"[remoteok] JSON parse failed: {e}")
            return []

        entries = [e for e in data if isinstance(e, dict) and e.get("id")]

        kw_lowers = [k.lower() for k in keywords]
        matched: list[DirectLead] = []
        seen_urls: set[str] = set()
        for entry in entries:
            if not any(_matches_keyword(entry, kw) for kw in kw_lowers):
                continue
            lead = _entry_to_lead(entry)
            if not lead or lead.url in seen_urls:
                continue
            seen_urls.add(lead.url)
            matched.append(lead)
            if len(matched) >= max_results:
                break

        return matched
