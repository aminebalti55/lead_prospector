"""Outreach send (single + bulk) — Supabase-backed.

Every send writes to the `email_events` table for tracking and updates the
opportunity's `stage` to 'contacted' (only when current stage permits).
Plan-10 features (sequences, IMAP reply detection, open/click tracking,
throttling, spam check) hook into this pipeline.
"""
from __future__ import annotations

import asyncio
import re
import secrets
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from backend.services import settings_store, templates_store
from backend.services.email_verifier import (
    is_safe_to_send,
    verify_and_store,
)
from backend.services.opportunities_store import update_stage as update_opp_stage
from backend.services.supabase_client import get_client
from backend.services.template_render import render as render_template


router = APIRouter(prefix="/api/outreach", tags=["outreach"])

# Stages from which we advance to "contacted" on send.
_ADVANCEABLE_STAGES = {"new", "researching", ""}
_BULK_DELAY_SECONDS = 2.0

# Spam-trigger words — flagged but not blocked. Build a coarser blocklist
# under settings later if it becomes a real problem.
_SPAM_TRIGGERS = (
    "free!!", "100% free", "act now", "guarantee", "limited time",
    "no risk", "risk-free", "no obligation", "click here", "best price",
    "winner", "earn $", "make money fast", "double your", "miracle",
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class OutreachSendRequest(BaseModel):
    opportunity_id: str
    opportunity_type: str  # "direct" | "cold"
    # Legacy compatibility — frontend sends them; we ignore source_file
    # / raw_lead_id since opportunity_id is the canonical key now.
    source_file: Optional[str] = None
    raw_lead_id: Optional[str] = None
    current_stage: str
    template_id: Optional[str] = None
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None
    to_email: str
    to_name: str
    variables: dict[str, str] = {}


class OutreachSendResponse(BaseModel):
    success: bool
    message: str
    sent_at: Optional[datetime] = None
    stage_advanced: bool = False
    spam_warnings: list[str] = []


class BulkRecipient(BaseModel):
    opportunity_id: str
    opportunity_type: str
    source_file: Optional[str] = None
    raw_lead_id: Optional[str] = None
    current_stage: str
    to_email: str
    to_name: str
    variables: dict[str, str] = {}


class OutreachBulkSendRequest(BaseModel):
    template_id: str
    recipients: list[BulkRecipient]
    delay_seconds: float = _BULK_DELAY_SECONDS


class BulkSendResult(BaseModel):
    opportunity_id: str
    to_email: str
    success: bool
    message: str
    stage_advanced: bool = False


class OutreachBulkSendResponse(BaseModel):
    sent: int
    failed: int
    results: list[BulkSendResult]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _substitute(text: str, variables: dict[str, str], *, seed: str | None = None) -> str:
    """Render with spintax + variables + fallbacks. `seed` pins the spintax
    choice per recipient so follow-ups stay consistent."""
    return render_template(text, variables, seed=seed)


def _gate_or_verify(opportunity_id: str, email: str) -> tuple[bool, str]:
    """Returns (allowed, status). Looks up the cached verification status
    in opportunities; if missing or stale, runs a fresh verify. Blocks the
    send when status is invalid / disposable / unknown.

    Order matters: we want to block bouncing addresses BEFORE we burn an
    SMTP connection on them — that's the entire point of the gate."""
    client = get_client()
    resp = (
        client.table("opportunities")
        .select("email_verification_status, email_verified_at")
        .eq("id", opportunity_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    cached = rows[0] if rows else {}

    from backend.services.email_verifier import needs_reverify
    if needs_reverify({**cached, "contact_email": email}):
        result = verify_and_store(opportunity_id, email)
        return is_safe_to_send(result.status), result.status

    status = cached.get("email_verification_status") or "unknown"
    return is_safe_to_send(status), status


def _resolve_smtp() -> dict[str, Any]:
    settings = settings_store.get_raw()
    email_cfg = settings.get("email", {})
    smtp_user = email_cfg.get("smtp_user") or ""
    smtp_password = email_cfg.get("smtp_password") or ""
    if not smtp_user or not smtp_password:
        raise HTTPException(
            status_code=400,
            detail="SMTP not configured — open Settings to set host, user, and password.",
        )
    return {
        "host": email_cfg.get("smtp_host") or "smtp.gmail.com",
        "port": int(email_cfg.get("smtp_port") or 587),
        "user": smtp_user,
        "password": smtp_password,
        "sender_name": email_cfg.get("sender_name") or "Lead Prospector",
        "from_email": email_cfg.get("from_email") or smtp_user,
        "daily_send_cap": int(email_cfg.get("daily_send_cap") or 30),
    }


def _spam_warnings(subject: str, body: str) -> list[str]:
    """Light-touch flag of spam-trigger phrases. Caller decides whether to
    block — we just surface them so the user can edit."""
    text = f"{subject}\n{body}".lower()
    return [w for w in _SPAM_TRIGGERS if w in text]


def _today_send_count() -> int:
    """How many `sent` events the system logged in the last 24h. Used by the
    daily-cap check before bulk sends."""
    cutoff = datetime.utcnow().replace(microsecond=0).isoformat()
    resp = (
        get_client()
        .table("email_events")
        .select("id", count="exact")
        .eq("event_type", "sent")
        .gte("occurred_at", _yesterday_iso())
        .execute()
    )
    return resp.count or 0


def _yesterday_iso() -> str:
    from datetime import timedelta
    return (datetime.utcnow() - timedelta(hours=24)).isoformat()


def _build_message(
    *, sender_name: str, from_email: str, to_name: str, to_email: str,
    subject: str, body_text: str, message_id: str,
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} <{from_email}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Subject"] = subject
    msg["Message-ID"] = message_id
    msg.attach(MIMEText(body_text, "plain"))
    return msg


def _wrap_with_tracking(
    body: str, *, tracking_token: str, base_url: str,
) -> str:
    """Inject open-tracking pixel + rewrite outbound URLs to /api/track/click.

    Pixel goes at the end (best deliverability — top-of-body pixels trip more
    spam filters). Click tracking rewrites http(s) URLs to /api/track/click
    with a base64-encoded `u` param so opens log per-recipient."""
    import base64

    def _rewrite(match: re.Match) -> str:
        original = match.group(0)
        encoded = base64.urlsafe_b64encode(original.encode()).decode().rstrip("=")
        return f"{base_url}/api/track/click?token={tracking_token}&u={encoded}"

    body_rewritten = re.sub(r"https?://[^\s)>\"']+", _rewrite, body)
    pixel = f"\n\n[image: {base_url}/api/track/open?token={tracking_token}]"
    return body_rewritten + pixel


def _advance_stage(*, opportunity_id: str, current_stage: str) -> bool:
    if (current_stage or "").lower() not in _ADVANCEABLE_STAGES:
        return False
    update_opp_stage(opportunity_id, "contacted", last_contacted=True)
    return True


def _log_event(
    *,
    opportunity_id: str,
    event_type: str,
    subject: str | None = None,
    to_email: str | None = None,
    message_id: str | None = None,
    tracking_token: str | None = None,
    body_excerpt: str | None = None,
    template_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    row = {
        "opportunity_id": opportunity_id,
        "event_type": event_type,
        "subject": subject,
        "to_email": to_email,
        "message_id": message_id,
        "tracking_token": tracking_token,
        "body_excerpt": (body_excerpt or "")[:500],
        "template_id": template_id,
        "metadata": metadata or {},
    }
    try:
        get_client().table("email_events").insert(row).execute()
    except Exception as e:
        print(f"[OUTREACH] event log failed: {e}", flush=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/send", response_model=OutreachSendResponse)
async def send(req: OutreachSendRequest, request: Request) -> OutreachSendResponse:
    try:
        smtp = _resolve_smtp()
    except HTTPException as e:
        return OutreachSendResponse(success=False, message=str(e.detail))

    # Resolve subject + body (custom > template).
    if req.custom_subject is not None and req.custom_body is not None:
        subject_raw = req.custom_subject
        body_raw = req.custom_body
        template_id_for_log = req.template_id
    else:
        if not req.template_id:
            raise HTTPException(status_code=400, detail="template_id or custom_subject+custom_body required")
        template = templates_store.get_by_id(req.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        subject_raw = req.custom_subject or template["subject"]
        body_raw = req.custom_body or template["body"]
        template_id_for_log = template["id"]

    variables = {"sender_name": smtp["sender_name"], **req.variables}
    # Pin spintax per opportunity so any follow-up rendered later picks the
    # same variant — recipients shouldn't see the greeting flip-flop.
    subject = _substitute(subject_raw, variables, seed=req.opportunity_id)
    body_text = _substitute(body_raw, variables, seed=req.opportunity_id)
    warnings = _spam_warnings(subject, body_text)

    # Verifier gate — block before we burn an SMTP connection on a bouncer.
    allowed, vstatus = _gate_or_verify(req.opportunity_id, req.to_email)
    if not allowed:
        return OutreachSendResponse(
            success=False,
            message=(
                f"Skipped — email verification status is '{vstatus}'. "
                "Sending would risk a bounce and damage sender reputation."
            ),
            spam_warnings=warnings,
        )

    base_url = str(request.base_url).rstrip("/")
    tracking_token = secrets.token_urlsafe(16)
    body_text_with_tracking = _wrap_with_tracking(
        body_text, tracking_token=tracking_token, base_url=base_url
    )

    message_id = f"<{uuid.uuid4()}@pulse>"

    msg = _build_message(
        sender_name=smtp["sender_name"], from_email=smtp["from_email"],
        to_name=req.to_name, to_email=req.to_email,
        subject=subject, body_text=body_text_with_tracking,
        message_id=message_id,
    )

    try:
        with smtplib.SMTP(smtp["host"], smtp["port"]) as server:
            server.starttls()
            server.login(smtp["user"], smtp["password"])
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return OutreachSendResponse(success=False, message="SMTP authentication failed.")
    except smtplib.SMTPException as e:
        return OutreachSendResponse(success=False, message=f"SMTP error: {e}", spam_warnings=warnings)
    except Exception as e:
        return OutreachSendResponse(success=False, message=f"Send failed: {e}", spam_warnings=warnings)

    advanced = _advance_stage(
        opportunity_id=req.opportunity_id, current_stage=req.current_stage,
    )

    _log_event(
        opportunity_id=req.opportunity_id,
        event_type="sent",
        subject=subject,
        to_email=req.to_email,
        message_id=message_id,
        tracking_token=tracking_token,
        body_excerpt=body_text,
        template_id=template_id_for_log,
        metadata={"warnings": warnings},
    )

    return OutreachSendResponse(
        success=True,
        message=f"Email sent to {req.to_email}",
        sent_at=datetime.utcnow(),
        stage_advanced=advanced,
        spam_warnings=warnings,
    )


@router.post("/bulk_send", response_model=OutreachBulkSendResponse)
async def bulk_send(req: OutreachBulkSendRequest, request: Request) -> OutreachBulkSendResponse:
    smtp = _resolve_smtp()
    template = templates_store.get_by_id(req.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Daily-cap guard. Counts `sent` events from the last 24h.
    daily_cap = smtp["daily_send_cap"]
    sent_today = _today_send_count()
    remaining = max(0, daily_cap - sent_today)

    base_url = str(request.base_url).rstrip("/")
    results: list[BulkSendResult] = []
    sent = 0
    failed = 0

    try:
        server = smtplib.SMTP(smtp["host"], smtp["port"])
        server.starttls()
        server.login(smtp["user"], smtp["password"])
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=400, detail="SMTP authentication failed.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP connection failed: {e}")

    try:
        for idx, r in enumerate(req.recipients):
            if not r.to_email or "@" not in r.to_email:
                results.append(BulkSendResult(
                    opportunity_id=r.opportunity_id, to_email=r.to_email or "",
                    success=False, message="No email address",
                ))
                failed += 1
                continue

            if sent >= remaining:
                results.append(BulkSendResult(
                    opportunity_id=r.opportunity_id, to_email=r.to_email,
                    success=False,
                    message=f"Daily cap reached ({daily_cap}/day). Try again tomorrow.",
                ))
                failed += 1
                continue

            allowed, vstatus = _gate_or_verify(r.opportunity_id, r.to_email)
            if not allowed:
                results.append(BulkSendResult(
                    opportunity_id=r.opportunity_id, to_email=r.to_email,
                    success=False,
                    message=f"Skipped — email is '{vstatus}' (would bounce).",
                ))
                failed += 1
                continue

            variables = {"sender_name": smtp["sender_name"], **r.variables}
            subject = _substitute(template["subject"], variables, seed=r.opportunity_id)
            body_text = _substitute(template["body"], variables, seed=r.opportunity_id)
            tracking_token = secrets.token_urlsafe(16)
            body_with_tracking = _wrap_with_tracking(
                body_text, tracking_token=tracking_token, base_url=base_url,
            )
            message_id = f"<{uuid.uuid4()}@pulse>"

            msg = _build_message(
                sender_name=smtp["sender_name"], from_email=smtp["from_email"],
                to_name=r.to_name or r.to_email, to_email=r.to_email,
                subject=subject, body_text=body_with_tracking,
                message_id=message_id,
            )

            try:
                server.send_message(msg)
            except Exception as e:
                results.append(BulkSendResult(
                    opportunity_id=r.opportunity_id, to_email=r.to_email,
                    success=False, message=f"Send failed: {e}",
                ))
                failed += 1
                continue

            advanced = _advance_stage(
                opportunity_id=r.opportunity_id, current_stage=r.current_stage,
            )
            _log_event(
                opportunity_id=r.opportunity_id,
                event_type="sent",
                subject=subject,
                to_email=r.to_email,
                message_id=message_id,
                tracking_token=tracking_token,
                body_excerpt=body_text,
                template_id=template["id"],
            )
            results.append(BulkSendResult(
                opportunity_id=r.opportunity_id, to_email=r.to_email,
                success=True, message="Sent", stage_advanced=advanced,
            ))
            sent += 1

            if idx < len(req.recipients) - 1 and req.delay_seconds > 0:
                await asyncio.sleep(req.delay_seconds)
    finally:
        try:
            server.quit()
        except Exception:
            pass

    return OutreachBulkSendResponse(sent=sent, failed=failed, results=results)


# ---------------------------------------------------------------------------
# Tracking endpoints — open pixel + click redirect
# ---------------------------------------------------------------------------


# 1×1 transparent GIF (43 bytes). Cheaper than a PNG for inbox image render.
_TRANSPARENT_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


@router.get("/track/open")
async def track_open(token: str):
    """Tracking pixel. Logs an `opened` event for the email matching token."""
    if token:
        await _record_event_by_token(token, "opened")
    return Response(content=_TRANSPARENT_GIF, media_type="image/gif")


@router.get("/track/click")
async def track_click(token: str, u: str):
    """Click redirect. Logs a `clicked` event then 302s to the original URL."""
    import base64
    target = ""
    try:
        # Restore base64 padding stripped at send-time.
        padded = u + "=" * (-len(u) % 4)
        target = base64.urlsafe_b64decode(padded.encode()).decode()
    except Exception:
        target = ""
    if not target.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid redirect target")

    if token:
        await _record_event_by_token(token, "clicked", link_url=target)
    return RedirectResponse(url=target, status_code=302)


async def _record_event_by_token(
    token: str, event_type: str, link_url: str | None = None
) -> None:
    """Find the original `sent` event by tracking_token, then log a derived
    open/click event tied to the same opportunity."""
    try:
        client = get_client()
        resp = (
            client.table("email_events")
            .select("opportunity_id, sequence_enrollment_id, template_id")
            .eq("tracking_token", token)
            .eq("event_type", "sent")
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return
        original = rows[0]
        client.table("email_events").insert({
            "opportunity_id": original["opportunity_id"],
            "sequence_enrollment_id": original.get("sequence_enrollment_id"),
            "template_id": original.get("template_id"),
            "event_type": event_type,
            "tracking_token": None,  # unique constraint — only `sent` rows hold the token
            "link_url": link_url,
        }).execute()
    except Exception as e:
        print(f"[OUTREACH] track {event_type} failed: {e}", flush=True)
