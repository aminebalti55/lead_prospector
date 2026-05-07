"""Tanit Jobs scraper — Tunisian job board, Cloudflare-protected.

Tanit's Cloudflare config is stricter than what ScraperEngine's default
StealthyFetcher call clears — we need `solve_cloudflare=True` and a wait_selector
for the listings article to appear. So this scraper bypasses engine.async_fetch
and calls StealthyFetcher directly with tuned kwargs, while still using the
engine's rate limiter for politeness.
"""
from __future__ import annotations

import logging
import math
import re
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup
from scrapling import StealthyFetcher

from src.core.models import DirectLead
from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


SEARCH_URL = "https://www.tanitjobs.com/jobs/?q={q}&l={l}&page={page}"
LISTINGS_PER_PAGE = 23

# Software-related stems. Word-boundary matched (see `_is_software_role`)
# so two-letter stems like 'ai' don't leak in via 'Anglais', 'Français', etc.
# Multi-word phrases ("data scientist") match as substrings.
_SOFTWARE_STEMS = (
    # Roles
    "developer", "developpeur", "développeur", "dev",
    "engineer", "ingenieur", "ingénieur", "engineering",
    "software", "logiciel", "informatique",
    "frontend", "front-end",
    "backend", "back-end",
    "fullstack", "full-stack",
    "full stack", "front end", "back end",
    "devops", "sysadmin", "sre",
    "data scientist", "data engineer", "data analyst",
    "machine learning", "artificial intelligence",
    # Languages / frameworks
    "react", "nextjs", "next.js",
    "vue", "vuejs", "angular", "svelte",
    "node", "nodejs", "node.js",
    "python", "django", "fastapi", "flask",
    "java", "spring",
    "kotlin", "scala", "rust", "golang",
    ".net", "dotnet", "c#", "csharp",
    "php", "laravel", "symfony",
    "ruby", "rails",
    "typescript", "javascript",
    # QA / testing
    "tester", "testeur", "qa engineer", "test automation",
    # Mobile
    "android", "swift", "flutter", "react native",
    # Cloud / infra
    "kubernetes", "docker", "terraform",
    # Platforms / CMS
    "wordpress", "shopify", "magento", "drupal",
    # Seniority / titles
    "tech lead", "team lead", "architect", "architecte",
    "founding engineer",
)

# Two-letter stems are kept separate and matched with strict word-boundaries
# so they don't leak via substrings ("ai" inside "Anglais", "ts" inside "Carts").
_SOFTWARE_SHORT_TOKENS = ("ai", "ml", "qa", "js", "ts", "ios")

# Anti-stems — phrases that strongly indicate a NON-software role even if a
# software stem accidentally appears. Negative-match wins.
_NON_SOFTWARE_TITLES = (
    "femme de menage", "femmes de menage",
    "commercial",            # sales role
    "vendeur", "vendeuse",   # sales clerk
    "comptable",             # accountant
    "secretaire",            # secretary
    "assistant administratif", "assistante administrative",
    "telemarketing", "telemarketeur",
    "operateur", "operatrice",
    "agent commercial", "agent de vente",
    "chargé de clientèle", "charge de clientele",
    "manutention", "magasinier",
    "chauffeur", "livreur",
    "barista",
    "serveur", "serveuse",
    "cuisinier", "cuisiniere",
    "femme de chambre",
)


def _normalize(text: str) -> str:
    """Lowercase + strip French/Tunisian accents for keyword matching."""
    import unicodedata
    out = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in out if not unicodedata.combining(c)).lower()


def _word_boundary_match(haystack: str, needle: str) -> bool:
    """True iff `needle` appears as a whole word (or contiguous phrase) in
    `haystack`. Both should already be lowercase + accent-stripped."""
    import re
    if not needle:
        return False
    # Treat `.`, `-`, `+`, `#` as word characters so 'next.js' / 'c#' match.
    pattern = r"(?:^|[^a-z0-9.+#-])" + re.escape(needle) + r"(?:$|[^a-z0-9.+#-])"
    return re.search(pattern, haystack) is not None


def _is_software_role(title: str, description: str, user_keywords: list[str]) -> bool:
    """True if the listing is plausibly software-related.

    Three checks, in order:
      1. Hard reject — title contains a known non-software role word
         (Commercial, Femme de ménage, Comptable, …). Negative-match wins.
      2. Positive match — the user's search keyword appears as a word, OR
         any software stem (multi-letter, word-boundary matched), OR a
         short stem (ai, ml, qa, js, ts, ios) at a word boundary.
    """
    norm_title = _normalize(title)
    norm_desc = _normalize(description)
    haystack = f"{norm_title} {norm_desc}"

    # Hard-reject by title — many Tanit listings have generic titles where
    # only the company is software-related, but the role itself is sales /
    # admin / support. Trust the title verb.
    for blacklisted in _NON_SOFTWARE_TITLES:
        if blacklisted in norm_title:
            return False

    # Try user keywords first (most specific signal).
    for kw in user_keywords:
        kw_norm = _normalize(kw)
        if not kw_norm:
            continue
        # Multi-word keyword → substring is fine. Single-word → word boundary.
        if " " in kw_norm:
            if kw_norm in haystack:
                return True
        elif _word_boundary_match(haystack, kw_norm):
            return True

    # Multi-letter software stems — substring OK because they're long enough
    # that false-positives are unlikely.
    for stem in _SOFTWARE_STEMS:
        stem_norm = _normalize(stem)
        if stem_norm and stem_norm in haystack:
            return True

    # Short tokens — strict word boundary required.
    for token in _SOFTWARE_SHORT_TOKENS:
        if _word_boundary_match(haystack, token):
            return True

    return False


def _strip_session_params(url: str) -> str:
    """Remove ?backPage=...&searchID=... so dedup works across runs."""
    if not url:
        return ""
    parsed = urlparse(url)
    # Drop query string entirely — Tanit detail URLs are stable as path-only
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return base


def _clean_text(s: str | None) -> str:
    if not s:
        return ""
    # Collapse all whitespace runs into a single space
    return re.sub(r"\s+", " ", s).strip()


def parse_listing_html(html: str) -> list[DirectLead]:
    """Parse a Tanit listing page (search results) into DirectLead objects.

    Selectors match the live structure as of this plan's recon (May 2026)."""
    soup = BeautifulSoup(html, "html.parser")
    leads: list[DirectLead] = []

    # Match cards with class containing 'listing-item__jobs' (featured cards have an extra class).
    articles = soup.select("article.listing-item__jobs")
    for article in articles:
        title_anchor = article.select_one(".listing-item__title a")
        if not title_anchor:
            continue
        title_text = _clean_text(title_anchor.get_text())
        href = title_anchor.get("href", "")
        url = _strip_session_params(href)
        if not url or not title_text:
            continue

        # Featured marker: prepend "[Featured] " for downstream visibility
        is_featured = "listing-item__featured" in (article.get("class") or [])
        if is_featured:
            title_text = f"[Featured] {title_text}"

        company_el = article.select_one(".listing-item-info-company")
        company = _clean_text((company_el.get_text() if company_el else "")) or ""
        # Strip a trailing " -" that always follows the company on the live site
        if company.endswith(" -"):
            company = company[:-2].rstrip()
        elif company.endswith("-"):
            company = company[:-1].rstrip()

        location_el = article.select_one(".listing-item-info-location")
        location = _clean_text(location_el.get_text() if location_el else "") or ""

        desc_el = article.select_one(".listing-item__desc")
        description = _clean_text(desc_el.get_text() if desc_el else "")[:500]

        leads.append(DirectLead(
            source="tanit",
            title=title_text,
            description=description,
            url=url,
            posted_date=None,  # Not on listing page; v1 leaves None
            company_name=company,
            location=location,
            contact_name="",
            contact_email="",
            contact_phone="",
        ))

    return leads


class TanitScraper:
    SOURCE_NAME = "tanit"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self,
        keywords: list[str],
        max_results: int = 20,
    ) -> list[DirectLead]:
        if not keywords:
            return []

        # Tanit's `q` param accepts one phrase. Use the first keyword for the URL;
        # the relevance matcher post-filters using the full skill list anyway.
        primary_kw = keywords[0]

        # How many pages do we need? ceil(max_results / 23), capped at 10 (safety).
        pages_needed = max(1, min(10, math.ceil(max_results / LISTINGS_PER_PAGE)))

        all_leads: list[DirectLead] = []
        for page in range(1, pages_needed + 1):
            url = SEARCH_URL.format(
                q=quote_plus(primary_kw),
                l="",
                page=page,
            )
            try:
                # Rate-limit via the engine's limiter (don't spam Tanit), but
                # call StealthyFetcher directly to pass Cloudflare-bypass kwargs.
                await self.engine.rate_limiter.wait_async("tanit")
                self.engine.rate_limiter.record_request("tanit")
                response = await StealthyFetcher.async_fetch(
                    url,
                    solve_cloudflare=True,
                    wait_selector="article.listing-item__jobs",
                    wait=3000,
                    network_idle=True,
                    google_search=True,
                )
                if not response:
                    continue
                # Use html_content (raw HTML) not get_all_text (strips tags)
                html = (
                    response.html_content
                    if getattr(response, "html_content", None)
                    else (response.body or b"").decode("utf-8", errors="replace")
                )
                page_leads = parse_listing_html(str(html))
                # Tanit's q-param filter is too loose — cleaning, sales, and
                # admin jobs slip through. Drop anything that doesn't look
                # software-related.
                before = len(page_leads)
                page_leads = [
                    l for l in page_leads
                    if _is_software_role(l.title, l.description, keywords)
                ]
                dropped = before - len(page_leads)
                if dropped:
                    logger.info(f"[tanit] dropped {dropped} non-software listings on page {page}")
                all_leads.extend(page_leads)
                # If a page returned zero results, we've hit the end — stop early.
                if before == 0:
                    break
            except Exception as e:
                logger.warning(f"[tanit] page {page} fetch failed: {e}")
                continue

        return all_leads[:max_results]
