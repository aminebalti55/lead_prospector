"""
LinkedIn Posts scraper — finds HR/recruiter hiring posts via Bing search.

LinkedIn posts (feed updates where someone writes "we're hiring a Java developer
in Tunis") are not in /jobs/search/. But search engines index them at
linkedin.com/posts/ and linkedin.com/feed/update/. We use Bing (less aggressive
bot detection than Google) to find these posts.
"""
import logging
import re
from datetime import datetime
from urllib.parse import quote

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)

# Country to search location terms
COUNTRY_LOCATIONS = {
    "TN": ["Tunisia", "Tunis", "Tunisie"],
    "US": ["United States", "USA"],
    "GB": ["United Kingdom", "London", "UK"],
    "FR": ["France", "Paris"],
    "DE": ["Germany", "Berlin"],
    "CA": ["Canada", "Toronto"],
    "AU": ["Australia", "Sydney"],
    "AE": ["UAE", "Dubai"],
    "SA": ["Saudi Arabia", "Riyadh"],
    "MA": ["Morocco", "Maroc", "Casablanca"],
    "DZ": ["Algeria", "Algérie", "Alger"],
}

HIRING_SIGNALS = [
    "hiring", "we're hiring", "we are hiring", "looking for",
    "join our team", "join us", "open position", "we need",
    "recruiting", "urgent hire", "immediate hire",
    # French
    "on recrute", "nous recrutons", "cherche", "recherche",
    "rejoignez-nous", "poste ouvert", "recrutement", "offre d'emploi",
]


class LinkedInPostsScraper:
    SOURCE_NAME = "linkedin_posts"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self, keywords: list[str], max_results: int = 20, country: str = ""
    ) -> list[DirectLead]:
        leads = []
        location_terms = COUNTRY_LOCATIONS.get(country.upper(), []) if country else []

        for kw in keywords[:5]:
            queries = self._build_queries(kw, location_terms)

            for query in queries:
                if len(leads) >= max_results:
                    break
                try:
                    # Use Bing — much less aggressive about blocking than Google
                    url = f"https://www.bing.com/search?q={quote(query)}&count=30"
                    response = await self.engine.async_fetch_with_retry(url, self.SOURCE_NAME)
                    if response:
                        new_leads = self._parse_search_results(response, kw)
                        leads.extend(new_leads)
                        logger.info(
                            f"[linkedin_posts] '{query[:50]}...' → {len(new_leads)} results"
                        )
                except Exception as e:
                    logger.warning(f"[linkedin_posts] Search failed: {e}")

            if len(leads) >= max_results:
                break

        # Deduplicate by URL
        seen = set()
        unique = []
        for lead in leads:
            if lead.url not in seen:
                seen.add(lead.url)
                unique.append(lead)

        return unique[:max_results]

    def _build_queries(self, keyword: str, location_terms: list[str]) -> list[str]:
        queries = []
        loc = f' "{location_terms[0]}"' if location_terms else ""

        # English hiring posts
        queries.append(
            f'site:linkedin.com/posts "{keyword}" ("hiring" OR "we\'re hiring" OR "looking for" OR "join our team"){loc}'
        )

        # French hiring posts (for francophone markets)
        if location_terms:
            queries.append(
                f'site:linkedin.com/posts "{keyword}" ("on recrute" OR "recrutons" OR "cherche" OR "recrutement"){loc}'
            )

        # Also search feed/update URLs
        queries.append(
            f'site:linkedin.com "{keyword}" "hiring" OR "recrute"{loc}'
        )

        return queries[:3]

    def _parse_search_results(self, page, keyword: str) -> list[DirectLead]:
        leads = []

        # Bing results: <li class="b_algo"> contains <a href="..."> and <p> snippet
        results = page.css("li.b_algo") or page.css("ol#b_results li")
        if not results:
            # Fallback: just find all links
            results = page.css("a")
            return self._parse_fallback_links(results or [], keyword)

        for result in (results or []):
            try:
                # Get the main link
                link_el = result.css("a")[0] if result.css("a") else None
                if not link_el:
                    continue

                href = link_el.attrib.get("href", "")
                if not self._is_linkedin_post(href):
                    continue

                title = link_el.get_all_text().strip()

                # Get snippet/description
                snippet_el = (
                    (result.css("p") or [None])[0]
                    or (result.css("div.b_caption p") or [None])[0]
                    or (result.css(".b_algoSlug") or [None])[0]
                )
                snippet = snippet_el.get_all_text().strip() if snippet_el else title

                # Skip if neither title nor snippet has hiring signals
                combined = f"{title} {snippet}".lower()
                has_signal = any(s in combined for s in HIRING_SIGNALS)
                has_keyword = keyword.lower() in combined
                if not (has_signal or has_keyword):
                    continue

                poster_name = self._extract_poster_name(href)

                lead = DirectLead(
                    source="linkedin_posts",
                    title=title[:200],
                    description=snippet[:2000],
                    url=href,
                    contact_name=poster_name,
                    location="Unknown",
                )
                leads.append(lead)

            except Exception as e:
                logger.debug(f"Failed to parse search result: {e}")
                continue

        return leads

    def _parse_fallback_links(self, links, keyword: str) -> list[DirectLead]:
        """Parse raw links if structured result parsing fails."""
        leads = []
        for link in links:
            href = link.attrib.get("href", "")
            if not self._is_linkedin_post(href):
                continue
            title = link.get_all_text().strip()
            if not title or len(title) < 10:
                continue
            combined = title.lower()
            if not any(s in combined for s in HIRING_SIGNALS) and keyword.lower() not in combined:
                continue
            leads.append(DirectLead(
                source="linkedin_posts",
                title=title[:200],
                description=title[:2000],
                url=href,
                contact_name=self._extract_poster_name(href),
                location="Unknown",
            ))
        return leads

    def _is_linkedin_post(self, url: str) -> bool:
        return any(p in url for p in [
            "linkedin.com/posts/",
            "linkedin.com/feed/update/",
            "linkedin.com/pulse/",
        ])

    def _extract_poster_name(self, url: str) -> str:
        match = re.search(r'linkedin\.com/posts/([a-z0-9-]+?)[-_]', url)
        if match:
            name = match.group(1).replace("-", " ").title()
            if len(name) > 3 and not name.isdigit():
                return name
        return ""
