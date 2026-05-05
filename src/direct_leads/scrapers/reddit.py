"""Reddit scraper — public search.json with hardened request path.

Three issues with the previous version caused recurring scrape failures:
1. The keyword was concatenated into the URL without escaping — multi-word
   queries broke or returned wrong results.
2. No custom User-Agent was sent — Reddit silently rate-limits requests
   carrying default Python/library UAs and returns either 429 or empty JSON.
3. `json.loads(response.get_all_text())` crashed when Reddit served an HTML
   error page (rate-limit notice, "you broke reddit") instead of JSON, which
   killed the loop early and looked like "no leads found."

Fixes:
- `quote_plus` on the keyword.
- A descriptive UA per Reddit's API guidelines (unique platform/app id).
- A defensive JSON guard that logs the response prefix and continues on bad
  payloads instead of raising.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus

from scrapling import Fetcher

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


SUBREDDITS = [
    # General hiring boards
    "forhire", "freelance", "slavelabour", "hiring",
    # Remote-dev specific
    "remotejs", "jobbit",
    # Stack-specific dev hiring threads
    "reactjs", "webdev", "node", "django",
]

# Reddit's API guidelines ask for a unique, descriptive User-Agent.
# Format: <platform>:<app id>:<version> (by /u/<username>)
USER_AGENT = "windows:lead-prospector:0.1 (by /u/lead-prospector-bot)"


def _safe_json_parse(body_text: str, source_label: str) -> dict | None:
    """Parse JSON, return None on failure with a logged prefix so we can
    distinguish between rate-limit HTML pages and genuine empty results."""
    if not body_text:
        return None
    stripped = body_text.lstrip()
    if not stripped.startswith(("{", "[")):
        logger.warning(
            f"[reddit] {source_label} returned non-JSON "
            f"(prefix: {stripped[:120]!r})"
        )
        return None
    try:
        return json.loads(body_text)
    except json.JSONDecodeError as e:
        logger.warning(f"[reddit] {source_label} JSON decode failed: {e}")
        return None


class RedditScraper:
    SOURCE_NAME = "reddit"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        if not keywords:
            return []

        leads: list[DirectLead] = []
        seen_urls: set[str] = set()

        for subreddit in SUBREDDITS:
            for kw in keywords[:3]:
                url = (
                    f"https://www.reddit.com/r/{subreddit}/search.json"
                    f"?q={quote_plus(kw)}&restrict_sr=1&sort=new&limit=25"
                )
                try:
                    await self.engine.rate_limiter.wait_async(self.SOURCE_NAME)
                    self.engine.rate_limiter.record_request(self.SOURCE_NAME)
                    # Bypass engine fetch so we can pass Reddit's required UA.
                    response = await asyncio.to_thread(
                        Fetcher().get,
                        url,
                        headers={"User-Agent": USER_AGENT},
                    )
                except Exception as e:
                    logger.warning(f"[reddit] r/{subreddit} '{kw}' fetch failed: {e}")
                    continue
                if not response:
                    continue

                # Prefer raw body over get_all_text so we don't lose JSON braces.
                try:
                    body = (
                        response.body.decode("utf-8", errors="replace")
                        if getattr(response, "body", None)
                        else response.get_all_text()
                    )
                except Exception:
                    body = ""

                data = _safe_json_parse(body, f"r/{subreddit}?q={kw}")
                if not data:
                    continue

                for post in data.get("data", {}).get("children", []):
                    pd = post.get("data", {}) or {}
                    flair = (pd.get("link_flair_text") or "").lower()
                    title_lower = (pd.get("title") or "").lower()

                    # Exclude self-promotion: people advertising their own services.
                    if "[for hire]" in title_lower or flair == "for hire":
                        continue
                    # Only keep [hiring] posts: people looking to pay someone.
                    if not (flair == "hiring" or "[hiring]" in title_lower):
                        continue

                    permalink = pd.get("permalink", "")
                    lead_url = f"https://reddit.com{permalink}" if permalink else ""
                    if not lead_url or lead_url in seen_urls:
                        continue
                    seen_urls.add(lead_url)

                    leads.append(DirectLead(
                        source="reddit",
                        title=pd.get("title", ""),
                        description=(pd.get("selftext") or "")[:2000],
                        url=lead_url,
                        posted_date=datetime.fromtimestamp(
                            pd.get("created_utc", 0), tz=timezone.utc
                        ) if pd.get("created_utc") else None,
                        location="Remote",
                        contact_name=pd.get("author", ""),
                    ))

                    if len(leads) >= max_results:
                        return leads[:max_results]

        return leads[:max_results]
