import logging

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


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

        # Try Nitter (public Twitter mirrors)
        for query in search_queries:
            for instance in self.NITTER_INSTANCES:
                try:
                    url = f"{instance}/search?f=tweets&q={query.replace(' ', '+')}"
                    response = self.engine.fetch_with_retry(url, self.SOURCE_NAME)
                    if response:
                        new_leads = self._parse_nitter(response, instance)
                        leads.extend(new_leads)
                        if new_leads:
                            break  # This instance works
                except Exception:
                    continue
            if len(leads) >= max_results:
                break

        return leads[:max_results]

    def _parse_nitter(self, page, instance: str) -> list[DirectLead]:
        leads = []
        tweets = page.css("div.timeline-item") or page.css("div.tweet-body")
        for tweet in tweets:
            try:
                content_el = tweet.css_first("div.tweet-content") or tweet.css_first("p")
                if not content_el:
                    continue
                text = content_el.get_all_text().strip()

                username_el = tweet.css_first("a.username")
                username = username_el.get_all_text().strip() if username_el else ""

                link_el = tweet.css_first("a.tweet-link") or tweet.css_first(
                    "a[href*='/status/']"
                )
                tweet_url = ""
                if link_el:
                    href = link_el.attrib.get("href", "")
                    tweet_url = (
                        f"https://twitter.com{href}" if href.startswith("/") else href
                    )

                date_el = tweet.css_first("span.tweet-date a") or tweet.css_first("time")

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
