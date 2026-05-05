"""Outreach: send a single email using user settings + a template."""
from __future__ import annotations

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


class OutreachSendRequest(BaseModel):
    opportunity_id: str
    opportunity_type: str  # "direct" or "cold"
    source_file: str  # Excel filename — the storage layer uses this to find/write
    raw_lead_id: str  # Original Lead_ID in the Excel row
    current_stage: str  # Current stage of the opp (used to decide whether to advance)
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


def _substitute(text: str, variables: dict[str, str]) -> str:
    out = text
    for key, value in variables.items():
        out = out.replace("{" + key + "}", str(value))
    return out


@router.post("/send", response_model=OutreachSendResponse)
async def send(req: OutreachSendRequest) -> OutreachSendResponse:
    # 1. Get SMTP settings (raw — we need the real password)
    settings = settings_store.get_raw()
    email_cfg = settings.get("email", {})
    smtp_host = email_cfg.get("smtp_host") or "smtp.gmail.com"
    smtp_port = int(email_cfg.get("smtp_port") or 587)
    smtp_user = email_cfg.get("smtp_user") or ""
    smtp_password = email_cfg.get("smtp_password") or ""
    sender_name = email_cfg.get("sender_name") or "Lead Prospector"
    from_email = email_cfg.get("from_email") or smtp_user

    if not smtp_user or not smtp_password:
        return OutreachSendResponse(
            success=False,
            message="SMTP not configured — open Settings to set host, user, and password.",
        )

    # 2. Resolve subject + body (custom > template)
    if req.custom_subject is not None and req.custom_body is not None:
        subject = req.custom_subject
        body_text = req.custom_body
    else:
        if not req.template_id:
            raise HTTPException(status_code=400, detail="template_id or custom_subject+custom_body required")
        template = templates_store.get_by_id(req.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        subject = req.custom_subject or template["subject"]
        body_text = req.custom_body or template["body"]

    # 3. Substitute variables (caller-supplied + sender_name)
    variables = {"sender_name": sender_name, **req.variables}
    subject = _substitute(subject, variables)
    body_text = _substitute(body_text, variables)

    # 4. Send via SMTP
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{from_email}>"
        msg["To"] = f"{req.to_name} <{req.to_email}>"
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return OutreachSendResponse(success=False, message="SMTP authentication failed. Check your credentials.")
    except smtplib.SMTPException as e:
        return OutreachSendResponse(success=False, message=f"SMTP error: {e}")
    except Exception as e:
        return OutreachSendResponse(success=False, message=f"Send failed: {e}")

    # 5. Advance stage to "contacted" if not already past it
    advanced = False
    if (req.current_stage or "").lower() in _ADVANCEABLE_STAGES:
        section = "cold" if req.opportunity_type == "cold" else "direct"
        try:
            update_lead(
                req.source_file,
                req.raw_lead_id,
                {
                    "Outreach_Status": "contacted",
                    "Last_Contacted": datetime.now().strftime("%Y-%m-%d %H:%M"),
                },
                section,
            )
            advanced = True
        except Exception as e:
            # Send succeeded; stage update is best-effort.
            print(f"[OUTREACH] Stage advance failed: {e}", flush=True)

    return OutreachSendResponse(
        success=True,
        message=f"Email sent to {req.to_email}",
        sent_at=datetime.utcnow(),
        stage_advanced=advanced,
    )
