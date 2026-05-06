"""Outreach: send a single email or a bulk batch using user settings + a template."""
from __future__ import annotations

import asyncio
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import settings_store, templates_store
from src.core.storage import update_lead

router = APIRouter(prefix="/api/outreach", tags=["outreach"])

# Stages we WILL advance to "contacted" on send. (Don't downgrade later stages.)
_ADVANCEABLE_STAGES = {"new", "researching", ""}

# Polite delay between bulk sends so SMTP providers (Gmail in particular)
# don't throttle the connection. 2s × 100 sends = ~3 minutes for a typical
# Workspace daily quota.
_BULK_DELAY_SECONDS = 2.0


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class OutreachSendRequest(BaseModel):
    opportunity_id: str
    opportunity_type: str  # "direct" or "cold"
    source_file: str
    raw_lead_id: str
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


class BulkRecipient(BaseModel):
    """One row in a bulk-send job."""
    opportunity_id: str
    opportunity_type: str
    source_file: str
    raw_lead_id: str
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


def _substitute(text: str, variables: dict[str, str]) -> str:
    out = text
    for key, value in variables.items():
        out = out.replace("{" + key + "}", str(value))
    return out


def _resolve_smtp() -> dict[str, Any]:
    """Pull SMTP config from settings; raise if not configured."""
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
    }


def _build_message(
    *, sender_name: str, from_email: str, to_name: str, to_email: str,
    subject: str, body_text: str,
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} <{from_email}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))
    return msg


def _advance_stage(
    *, opportunity_type: str, source_file: str, raw_lead_id: str,
    current_stage: str,
) -> bool:
    """Best-effort: advance lead to 'contacted' if not already past it."""
    if (current_stage or "").lower() not in _ADVANCEABLE_STAGES:
        return False
    section = "cold" if opportunity_type == "cold" else "direct"
    try:
        update_lead(
            source_file,
            raw_lead_id,
            {
                "Outreach_Status": "contacted",
                "Last_Contacted": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
            section,
        )
        return True
    except Exception as e:
        print(f"[OUTREACH] Stage advance failed: {e}", flush=True)
        return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/send", response_model=OutreachSendResponse)
async def send(req: OutreachSendRequest) -> OutreachSendResponse:
    try:
        smtp = _resolve_smtp()
    except HTTPException as e:
        return OutreachSendResponse(success=False, message=str(e.detail))

    # Resolve subject + body (custom > template).
    if req.custom_subject is not None and req.custom_body is not None:
        subject_raw = req.custom_subject
        body_raw = req.custom_body
    else:
        if not req.template_id:
            raise HTTPException(status_code=400, detail="template_id or custom_subject+custom_body required")
        template = templates_store.get_by_id(req.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        subject_raw = req.custom_subject or template["subject"]
        body_raw = req.custom_body or template["body"]

    variables = {"sender_name": smtp["sender_name"], **req.variables}
    subject = _substitute(subject_raw, variables)
    body_text = _substitute(body_raw, variables)

    msg = _build_message(
        sender_name=smtp["sender_name"], from_email=smtp["from_email"],
        to_name=req.to_name, to_email=req.to_email,
        subject=subject, body_text=body_text,
    )

    try:
        with smtplib.SMTP(smtp["host"], smtp["port"]) as server:
            server.starttls()
            server.login(smtp["user"], smtp["password"])
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return OutreachSendResponse(success=False, message="SMTP authentication failed. Check your credentials.")
    except smtplib.SMTPException as e:
        return OutreachSendResponse(success=False, message=f"SMTP error: {e}")
    except Exception as e:
        return OutreachSendResponse(success=False, message=f"Send failed: {e}")

    advanced = _advance_stage(
        opportunity_type=req.opportunity_type,
        source_file=req.source_file,
        raw_lead_id=req.raw_lead_id,
        current_stage=req.current_stage,
    )

    return OutreachSendResponse(
        success=True,
        message=f"Email sent to {req.to_email}",
        sent_at=datetime.utcnow(),
        stage_advanced=advanced,
    )


@router.post("/bulk_send", response_model=OutreachBulkSendResponse)
async def bulk_send(req: OutreachBulkSendRequest) -> OutreachBulkSendResponse:
    """Send the same template to many recipients over a single SMTP session.
    Skips recipients without an email. Throttles between sends to avoid
    provider-side rate limits."""
    smtp = _resolve_smtp()
    template = templates_store.get_by_id(req.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    results: list[BulkSendResult] = []
    sent = 0
    failed = 0

    # One SMTP login for the whole batch — much faster and friendlier to
    # providers than reconnecting per email.
    try:
        server = smtplib.SMTP(smtp["host"], smtp["port"])
        server.starttls()
        server.login(smtp["user"], smtp["password"])
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=400, detail="SMTP authentication failed. Check your credentials.")
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

            variables = {"sender_name": smtp["sender_name"], **r.variables}
            subject = _substitute(template["subject"], variables)
            body_text = _substitute(template["body"], variables)
            msg = _build_message(
                sender_name=smtp["sender_name"], from_email=smtp["from_email"],
                to_name=r.to_name or r.to_email, to_email=r.to_email,
                subject=subject, body_text=body_text,
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
                opportunity_type=r.opportunity_type,
                source_file=r.source_file,
                raw_lead_id=r.raw_lead_id,
                current_stage=r.current_stage,
            )
            results.append(BulkSendResult(
                opportunity_id=r.opportunity_id, to_email=r.to_email,
                success=True, message="Sent", stage_advanced=advanced,
            ))
            sent += 1

            # Polite delay between sends — but skip the wait after the last one.
            if idx < len(req.recipients) - 1 and req.delay_seconds > 0:
                await asyncio.sleep(req.delay_seconds)
    finally:
        try:
            server.quit()
        except Exception:
            pass

    return OutreachBulkSendResponse(sent=sent, failed=failed, results=results)
