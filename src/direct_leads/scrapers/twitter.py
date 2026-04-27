import logging

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


def _first(elements):
    return elements[0] if elements else None


class TwitterScraper:
    SOURCE_NAME = "twitter"
    NITTER_INSTANCES = ["https://nitter.net", "https://nitter.privacydev.net"]

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        leads = []
        search_queries = [
            f'"{kw}" "looking for" OR "need" OR "hiring"' for kw in keywords[:3]
        ]

        for query in search_queries:
            for instance in self.NITTER_INSTANCES:
                try:
                    url = f"{instance}/search?f=tweets&q={query.replace(' ', '+')}"
                    response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                    if response:
                        new_leads = self._parse_nitter(response, instance)
                        leads.extend(new_leads)
                        if new_leads:
                            break
                except Exception:
                    continue
            if len(leads) >= max_results:
                break

        return leads[:max_results]

    def _parse_nitter(self, page, instance: str) -> list[DirectLead]:
        leads = []
        tweets = page.css("div.timeline-item") or page.css("div.tweet-body")
        for tweet in (tweets or []):
            try:
                content_el = _first(tweet.css("div.tweet-content")) or _first(tweet.css("p"))
                if not content_el:
                    continue
                text = content_el.get_all_text().strip()

                username_el = _first(tweet.css("a.username"))
                username = username_el.get_all_text().strip() if username_el else ""

                link_el = _first(tweet.css("a.tweet-link")) or _first(tweet.css("a[href*='/status/']"))
                tweet_url = ""
                if link_el:
                    href = link_el.attrib.get("href", "")
                    tweet_url = (
                        f"https://twitter.com{href}" if href.startswith("/") else href
                    )

                lead = DirectLead(
                    source="twitter",
                    title=text[:100] + ("..." if len(text) > 100 else ""),
                    description=text[:2000],
                    url=tweet_url,
                    contact_name=username,
                    location="Unknown",
                )
                leads.append(lead)
            except Exception:
                continue
        return leads
