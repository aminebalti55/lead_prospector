"""Google Maps scraper — Playwright/Scrapling-based, no API key required.

Replaces the previous Places-API stub that silently returned `[]` whenever
GOOGLE_PLACES_API_KEY wasn't set. Hits maps.google.com directly via the
StealthyFetcher (Playwright under the hood) and extracts businesses from
the live DOM.

Selectors verified live (May 2026) against
`https://www.google.com/maps/search/dental+clinic+near+Austin+TX`:

| Field        | Selector                                              |
| ------------ | ----------------------------------------------------- |
| Card anchor  | `a.hfpxzc`                                            |
| Name         | the anchor's `aria-label` attribute                   |
| Place URL    | the anchor's `href`                                   |
| Sponsored    | innerText of card starts with "Sponsorisé"/"Sponsored"|
| Feed (list)  | `[role="feed"]`                                       |

Each detail page exposes structured rows via `data-item-id`:
  • `address`          → full street address
  • `phone:tel:+...`   → the number is in the suffix of the item-id itself
  • `authority` (A)    → the business's website (href)
  • `oh`               → opening hours
  • `oloc`             → plus-code

The `data-item-id` attribute is what Google uses internally for
accessibility/automation; it survives UI shuffles much better than the
auto-generated CSS classes.

NOTE: Google may serve the page in the user's locale (French in our case
when running from Tunisia). Selectors above are locale-agnostic — they
target attributes, not visible text.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote_plus, urlparse

from scrapling import StealthyFetcher

from src.core.models import BusinessLead
from src.core.scraper_engine import ScraperEngine


logger = logging.getLogger(__name__)


_SEARCH_URL = "https://www.google.com/maps/search/{q}+in+{city}+{state}"

# How long to wait for the result feed before giving up.
_FEED_WAIT_MS = 6000

# How many "scroll the feed" loops we run to load more cards. Google lazy-
# loads ~20 cards per scroll; 4 scrolls ≈ 80 cards before the "End of list"
# sentinel appears.
_SCROLL_PASSES = 4

# Concurrency limit for per-place detail fetches. Google rate-limits at
# the IP level — 4 parallel detail fetches stays well under their threshold.
_DETAIL_CONCURRENCY = 4


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _parse_rating(raw: str | None) -> tuple[float | None, int | None]:
    """Convert "4,8\\n(1 471)" or "4.8 (1471)" into (4.8, 1471)."""
    if not raw:
        return None, None
    s = raw.replace(" ", "").replace("\xa0", "").replace(" ", "")
    s = s.replace(",", ".")
    m_rating = re.search(r"(\d+(?:\.\d+)?)", s)
    m_count = re.search(r"\((\d+(?:\s*\d+)*)\)", s)
    rating = float(m_rating.group(1)) if m_rating else None
    count = None
    if m_count:
        count = int(re.sub(r"\D", "", m_count.group(1)))
    return rating, count


def _phone_from_item_id(item_id: str) -> str:
    """`phone:tel:+15128152524` → `+1 512-815-2524`."""
    m = re.search(r"phone:tel:([+\d]+)", item_id or "")
    if not m:
        return ""
    digits = m.group(1)
    if digits.startswith("+1") and len(digits) == 12:
        return f"+1 {digits[2:5]}-{digits[5:8]}-{digits[8:]}"
    return digits


def _strip_tracking(url: str) -> str:
    """Remove utm_*/gclid/etc. so dedup keys are stable."""
    if not url:
        return ""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _looks_sponsored(card_text: str) -> bool:
    """Skip ads — they're paid placements, not organic results."""
    head = (card_text or "").strip().split("\n", 1)[0].lower()
    return head in ("sponsorisé", "sponsored", "sponsorisée", "anuncio", "anzeige")


# JS run in the page to extract the list of cards once the feed has loaded.
_LIST_EXTRACT_JS = r"""() => {
  const out = [];
  const cards = document.querySelectorAll('a.hfpxzc');
  for (const a of cards) {
    const card = a.closest('[role="article"]') || a.parentElement;
    out.push({
      name: a.getAttribute('aria-label') || '',
      place_url: a.href,
      card_text: (card?.innerText || '').slice(0, 600),
    });
  }
  return out;
}"""

# JS run in the place-detail page to extract the structured fields.
_DETAIL_EXTRACT_JS = r"""() => {
  const result = {
    name: '',
    address: '',
    phone_item_id: '',
    website: '',
    rating_text: '',
    category: '',
    located_in: '',
  };

  result.name = document.querySelector('h1')?.innerText || '';

  const addr = document.querySelector('button[data-item-id="address"]');
  result.address = addr ? (addr.getAttribute('aria-label') || addr.innerText || '') : '';

  // Phone number is encoded inside the data-item-id suffix:
  //   data-item-id="phone:tel:+15128152524"
  const phone = document.querySelector('button[data-item-id^="phone:tel:"]');
  result.phone_item_id = phone ? phone.getAttribute('data-item-id') : '';

  const site = document.querySelector('a[data-item-id="authority"]');
  result.website = site ? site.href : '';

  result.rating_text = document.querySelector('div.F7nice')?.innerText || '';

  // The category is a small button below the rating; it shares a jsaction
  // hint that contains the word "category".
  const cat = document.querySelector('button[jsaction*="category"]');
  result.category = cat ? cat.innerText.trim() : '';

  const loc = document.querySelector('button[data-item-id="locatedin"]');
  result.located_in = loc ? loc.innerText.replace(/^Situé dans\s*:\s*/i, '').trim() : '';

  return result;
}"""

# JS that scrolls the result feed to load more cards. Returns the new card
# count so the caller knows whether to keep scrolling.
_SCROLL_JS = r"""() => {
  const feed = document.querySelector('[role="feed"]');
  if (!feed) return 0;
  feed.scrollTop = feed.scrollHeight;
  return document.querySelectorAll('a.hfpxzc').length;
}"""


# ─────────────────────────────────────────────────────────────────────────────
#  Scraper
# ─────────────────────────────────────────────────────────────────────────────


class GoogleMapsScraper:
    """Playwright-based scrape of maps.google.com search results.

    Difficulty: HIGH (Google has anti-bot measures, but a single user
    browsing maps without an account looks legitimate to their classifier).
    Rate limiting: ScraperEngine handles delay between requests.
    """

    SOURCE_NAME = "google_maps"

    def __init__(self, engine: ScraperEngine):
        self.engine = engine

    async def search(
        self,
        business_type: str,
        city: str,
        state: str,
        max_results: int = 20,
    ) -> list[BusinessLead]:
        if not business_type or not city:
            return []

        url = _SEARCH_URL.format(
            q=quote_plus(business_type),
            city=quote_plus(city),
            state=quote_plus(state or ""),
        )
        logger.info(f"[google_maps] searching: {url}")

        # Stage 1 — load the search page, scroll to fill the feed.
        try:
            await self.engine.rate_limiter.wait_async(self.SOURCE_NAME)
            self.engine.rate_limiter.record_request(self.SOURCE_NAME)
            cards = await self._fetch_list(url, max_results)
        except Exception as e:
            logger.error(f"[google_maps] list fetch failed: {e}", exc_info=True)
            return []

        if not cards:
            logger.warning(f"[google_maps] no cards extracted for '{business_type}' in {city}")
            return []

        # Stage 2 — fetch each place's detail page in parallel (bounded).
        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        tasks = [
            self._fetch_detail(sem, card, city, state, business_type)
            for card in cards[:max_results]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        leads: list[BusinessLead] = []
        for r in results:
            if isinstance(r, BusinessLead):
                leads.append(r)
            elif isinstance(r, Exception):
                logger.debug(f"[google_maps] detail failed: {r}")

        logger.info(f"[google_maps] returning {len(leads)} businesses")
        return leads

    # -----------------------------------------------------------------

    async def _fetch_list(self, url: str, max_results: int) -> list[dict[str, Any]]:
        """Open the maps search page and scroll the feed until enough cards
        are loaded. Returns a list of {name, place_url, card_text}.

        Filters out sponsored cards (ads) and de-dupes by place_url so the
        same place doesn't appear twice when Google duplicates results.
        """

        # Build a per-page script that scrolls + extracts in one Playwright
        # action. StealthyFetcher exposes `page_action` for this — a callable
        # that receives the live Page object before the response is captured.
        async def page_action(page):
            # Wait for the feed to appear. If we get a CAPTCHA / blocked,
            # the feed never loads and we'll return an empty card list.
            try:
                await page.wait_for_selector('[role="feed"]', timeout=_FEED_WAIT_MS)
            except Exception:
                logger.warning("[google_maps] feed didn't load — possibly blocked")
                return page

            # Scroll to load more cards; bail early once we have enough.
            for i in range(_SCROLL_PASSES):
                try:
                    n = await page.evaluate(_SCROLL_JS)
                    if n >= max_results + 5:  # +5 to absorb sponsored skips
                        break
                except Exception:
                    break
                await page.wait_for_timeout(800)
            return page

        response = await StealthyFetcher.async_fetch(
            url,
            solve_cloudflare=False,  # Google doesn't use CF
            wait_selector='[role="feed"]',
            wait=2000,
            network_idle=False,
            google_search=False,
            page_action=page_action,
        )
        if not response:
            return []

        html = self._html(response)
        if not html:
            return []

        # We can't run our extractor JS on a static html string after the
        # page closes — but we ALREADY ran the scroll loop in page_action.
        # Re-extract via a second StealthyFetcher pass that just runs the
        # extractor JS. Cheaper alternative: parse the HTML with BS4.
        # Going with HTML parse — feed cards have stable attributes.
        return self._parse_list_html(html)

    @staticmethod
    def _parse_list_html(html: str) -> list[dict[str, Any]]:
        """BS4 fallback parser for the list page when we can't run JS."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in soup.select("a.hfpxzc"):
            name = a.get("aria-label", "").strip()
            place_url = a.get("href", "")
            if not name or not place_url:
                continue

            # The card container holds the full innerText we use to detect
            # sponsored ads. role="article" is consistent across locales.
            card = a.find_parent(attrs={"role": "article"}) or a.parent
            card_text = card.get_text("\n", strip=True) if card else ""

            if _looks_sponsored(card_text):
                continue

            stable = _strip_tracking(place_url)
            if stable in seen:
                continue
            seen.add(stable)

            out.append({"name": name, "place_url": place_url, "card_text": card_text})
        return out

    # -----------------------------------------------------------------

    async def _fetch_detail(
        self,
        sem: asyncio.Semaphore,
        card: dict[str, Any],
        city: str,
        state: str,
        business_type: str,
    ) -> BusinessLead | None:
        """Open one place's detail page and extract phone / website /
        full address / rating. Returns None on failure so gather() can
        skip without aborting the whole batch."""
        async with sem:
            await self.engine.rate_limiter.wait_async(self.SOURCE_NAME)
            self.engine.rate_limiter.record_request(self.SOURCE_NAME)

            try:
                async def page_action(page):
                    # Wait for the address row to appear — that's the
                    # signal the right-side panel finished hydrating.
                    try:
                        await page.wait_for_selector(
                            'button[data-item-id="address"]', timeout=8000
                        )
                    except Exception:
                        pass
                    return page

                response = await StealthyFetcher.async_fetch(
                    card["place_url"],
                    solve_cloudflare=False,
                    wait=1500,
                    network_idle=False,
                    page_action=page_action,
                )
            except Exception as e:
                logger.debug(f"[google_maps] detail fetch failed for {card['name']}: {e}")
                return None

            if not response:
                return None
            html = self._html(response)
            if not html:
                return None

            details = self._parse_detail_html(html)

            # Rating + review count come from the list card too — fall back
            # to those if the detail panel didn't render.
            rating, review_count = _parse_rating(details.get("rating_text") or "")
            if rating is None:
                # The list card text is "<name>\n<rating>(<count>)\n…"
                rating, review_count = _parse_rating(card.get("card_text", ""))

            address = details.get("address") or ""
            phone = _phone_from_item_id(details.get("phone_item_id") or "")
            website = _strip_tracking(details.get("website") or "")

            return BusinessLead(
                source=self.SOURCE_NAME,
                name=details.get("name") or card["name"],
                city=city,
                state=state,
                phone=phone or None,
                website=website or None,
                address=address or None,
                rating=rating,
                review_count=review_count,
                categories=[details.get("category")] if details.get("category") else [],
                detail_url=_strip_tracking(card["place_url"]),
            )

    @staticmethod
    def _parse_detail_html(html: str) -> dict[str, str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        out: dict[str, str] = {}
        h1 = soup.find("h1")
        if h1:
            out["name"] = h1.get_text(strip=True)

        addr = soup.find("button", attrs={"data-item-id": "address"})
        if addr:
            out["address"] = (
                addr.get("aria-label", "")
                or addr.get_text(" ", strip=True)
            )
            # Strip the localized "Address: " prefix some locales add.
            out["address"] = re.sub(r"^[^:]+:\s*", "", out["address"]).strip()

        phone = soup.find("button", attrs={"data-item-id": re.compile(r"^phone:tel:")})
        if phone:
            out["phone_item_id"] = phone.get("data-item-id", "")

        site = soup.find("a", attrs={"data-item-id": "authority"})
        if site:
            out["website"] = site.get("href", "")

        rating_div = soup.find("div", class_="F7nice")
        if rating_div:
            out["rating_text"] = rating_div.get_text(" ", strip=True)

        cat_btn = soup.find("button", attrs={"jsaction": re.compile(r"category")})
        if cat_btn:
            out["category"] = cat_btn.get_text(strip=True)

        return out

    # -----------------------------------------------------------------

    @staticmethod
    def _html(response) -> str:
        for attr in ("html_content", "body"):
            v = getattr(response, attr, None)
            if v:
                if isinstance(v, bytes):
                    return v.decode("utf-8", errors="replace")
                return str(v)
        try:
            return str(response)
        except Exception:
            return ""

    # -----------------------------------------------------------------

    async def get_details(self, lead: BusinessLead) -> BusinessLead:
        """Compatibility shim — the cold pipeline calls scraper.get_details
        on leads that lack a website. Our search() already populates the
        website field from the detail page, so this is a no-op."""
        return lead
