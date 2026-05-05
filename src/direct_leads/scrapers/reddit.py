import json
import logging
from datetime import datetime, timezone

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)

SUBREDDITS = ["forhire", "freelance", "slavelabour", "hiring"]


class RedditScraper:
    SOURCE_NAME = "reddit"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(self, keywords: list[str], max_results: int = 20) -> list[DirectLead]:
        leads: list[DirectLead] = []
        for subreddit in SUBREDDITS:
            for kw in keywords[:3]:  # limit keyword combos
                try:
                    url = (
                        f"https://www.reddit.com/r/{subreddit}/search.json"
                        f"?q={kw}&restrict_sr=1&sort=new&limit=25"
                    )
                    response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                    if response:
                        data = json.loads(response.get_all_text())
                        for post in data.get("data", {}).get("children", []):
                            pd = post.get("data", {})
                            flair = (pd.get("link_flair_text") or "").lower()
                            title_lower = pd.get("title", "").lower()
                            # Only match [Hiring] posts (people looking to hire)
                            # Exclude [For Hire] posts (people offering their services)
                            if "[for hire]" in title_lower or flair == "for hire":
                                continue
                            if flair == "hiring" or "[hiring]" in title_lower:
                                lead = DirectLead(
                                    source="reddit",
                                    title=pd.get("title", ""),
                                    description=pd.get("selftext", "")[:2000],
                                    url=f"https://reddit.com{pd.get('permalink', '')}",
                                    posted_date=datetime.fromtimestamp(
                                        pd.get("created_utc", 0), tz=timezone.utc
                                    ),
                                    location="Remote",
                                    contact_name=pd.get("author", ""),
                                )
                                leads.append(lead)
                except Exception as e:
                    logger.warning(f"Reddit search failed for r/{subreddit} '{kw}': {e}")
                if len(leads) >= max_results:
                    break
            if len(leads) >= max_results:
                break
        return leads[:max_results]
