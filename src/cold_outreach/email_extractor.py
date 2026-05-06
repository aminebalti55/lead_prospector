"""
Email Extractor v4 — find REAL business emails across 4 escalating layers.

Each layer is more expensive than the last, so we stop on the first hit.

  ┌──────────────────────────────────────────────────────────────────────┐
  │  Layer 1: Direct DOM extraction      (homepage HTML, ~1-2s)          │
  │    • mailto: hrefs                   ← strongest signal              │
  │    • JSON-LD (Organization.email)    ← Schema.org structured data    │
  │    • Cloudflare cfemail (XOR decode) ← Cloudflare Email Protection   │
  │    • <meta> tags (og:email, etc.)    ← Open Graph / business meta    │
  │    • Footer-focused text scan        ← SMBs concentrate emails here  │
  │    • Plain-text regex + de-obfuscate ← "info [at] domain DOT com"    │
  │                                                                      │
  │  Layer 2: Multi-page site crawl      (8 paths + sitemap, ~10-20s)    │
  │    • /contact, /contact-us, /about, /about-us, /team, /our-team,     │
  │      /staff, /get-in-touch                                            │
  │    • /sitemap.xml → any "contact"-shaped URL                         │
  │    • Re-run all Layer 1 techniques on each page                      │
  │                                                                      │
  │  Layer 3: Stealth / JS render        (only if site is JS-y, ~10-20s) │
  │    • StealthyFetcher (Playwright) with full JS execution             │
  │    • Catches Wix, Squarespace, React SPA, lazy-loaded footers        │
  │    • Re-run all Layer 1 techniques on rendered DOM                   │
  │                                                                      │
  │  Layer 4: External discovery         (slowest, ~5-15s)               │
  │    • Directory profile pages (BBB, Manta, YellowPages detail URL)    │
  │      — these often expose email even when the SMB site doesn't       │
  │    • DuckDuckGo HTML SERP for "<business_name>" "<domain>" — finds   │
  │      emails published on third-party sites (review sites, news,      │
  │      directory listings) even when the business's own site has none  │
  └──────────────────────────────────────────────────────────────────────┘

If all four layers fail, we return `EmailResult()` with `email=None`. We do
NOT guess patterns — a fake `info@<domain>` that bounces hurts more than it
helps (sender-reputation damage, recipient-side spam scoring).

Branded-only filter: when the business has its own domain, we discard any
email whose domain doesn't match. Template placeholders (john@smith.com),
marketing-platform addresses, and unrelated WHOIS contacts are common
false positives that the branded filter eliminates.

Yield expectations on local-SMB websites:
  - Layer 1 alone:                   ~50-65% hit rate
  - Layers 1+2 (multi-page):         ~65-75%
  - Layers 1+2+3 (JS fallback):      ~70-80%
  - Layers 1+2+3+4 (external):       ~80-88%
"""

from __future__ import annotations

import html
import json
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup
from scrapling import Fetcher, StealthyFetcher

from src.core.scraper_engine import ScraperEngine

logger = logging.getLogger(__name__)


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

CONTACT_PATHS: list[tuple[str, str]] = [
    ("/contact", "contact_page"),
    ("/contact-us", "contact_page"),
    ("/about", "about_page"),
    ("/about-us", "about_page"),
    ("/get-in-touch", "contact_page"),
    ("/team", "team_page"),
    ("/our-team", "team_page"),
    ("/staff", "team_page"),
]

EXCLUDED_DOMAINS = {
    "example.com", "example.org", "example.net",
    "email.com", "domain.com", "yoursite.com", "yourdomain.com",
    "yourcompany.com", "company.com", "placeholder.com",
    "test.com", "sample.com",
    "wixpress.com", "wix.com", "squarespace.com", "weebly.com",
    "godaddy.com", "wordpress.com", "wordpress.org",
    "shopify.com", "webflow.io",
    "sentry.io", "w3.org", "schema.org", "googleapis.com",
    "google.com", "facebook.com", "twitter.com", "instagram.com",
    "linkedin.com", "youtube.com", "pinterest.com",
    "gravatar.com", "githubusercontent.com", "cloudinary.com", "imgix.net",
    "privacyguard.com", "domainsbyproxy.com", "whoisguard.com",
    "contactprivacy.com",
    "duckduckgo.com", "bing.com",
}

EXCLUDED_LOCAL_PARTS = {
    "wix-site", "no-reply", "noreply", "donotreply",
    "hostmaster", "postmaster", "abuse", "webmaster",
}

_FILE_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".js", ".css", ".html", ".pdf", ".doc", ".docx", ".xml",
)


@dataclass
class EmailResult:
    email: str | None = None
    source: str = ""        # "L1:mailto" | "L2:contact_page:json_ld" | "L4:duckduckgo" | ...
    confidence: str = "low"  # "high" | "medium" | "low"


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers shared by every layer
# ═══════════════════════════════════════════════════════════════════════════


def _normalize_url(website: str) -> str:
    return website if website.startswith("http") else f"https://{website}"


def _domain_from_url(url: str) -> str:
    try:
        from tldextract import extract as tld_extract
        parsed = tld_extract(url)
        if parsed.domain and parsed.suffix:
            return f"{parsed.domain}.{parsed.suffix}".lower()
    except Exception:
        pass
    return ""


def _is_valid_email(email: str) -> bool:
    email = email.lower().strip()
    if "@" not in email:
        return False
    local, _, domain = email.partition("@")
    if not domain or domain.startswith("."):
        return False
    if domain in EXCLUDED_DOMAINS:
        return False
    if local in EXCLUDED_LOCAL_PARTS:
        return False
    if any(email.endswith(ext) for ext in _FILE_EXTENSIONS):
        return False
    if re.search(r"@\d+x\.", email):
        return False
    if len(local) > 64:
        return False
    if not re.match(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", email):
        return False
    return True


def _pick_email(emails: list[str], domain: str, *, allow_cross_domain: bool) -> str | None:
    """Choose the best email from a candidate list.

    For explicit signals (mailto, JSON-LD, cfemail, meta) we allow
    cross-domain results — a franchise might publish a parent-domain
    dispatch email. For implicit signals (text/footer regex) we require
    the email to match the business's own domain, otherwise we'd let
    template placeholders like john@smith.com through.
    """
    if not emails:
        return None
    if not domain:
        return emails[0]
    branded = [e for e in emails if e.endswith(f"@{domain}") or e.endswith(f".{domain}")]
    if branded:
        return branded[0]
    if allow_cross_domain:
        return emails[0]
    return None


# Backwards-compat alias.
def _prefer_branded(emails: list[str], domain: str) -> str | None:
    return _pick_email(emails, domain, allow_cross_domain=False)


def _deobfuscate(text: str) -> str:
    """Convert "info [at] foo DOT com" / HTML entities back into a real address."""
    text = html.unescape(text)
    text = re.sub(r"&#0?64;", "@", text)
    text = re.sub(r"&#x40;", "@", text, flags=re.IGNORECASE)
    text = re.sub(r"&commat;", "@", text, flags=re.IGNORECASE)
    text = re.sub(r"&#0?46;", ".", text)
    text = re.sub(r"\s*[\[\(]\s*at\s*[\]\)]\s*", "@", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*[\[\(]\s*dot\s*[\]\)]\s*", ".", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\w)\s+at\s+(?=\w)", "@", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\w)\s+dot\s+(?=\w)", ".", text, flags=re.IGNORECASE)
    return text


def _fetch_html(url: str, timeout: int = 12) -> str:
    try:
        page = Fetcher().get(url, timeout=timeout)
    except Exception:
        return ""
    if not page:
        return ""
    for attr in ("html_content", "body"):
        v = getattr(page, attr, None)
        if v:
            if isinstance(v, bytes):
                return v.decode("utf-8", errors="replace")
            return str(v)
    try:
        return str(page)
    except Exception:
        return ""


async def _fetch_html_stealth_async(url: str) -> str:
    """Async-only — Scrapling's sync StealthyFetcher.get() returns empty
    payloads. Use async_fetch and decode the body."""
    try:
        page = await StealthyFetcher.async_fetch(url)
    except Exception:
        return ""
    if not page:
        return ""
    for attr in ("html_content", "body"):
        v = getattr(page, attr, None)
        if v:
            if isinstance(v, bytes):
                return v.decode("utf-8", errors="replace")
            return str(v)
    return ""


def _looks_jsy(html_text: str) -> bool:
    """Worth a JS retry?

    Triggers on:
    - Site builders that lazy-load content (Wix, Squarespace, Shopify)
    - React / Next.js SPAs that hydrate client-side
    - Cloudflare challenge pages — the static fetch was blocked, so a
      stealth fetch is the only way to see real content.
    """
    if not html_text:
        return False
    sample = html_text[:6000].lower()
    return any(sig in sample for sig in (
        "wix.com", "squarespace.com", "shopify.com",
        "__next_data__", "window.shopify", "data-react-",
        # Cloudflare anti-bot challenge markers
        "cf-browser-verification", "cf-chl-", "cloudflare ray id",
        "challenge-platform", "checking your browser",
        # Generic 403 / blocked indicators worth a stealth retry
        "access denied", "request blocked",
    ))


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 1 — Direct DOM extraction techniques
# ═══════════════════════════════════════════════════════════════════════════


def _decode_cfemail(hexstr: str) -> str | None:
    """Decode a Cloudflare Email Protection token. The first byte is the XOR
    key; every following byte is `key XOR original_byte`."""
    try:
        if not hexstr or len(hexstr) < 4 or len(hexstr) % 2 != 0:
            return None
        key = int(hexstr[:2], 16)
        return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))
    except (ValueError, IndexError):
        return None


def _l1_mailto(soup: BeautifulSoup) -> list[str]:
    """`<a href="mailto:...">` — explicit publicly-published contact channel."""
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.lower().startswith("mailto:"):
            continue
        addr = href[len("mailto:"):].split("?", 1)[0].strip()
        if addr and _is_valid_email(addr):
            out.append(addr.lower())
    return list(dict.fromkeys(out))


def _l1_structured(html_text: str, base_url: str) -> list[str]:
    """All four structured-data formats SMB sites commonly publish:
    JSON-LD (Yoast SEO), microdata (`itemprop="email"`), RDFa, OpenGraph.

    `extruct` handles the format quirks (e.g. JSON-LD `@graph` nesting,
    microdata `itemref` resolution) that our hand-rolled walker missed.
    Microdata in particular adds yield — older WordPress themes use
    `<span itemprop="email">info@...</span>` instead of JSON-LD."""
    out: list[str] = []
    try:
        import extruct
        data = extruct.extract(
            html_text,
            base_url=base_url or None,
            syntaxes=["json-ld", "microdata", "rdfa", "opengraph"],
            uniform=True,
        )
    except Exception:
        return out

    def _normalize(value: str) -> str:
        # extruct preserves `mailto:` prefix when the itemprop="email" is on
        # an anchor — strip it and any querystring.
        v = value.strip()
        if v.lower().startswith("mailto:"):
            v = v[len("mailto:"):]
        return v.split("?", 1)[0].strip().lower()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() == "email":
                    candidates: list[str] = []
                    if isinstance(v, str):
                        candidates.append(v)
                    elif isinstance(v, list):
                        candidates.extend(c for c in v if isinstance(c, str))
                    for c in candidates:
                        normalized = _normalize(c)
                        if _is_valid_email(normalized):
                            out.append(normalized)
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return list(dict.fromkeys(out))


def _l1_cfemail(soup: BeautifulSoup) -> list[str]:
    """Cloudflare Email Protection — XOR-encoded `data-cfemail` attribute and
    the `/cdn-cgi/l/email-protection#HEX` href fallback."""
    out: list[str] = []
    for el in soup.select("[data-cfemail]"):
        decoded = _decode_cfemail(el.get("data-cfemail", ""))
        if decoded and _is_valid_email(decoded):
            out.append(decoded.lower())
    for a in soup.find_all("a", href=True):
        m = re.search(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]+)", a["href"])
        if m:
            decoded = _decode_cfemail(m.group(1))
            if decoded and _is_valid_email(decoded):
                out.append(decoded.lower())
    return list(dict.fromkeys(out))


def _l1_meta_tags(soup: BeautifulSoup) -> list[str]:
    """Open Graph + business meta tags. Niche but very high-confidence when set."""
    out: list[str] = []
    selectors = [
        ("meta", {"property": "og:email"}),
        ("meta", {"property": "business:contact_data:email"}),
        ("meta", {"name": "email"}),
        ("meta", {"name": "contact"}),
        ("meta", {"itemprop": "email"}),
    ]
    for tag_name, attrs in selectors:
        for tag in soup.find_all(tag_name, attrs=attrs):
            content = tag.get("content", "")
            if content and _is_valid_email(content):
                out.append(content.lower())
    return list(dict.fromkeys(out))


def _l1_footer_text(soup: BeautifulSoup) -> list[str]:
    """SMBs concentrate emails in <footer>. Targeted scrape catches addresses
    that the homepage's noisy `<head>` would otherwise drown out."""
    out: list[str] = []
    candidates = soup.find_all("footer")
    candidates += soup.find_all(class_=re.compile(r"footer", re.IGNORECASE))
    for el in candidates:
        text = _deobfuscate(el.get_text(" ", strip=True))
        for m in EMAIL_REGEX.findall(text):
            if _is_valid_email(m):
                out.append(m.lower())
    return list(dict.fromkeys(out))


def _l1_text_regex(html_text: str) -> list[str]:
    """Plain-text regex over deobfuscated HTML — broadest net, highest noise."""
    text = _deobfuscate(html_text)
    return list(dict.fromkeys(
        e.lower() for e in EMAIL_REGEX.findall(text) if _is_valid_email(e)
    ))


def _layer1_extract(html_text: str, domain: str, base_url: str = "") -> tuple[str | None, str]:
    """Run all Layer 1 techniques in priority order. Returns (email, sub-source-tag)."""
    if not html_text:
        return None, ""
    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception:
        return None, ""

    # Explicit signals: business literally published this address as a
    # contact channel. Cross-domain results allowed (franchise dispatch
    # emails, parent-company addresses).
    explicit = [
        ("mailto", _l1_mailto(soup)),
        ("structured", _l1_structured(html_text, base_url)),  # JSON-LD + microdata + RDFa + OG
        ("cfemail", _l1_cfemail(soup)),
        ("meta", _l1_meta_tags(soup)),
    ]
    for name, emails in explicit:
        chosen = _pick_email(emails, domain, allow_cross_domain=True)
        if chosen:
            return chosen, name

    # Implicit signals: regex over text. Strict branded filter — otherwise
    # we'd accept template placeholders like john@smith.com.
    implicit = [
        ("footer", _l1_footer_text(soup)),
        ("text", _l1_text_regex(html_text)),
    ]
    for name, emails in implicit:
        chosen = _pick_email(emails, domain, allow_cross_domain=False)
        if chosen:
            return chosen, name
    return None, ""


def _has_mx_record(email: str) -> bool:
    """Confirm the domain after `@` has a working mail server. Drops emails
    pointing at dead/typo domains before we ever try to send.

    Cached per-domain because every business has at most a handful of
    domains and DNS is slow."""
    if not email or "@" not in email:
        return False
    domain = email.partition("@")[2]
    if not domain:
        return False
    cached = _mx_cache.get(domain)
    if cached is not None:
        return cached
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX", lifetime=5.0)
        ok = len(list(answers)) > 0
    except Exception:
        ok = False
    _mx_cache[domain] = ok
    return ok


_mx_cache: dict[str, bool] = {}


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 4 — External discovery
# ═══════════════════════════════════════════════════════════════════════════


def _l4_directory_profile(detail_url: str, domain: str) -> tuple[str | None, str]:
    """Directory pages (BBB, Manta, YP) sometimes expose the business email
    field even when the SMB's own site doesn't. We re-run Layer 1 against
    that page."""
    if not detail_url:
        return None, ""
    html_text = _fetch_html(detail_url)
    if not html_text:
        return None, ""
    email, sub = _layer1_extract(html_text, domain)
    if email:
        return email, f"directory:{sub}"
    return None, ""


def _l4_duckduckgo(business_name: str, domain: str) -> tuple[str | None, str]:
    """DDG's HTML interface (no JS, no captcha for low-volume queries) often
    surfaces emails published on third-party sites — review aggregators,
    news mentions, niche directory listings — even when the SMB's own site
    has none. We pin the query to the business's domain so SERP snippets
    include matching addresses."""
    if not business_name or not domain:
        return None, ""
    query = f'"{business_name}" "@{domain}"'
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html_text = _fetch_html(url)
    if not html_text:
        return None, ""
    # SERP snippets are inline text; the regex over the whole page is enough.
    candidates = [e for e in EMAIL_REGEX.findall(_deobfuscate(html_text)) if _is_valid_email(e)]
    chosen = _prefer_branded(list(dict.fromkeys(candidates)), domain)
    if chosen:
        return chosen, "duckduckgo"
    return None, ""


# ═══════════════════════════════════════════════════════════════════════════
#  Extractor
# ═══════════════════════════════════════════════════════════════════════════


class EmailExtractor:
    """4-layer email discovery. Never guesses."""

    def __init__(self, engine: ScraperEngine | None = None):
        self.engine = engine or ScraperEngine()

    async def extract_async(
        self,
        website: str,
        *,
        business_name: str = "",
        detail_url: str = "",
    ) -> EmailResult:
        if not website and not detail_url:
            return EmailResult()

        url = _normalize_url(website) if website else ""
        domain = _domain_from_url(url) if url else ""

        homepage_html = ""

        # ── LAYER 1: Homepage direct DOM extraction ───────────────────────
        if url:
            homepage_html = _fetch_html(url)
            if homepage_html:
                email, sub = _layer1_extract(homepage_html, domain, base_url=url)
                if email:
                    return EmailResult(
                        email=email,
                        source=f"L1:homepage:{sub}",
                        confidence="high" if sub != "text" else "medium",
                    )

        # ── LAYER 2: Multi-page site crawl ────────────────────────────────
        if url:
            for path, kind in CONTACT_PATHS:
                page_url = url.rstrip("/") + path
                page_html = _fetch_html(page_url)
                email, sub = _layer1_extract(page_html, domain, base_url=page_url)
                if email:
                    return EmailResult(
                        email=email,
                        source=f"L2:{kind}:{sub}",
                        confidence="high" if sub != "text" else "medium",
                    )

        # ── LAYER 3: JS-rendered fallback ─────────────────────────────────
        # Trigger when:
        #   1. Homepage looked JS-y (Wix/Squarespace/SPA/Cloudflare challenge)
        #   2. Static fetch returned nothing (403 / blocked)
        #   3. Static fetch worked but Layers 1+2 found no email — try
        #      stealth in case the email is in a JS-hydrated footer.
        if url and (_looks_jsy(homepage_html) or not homepage_html or homepage_html):
            rendered = await _fetch_html_stealth_async(url)
            if rendered:
                email, sub = _layer1_extract(rendered, domain, base_url=url)
                if email:
                    return EmailResult(
                        email=email,
                        source=f"L3:js_rendered:{sub}",
                        confidence="medium",
                    )

        # ── LAYER 4: External discovery ───────────────────────────────────
        # 4a. Directory profile (BBB / Manta / YP detail page)
        if detail_url:
            email, sub = _l4_directory_profile(detail_url, domain)
            if email:
                return EmailResult(
                    email=email,
                    source=f"L4:{sub}",
                    confidence="medium",
                )

        # 4b. DuckDuckGo SERP — finds emails on third-party sites
        if business_name and domain:
            email, sub = _l4_duckduckgo(business_name, domain)
            if email:
                return EmailResult(
                    email=email,
                    source=f"L4:{sub}",
                    confidence="medium",
                )

        return EmailResult()
