"""Twitter scraper via Nitter mirror rotation.

Twitter's public search has been auth-walled since 2023, so we read through
public Nitter mirrors. Mirrors come and go — `nitter.net` and most of the
classic instances are dead. The list below is the actively-maintained set
as of May 2026; we shuffle on each search to spread load and skip mirrors
that don't return parseable markup.

NOTE (May 2026): The Nitter ecosystem is currently degraded — most live
mirrors return search shells with zero results because X has been
rate-limiting the upstream feed. This scraper's structure is correct and
will yield results again when mirrors recover; today it should be treated
as a best-effort source. Other direct-lead sources (LinkedIn guest API,
Indeed, Tanit, GoodFirms) carry the lead-generation load in the meantime.
"""
from __future__ import annotations

import logging
import random
from urllib.parse import quote_plus

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


NITTER_INSTANCES = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.privacyredirect.com",
    "https://lightbrd.com",
    "https://nitter.space",
    "https://nitter.tiekoetter.com",
    "https://nuku.trabun.org",
    "https://nitter.catsarch.com",
]


def _first(elements):
    return elements[0] if elements else None


def _shuffled_instances() -> list[str]:
    """Random rotation so we don't always hit the same dead mirror first."""
    pool = list(NITTER_INSTANCES)
    random.shuffle(pool)
    return pool


def _looks_like_nitter(response) -> bool:
    """Confirm the response is a Nitter mirror (search shell), not a dead
    domain or SPA. We check for Nitter-specific chrome — `nav.nav` / a search
    form or `title` containing "Nitter" — so empty-result pages still count
    as a live mirror."""
    try:
        body = response.body.decode("utf-8", errors="replace") if getattr(response, "body", None) else ""
    except Exception:
        body = ""
    if not body:
        return False
    body_lc = body.lower()
    # Strong signal: a tweet was rendered.
    try:
        if response.css("div.timeline-item") or response.css("a.tweet-link"):
            return True
    except Exception:
        pass
    # Weak signal: Nitter chrome present even with zero search results.
    has_nitter_chrome = (
        "<title>nitter" in body_lc
        or 'class="search-bar"' in body_lc
        or 'action="/search"' in body_lc
    )
    # Reject SPAs (preact/react bundles served by repurposed domains).
    looks_like_spa = "createelement" in body_lc and "<div id=\"root\"" in body_lc
    return has_nitter_chrome and not looks_like_spa


class TwitterScraper:
    SOURCE_NAME = "twitter"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        if not keywords:
            return []

        queries = [
            f'"{kw}" ("looking for" OR "need" OR "hiring")'
            for kw in keywords[:3]
        ]

        all_leads: list[DirectLead] = []
        seen_urls: set[str] = set()

        for query in queries:
            query_leads = await self._fetch_leads_from_any_mirror(query)
            if not query_leads:
                logger.warning(f"[twitter] no mirror returned tweets for: {query[:60]}")
                continue
            for lead in query_leads:
                if lead.url and lead.url in seen_urls:
                    continue
                if lead.url:
                    seen_urls.add(lead.url)
                all_leads.append(lead)
                if len(all_leads) >= max_results:
                    return all_leads[:max_results]

        return all_leads[:max_results]

    async def _fetch_leads_from_any_mirror(self, query: str) -> list[DirectLead]:
        """Try mirrors in random order; return parsed leads from the first
        mirror that yields at least one tweet. Returns [] if none do."""
        for instance in _shuffled_instances():
            url = f"{instance}/search?f=tweets&q={quote_plus(query)}"
            try:
                response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
            except Exception as e:
                logger.debug(f"[twitter] {instance} fetch raised: {e}")
                continue
            if response is None or not _looks_like_nitter(response):
                continue
            leads = self._parse_nitter(response)
            if leads:
                logger.info(f"[twitter] mirror {instance} returned {len(leads)} tweets")
                return leads
            logger.debug(f"[twitter] {instance} is live but returned 0 tweets, trying next")
        return []

    def _parse_nitter(self, page) -> list[DirectLead]:
        leads: list[DirectLead] = []
        tweets = page.css("div.timeline-item") or page.css("div.tweet-body")
        for tweet in (tweets or []):
            try:
                content_el = _first(tweet.css("div.tweet-content")) or _first(tweet.css("p"))
                if not content_el:
                    continue
                text = content_el.get_all_text().strip()
                if not text:
                    continue

                username_el = _first(tweet.css("a.username"))
                username = username_el.get_all_text().strip() if username_el else ""

                link_el = (
                    _first(tweet.css("a.tweet-link"))
                    or _first(tweet.css("a[href*='/status/']"))
                )
                tweet_url = ""
                if link_el:
                    href = link_el.attrib.get("href", "")
                    tweet_url = (
                        f"https://twitter.com{href}" if href.startswith("/") else href
                    )

                leads.append(DirectLead(
                    source="twitter",
                    title=text[:100] + ("..." if len(text) > 100 else ""),
                    description=text[:2000],
                    url=tweet_url,
                    contact_name=username,
                    location="",
                ))
            except Exception as e:
                logger.debug(f"[twitter] tweet parse error: {e}")
                continue
        return leads
