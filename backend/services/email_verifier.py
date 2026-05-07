"""SMTP-handshake email verifier — gates sends to keep the bounce rate under 2%.

Four-stage check (Hunter.io's approach):
  1. SYNTAX  — RFC-shape regex
  2. DNS MX  — domain has at least one mail exchanger
  3. SMTP    — connect to the MX, EHLO, MAIL FROM, RCPT TO; observe code
  4. CATCH-ALL probe — RCPT a guaranteed-fake address; if it's accepted too,
                       the server accepts everything and the original RCPT
                       result is unreliable → mark `risky` not `valid`.

Returns one of:
  - valid       SMTP returned 250 for the address AND the catch-all probe
                returned ≥500. Highest-confidence result.
  - catch_all   The server accepts everything; we cannot tell whether this
                specific address is real. Better than 'invalid' but should
                send carefully (catch-alls bounce silently sometimes).
  - invalid     SMTP returned ≥500 for the address (mailbox doesn't exist).
                Do NOT send.
  - risky       SMTP returned a 4xx (greylist / temp fail) — try later.
  - unknown     Something went wrong (timeout, blocked port 25, MX refused).
                Default to "do not send" to be safe.
  - disposable  Domain is on a public throwaway list (10minutemail etc.).

Caches results per-address for 30 days; we don't re-verify a working email
on every send.

LIMITATIONS:
  - Most cloud hosts (Hetzner / DO / AWS) block outbound port 25 by default.
    On those hosts every check returns 'unknown'. The verifier still does
    syntax + MX, which catches the cheapest mistakes (typos, dead domains).
  - Gmail and Microsoft 365 are accept-then-bounce-silently providers —
    even a real RCPT-OK doesn't guarantee delivery. We mark them as
    'catch_all' to be conservative.
"""

from __future__ import annotations

import logging
import os
import re
import smtplib
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import dns.exception
import dns.resolver

from backend.services import settings_store
from backend.services.supabase_client import get_client


logger = logging.getLogger(__name__)


VerificationStatus = Literal[
    "valid", "invalid", "risky", "catch_all", "disposable", "unknown",
]

# Re-verify any address whose check is older than this. Bounces happen when
# mailboxes get suspended, domains expire, etc. — 30 days is the industry
# default revalidation window.
_REVERIFY_AFTER = timedelta(days=30)

_SYNTAX_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# Common "accept-then-bounce-silently" providers. RCPT-OK against these
# means almost nothing — we mark such addresses `catch_all` to make the
# downstream send code treat them carefully.
_ACCEPT_ALL_PROVIDERS = {
    "google.com", "googlemail.com",
    "outlook.com", "hotmail.com", "live.com", "office365.com", "outlook.office365.com",
    "icloud.com", "me.com", "mac.com",
    "yahoo.com", "ymail.com", "rocketmail.com",
    "proton.me", "protonmail.com",
}

# Throwaway / disposable domains — never useful for outreach.
_DISPOSABLE_DOMAINS = {
    "10minutemail.com", "guerrillamail.com", "mailinator.com",
    "tempmail.com", "throwawaymail.com", "yopmail.com",
    "trashmail.com", "fakeinbox.com", "getnada.com",
    "sharklasers.com", "maildrop.cc",
}


@dataclass
class VerifyResult:
    status: VerificationStatus
    reason: str = ""


def _split(email: str) -> tuple[str, str] | None:
    if "@" not in email:
        return None
    local, _, domain = email.partition("@")
    return local.strip().lower(), domain.strip().lower()


# ---------------------------------------------------------------------------
# DNS / MX
# ---------------------------------------------------------------------------


_mx_cache: dict[str, list[str]] = {}


def _mx_records(domain: str) -> list[str]:
    """Return MX hostnames sorted by priority. Empty list if no MX."""
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5.0)
        mxs = sorted(
            ((r.preference, str(r.exchange).rstrip(".")) for r in answers),
            key=lambda p: p[0],
        )
        result = [host for _, host in mxs]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers,
            dns.exception.Timeout):
        result = []
    except Exception as e:
        logger.debug(f"MX lookup failed for {domain}: {e}")
        result = []
    _mx_cache[domain] = result
    return result


# ---------------------------------------------------------------------------
# SMTP probe
# ---------------------------------------------------------------------------


def _probe_smtp(
    mx_host: str, *, helo_domain: str, mail_from: str, recipients: list[str],
    timeout: float = 8.0,
) -> dict[str, int]:
    """Open SMTP to `mx_host`, run HELO/MAIL FROM/RCPT TO for each recipient,
    return {recipient: smtp_code}. 0 means the connection itself failed."""
    out: dict[str, int] = {r: 0 for r in recipients}
    try:
        with smtplib.SMTP(mx_host, 25, timeout=timeout) as server:
            try:
                code, _ = server.ehlo(helo_domain)
            except smtplib.SMTPException:
                code, _ = server.helo(helo_domain)
            if code >= 400:
                return out
            code, _ = server.mail(mail_from)
            if code >= 400:
                return out
            for r in recipients:
                try:
                    code, _ = server.rcpt(r)
                except smtplib.SMTPException as e:
                    code = getattr(e, "smtp_code", 0) or 550
                out[r] = code
            try:
                server.quit()
            except Exception:
                pass
    except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError) as e:
        logger.debug(f"SMTP probe failed for {mx_host}: {e}")
    except smtplib.SMTPException as e:
        logger.debug(f"SMTP error for {mx_host}: {e}")
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify(email: str) -> VerifyResult:
    """Run the four-stage check synchronously. Safe to call from request
    handlers (it's <10s for the worst case)."""
    if not email:
        return VerifyResult("invalid", "empty")
    email = email.strip().lower()

    # Stage 1 — syntax
    if not _SYNTAX_RE.match(email):
        return VerifyResult("invalid", "syntax")
    parts = _split(email)
    if not parts:
        return VerifyResult("invalid", "no_at")
    local, domain = parts

    # Disposable
    if domain in _DISPOSABLE_DOMAINS:
        return VerifyResult("disposable", "throwaway_domain")

    # Stage 2 — MX
    mxs = _mx_records(domain)
    if not mxs:
        return VerifyResult("invalid", "no_mx")

    # Catch-all early-out for big consumer providers
    if domain in _ACCEPT_ALL_PROVIDERS:
        return VerifyResult("catch_all", "consumer_provider")

    # Stage 3 + 4 — SMTP RCPT for both real and probe addresses, same connection
    helo_domain = (settings_store.get_raw().get("email") or {}).get(
        "from_email", ""
    ) or "verify.local"
    helo_domain = helo_domain.split("@", 1)[-1] or "verify.local"
    mail_from = f"verify@{helo_domain}"

    fake_local = f"verify-{os.urandom(6).hex()}"
    probe = f"{fake_local}@{domain}"

    # Try each MX host in priority order — first one that responds wins.
    for mx in mxs[:3]:
        codes = _probe_smtp(
            mx, helo_domain=helo_domain, mail_from=mail_from,
            recipients=[email, probe],
        )
        real_code = codes.get(email, 0)
        probe_code = codes.get(probe, 0)
        if real_code == 0 and probe_code == 0:
            continue  # connection failed, try next MX

        # Catch-all: probe accepted → can't trust the real result.
        if 250 <= probe_code < 260:
            return VerifyResult("catch_all", "server_accepts_anything")

        if 250 <= real_code < 260 and probe_code >= 500:
            return VerifyResult("valid", f"smtp_{real_code}")

        if 400 <= real_code < 500:
            return VerifyResult("risky", f"smtp_{real_code}_temp_fail")

        if real_code >= 500:
            return VerifyResult("invalid", f"smtp_{real_code}_rejected")

    # All MX probes failed — likely outbound port 25 blocked or every MX
    # refused. Treat as unknown (do-not-send). Most cloud hosts hit this.
    return VerifyResult("unknown", "smtp_unreachable")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def needs_reverify(opp: dict) -> bool:
    """True if this opportunity has an email but no recent verification."""
    if not opp.get("contact_email"):
        return False
    if not opp.get("email_verification_status"):
        return True
    last = opp.get("email_verified_at")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return True
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_dt > _REVERIFY_AFTER


def verify_and_store(opp_id: str, email: str) -> VerifyResult:
    """Verify + write the result back to opportunities. Returns the result."""
    result = verify(email)
    try:
        get_client().table("opportunities").update({
            "email_verification_status": result.status,
            "email_verified_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", opp_id).execute()
    except Exception as e:
        logger.warning(f"Persist verify result failed for {opp_id}: {e}")
    return result


def is_safe_to_send(status: str | None) -> bool:
    """The send gate. Only `valid` and `catch_all` are allowed through.
    `unknown` defaults to NO — bouncing one address is worse than skipping."""
    return status in ("valid", "catch_all")


def verify_many(opp_ids: list[str]) -> dict[str, VerifyResult]:
    """Verify a batch of opportunities by id. Looks up emails in one query,
    writes results back in one upsert."""
    if not opp_ids:
        return {}
    client = get_client()
    resp = (
        client.table("opportunities")
        .select("id, contact_email, email_verification_status, email_verified_at")
        .in_("id", opp_ids)
        .execute()
    )
    rows = resp.data or []
    out: dict[str, VerifyResult] = {}
    updates: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for r in rows:
        if not needs_reverify(r):
            existing = r.get("email_verification_status") or "unknown"
            out[r["id"]] = VerifyResult(existing, "cached")
            continue
        result = verify(r.get("contact_email") or "")
        out[r["id"]] = result
        updates.append({
            "id": r["id"],
            "email_verification_status": result.status,
            "email_verified_at": now_iso,
        })
    # Update one at a time — upsert would require all NOT NULL columns and
    # postgrest doesn't have a true bulk-update primitive. Per-row updates
    # are fine for the worker volumes we ship at (max ~50 per batch).
    for u in updates:
        try:
            client.table("opportunities").update({
                "email_verification_status": u["email_verification_status"],
                "email_verified_at": u["email_verified_at"],
            }).eq("id", u["id"]).execute()
        except Exception as e:
            logger.warning(f"Verify persist failed for {u['id']}: {e}")
    return out
