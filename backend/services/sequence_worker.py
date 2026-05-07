"""Sequence worker — fires due follow-up emails.

Plan-10 outreach engine. Watches `sequence_enrollments` rows where
status='active' and next_send_at <= now, looks up the matching
`sequence_steps` row, sends the email via the outreach send pipeline,
then advances `current_step` and recomputes the next `next_send_at` from
`delay_days` of the next step. When there are no more steps the
enrollment moves to status='completed'.

A reply (detected by `imap_poller`) flips status to 'replied' and
prevents further sends — exactly what we want.

Cadence semantics:
- step 0 fires immediately on enrollment (delay_days=0)
- subsequent steps fire `delay_days` days after the previous send
"""
from __future__ import annotations

import asyncio
import logging
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from backend.services import settings_store
from backend.services.email_verifier import is_safe_to_send, needs_reverify, verify_and_store
from backend.services.opportunities_store import update_stage as update_opp_stage
from backend.services.supabase_client import get_client
from backend.services.template_render import render as render_template


logger = logging.getLogger(__name__)


_POLL_INTERVAL_SECONDS = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Public API for routers
# ---------------------------------------------------------------------------


def enroll(opportunity_id: str, sequence_id: str) -> dict[str, Any] | None:
    """Add a lead to a sequence. Returns the enrollment row or None if the
    lead is already enrolled (ON CONFLICT DO NOTHING)."""
    client = get_client()
    payload = {
        "opportunity_id": opportunity_id,
        "sequence_id": sequence_id,
        "current_step": 0,
        "status": "active",
        "next_send_at": _iso(_now()),  # fire step 0 on the next worker tick
    }
    try:
        resp = client.table("sequence_enrollments").insert(payload).execute()
    except Exception as e:
        # Likely a uniqueness conflict — already enrolled.
        logger.info(f"enroll skipped (already enrolled?) — {e}")
        return None
    return (resp.data or [None])[0]


def pause(enrollment_id: str) -> None:
    get_client().table("sequence_enrollments").update(
        {"status": "paused"}
    ).eq("id", enrollment_id).execute()


def mark_replied(opportunity_id: str) -> int:
    """Called by the IMAP poller. Marks every active enrollment for this
    lead as 'replied'. Returns count of rows updated."""
    resp = (
        get_client()
        .table("sequence_enrollments")
        .update({"status": "replied"})
        .eq("opportunity_id", opportunity_id)
        .eq("status", "active")
        .execute()
    )
    return len(resp.data or [])


# ---------------------------------------------------------------------------
# Worker loop
# ---------------------------------------------------------------------------


class SequenceWorker:
    """Polls due enrollments and fires the next email. Run as a long-lived
    asyncio task alongside the FastAPI server."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Sequence worker started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._fire_due()
            except Exception as e:
                logger.error(f"Sequence worker error: {e}")
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    async def _fire_due(self) -> None:
        client = get_client()
        now_iso = _iso(_now())

        resp = (
            client.table("sequence_enrollments")
            .select(
                "id, opportunity_id, sequence_id, current_step, status, next_send_at"
            )
            .eq("status", "active")
            .lte("next_send_at", now_iso)
            .limit(50)
            .execute()
        )
        due = resp.data or []
        if not due:
            return

        logger.info(f"Sequence worker firing {len(due)} due enrollment(s)")
        for enroll in due:
            try:
                await self._fire_one(enroll)
            except Exception as e:
                logger.error(
                    f"Failed to fire enrollment {enroll['id']}: {e}", exc_info=True
                )

    async def _fire_one(self, enroll: dict[str, Any]) -> None:
        client = get_client()
        sequence_id = enroll["sequence_id"]
        step_index = enroll["current_step"]

        # Look up this step's template + the next step's delay (if any).
        step_resp = (
            client.table("sequence_steps")
            .select("id, step_index, delay_days, template_id, reuse_subject_thread")
            .eq("sequence_id", sequence_id)
            .order("step_index")
            .execute()
        )
        steps = step_resp.data or []
        current = next((s for s in steps if s["step_index"] == step_index), None)
        if not current:
            # No matching step — sequence is malformed or completed.
            client.table("sequence_enrollments").update({
                "status": "completed",
                "completed_at": _iso(_now()),
            }).eq("id", enroll["id"]).execute()
            return

        # Pull the lead so we can substitute variables + check stage.
        opp_resp = (
            client.table("opportunities")
            .select(
                "id, contact_email, contact_name, company_name, niche, "
                "city, source, location, stage, lead_subtype, "
                "email_verification_status, email_verified_at"
            )
            .eq("id", enroll["opportunity_id"])
            .limit(1)
            .execute()
        )
        opps = opp_resp.data or []
        if not opps:
            # Lead was deleted — kill the enrollment.
            client.table("sequence_enrollments").update({
                "status": "completed",
                "completed_at": _iso(_now()),
            }).eq("id", enroll["id"]).execute()
            return
        opp = opps[0]

        if not opp.get("contact_email"):
            logger.info(
                f"Skipping enrollment {enroll['id']} — opportunity has no email"
            )
            client.table("sequence_enrollments").update({
                "status": "paused",
            }).eq("id", enroll["id"]).execute()
            return

        # Verifier gate — refuse to send to addresses that would bounce.
        # Pause the enrollment so the user can fix the email then resume.
        if needs_reverify(opp):
            verify_and_store(opp["id"], opp["contact_email"])
            opp = (
                client.table("opportunities")
                .select("email_verification_status")
                .eq("id", opp["id"])
                .limit(1)
                .execute()
            ).data[0] | opp
        if not is_safe_to_send(opp.get("email_verification_status")):
            logger.info(
                f"Pausing enrollment {enroll['id']} — email status "
                f"{opp.get('email_verification_status')} (would bounce)"
            )
            client.table("sequence_enrollments").update({
                "status": "paused",
            }).eq("id", enroll["id"]).execute()
            return

        # Send.
        ok = await self._send_step(opp, current, enroll["id"])
        if not ok:
            # SMTP failure — leave enrollment active, retry next tick. Bounce
            # back-off would be the next polish pass.
            return

        # Advance to next step or complete.
        next_step = next((s for s in steps if s["step_index"] == step_index + 1), None)
        if next_step:
            next_send = _now() + timedelta(days=int(next_step["delay_days"]))
            client.table("sequence_enrollments").update({
                "current_step": step_index + 1,
                "next_send_at": _iso(next_send),
            }).eq("id", enroll["id"]).execute()
        else:
            client.table("sequence_enrollments").update({
                "status": "completed",
                "completed_at": _iso(_now()),
            }).eq("id", enroll["id"]).execute()

    async def _send_step(
        self, opp: dict[str, Any], step: dict[str, Any], enrollment_id: str
    ) -> bool:
        """Send a single sequence step. Returns True on SMTP success."""
        client = get_client()

        # Resolve template.
        tpl_resp = (
            client.table("templates")
            .select("id, subject, body")
            .eq("id", step["template_id"])
            .limit(1)
            .execute()
        )
        tpl_rows = tpl_resp.data or []
        if not tpl_rows:
            logger.warning(f"Step {step['id']} references missing template")
            return False
        template = tpl_rows[0]

        # SMTP config.
        try:
            settings = settings_store.get_raw()
        except Exception:
            return False
        email_cfg = settings.get("email") or {}
        smtp_user = email_cfg.get("smtp_user") or ""
        smtp_pw = email_cfg.get("smtp_password") or ""
        if not smtp_user or not smtp_pw:
            logger.warning("Sequence worker — SMTP not configured; skipping")
            return False

        sender_name = email_cfg.get("sender_name") or "Pulse"
        from_email = email_cfg.get("from_email") or smtp_user

        # Substitute variables.
        variables = {
            "sender_name": sender_name,
            "first_name": (opp.get("contact_name") or "").split(" ")[0] or "there",
            "company": opp.get("company_name") or "",
            "niche": opp.get("niche") or "your business",
            "city": opp.get("city") or opp.get("location") or "",
            "previous_subject": "",  # filled in if reuse_subject_thread
        }

        # If this step reuses the thread (Re: same subject), look up the
        # previous step's rendered subject from email_events.
        if step.get("reuse_subject_thread") and step["step_index"] > 0:
            prev_resp = (
                client.table("email_events")
                .select("subject")
                .eq("opportunity_id", opp["id"])
                .eq("event_type", "sent")
                .order("occurred_at", desc=True)
                .limit(1)
                .execute()
            )
            prev_rows = prev_resp.data or []
            if prev_rows:
                variables["previous_subject"] = prev_rows[0].get("subject") or ""

        # Pin spintax per-opportunity so a recipient gets the same greeting
        # variant on the initial send AND the follow-ups.
        subject = render_template(template["subject"], variables, seed=opp["id"])
        body = render_template(template["body"], variables, seed=opp["id"])

        message_id = f"<{uuid.uuid4()}@pulse>"
        tracking_token = secrets.token_urlsafe(16)

        # Wire-up the email.
        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{from_email}>"
        msg["To"] = f"{opp.get('contact_name') or opp['contact_email']} <{opp['contact_email']}>"
        msg["Subject"] = subject
        msg["Message-ID"] = message_id
        msg.attach(MIMEText(body, "plain"))

        smtp_host = email_cfg.get("smtp_host") or "smtp.gmail.com"
        smtp_port = int(email_cfg.get("smtp_port") or 587)

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pw)
                server.send_message(msg)
        except Exception as e:
            logger.error(f"Sequence step send failed: {e}")
            return False

        # Log the sent event.
        client.table("email_events").insert({
            "opportunity_id": opp["id"],
            "sequence_enrollment_id": enrollment_id,
            "template_id": template["id"],
            "step_index": step["step_index"],
            "event_type": "sent",
            "subject": subject,
            "to_email": opp["contact_email"],
            "message_id": message_id,
            "tracking_token": tracking_token,
            "body_excerpt": body[:500],
        }).execute()

        # Advance opportunity stage on the FIRST step only — follow-ups
        # don't change stage (lead is already 'contacted').
        if step["step_index"] == 0 and (opp.get("stage") or "new") in (
            "new", "researching", ""
        ):
            try:
                update_opp_stage(opp["id"], "contacted", last_contacted=True)
            except Exception:
                pass

        logger.info(
            f"Sequence step {step['step_index']} sent to {opp['contact_email']}"
        )
        return True

