"""IMAP reply detector — pause sequences when prospects reply.

Plan-10 outreach engine. Connects to the user's IMAP inbox, fetches
unseen messages, and for each one matches the sender's email against
opportunity contact_emails. On a match:
  1. Logs an `email_events` row with type='replied'
  2. Marks every active sequence_enrollment for that opportunity 'replied'
  3. Advances opportunity.stage to 'replied' (only if currently 'contacted')

Why IMAP and not webhooks: SMTP providers don't push reply notifications
universally. IMAP polling works on Gmail, Workspace, Outlook, Fastmail,
Zoho — anywhere the user already has email.

Marks messages \\Seen after processing so we don't double-count.
"""
from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import re
from datetime import datetime, timezone
from email.utils import parseaddr

from backend.services import settings_store
from backend.services.opportunities_store import update_stage as update_opp_stage
from backend.services.sequence_worker import mark_replied
from backend.services.supabase_client import get_client


logger = logging.getLogger(__name__)


_POLL_INTERVAL_SECONDS = 90


class ImapPoller:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("IMAP poller started")

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
                # IMAP is blocking — push to a thread.
                processed = await asyncio.to_thread(self._poll_once)
                if processed:
                    logger.info(f"IMAP poller processed {processed} reply(s)")
            except Exception as e:
                logger.error(f"IMAP poll error: {e}")
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    # -----------------------------------------------------------------

    def _poll_once(self) -> int:
        cfg = (settings_store.get_raw() or {}).get("email") or {}
        host = cfg.get("imap_host") or ""
        port = int(cfg.get("imap_port") or 993)
        user = cfg.get("imap_user") or cfg.get("smtp_user") or ""
        pw = cfg.get("imap_password") or cfg.get("smtp_password") or ""

        if not host or not user or not pw:
            return 0  # IMAP not configured — silent no-op

        try:
            conn = imaplib.IMAP4_SSL(host, port)
            conn.login(user, pw)
        except Exception as e:
            logger.warning(f"IMAP login failed: {e}")
            return 0

        try:
            conn.select("INBOX", readonly=False)
            # UNSEEN only — once we mark them \\Seen below they're skipped on
            # subsequent polls.
            typ, data = conn.search(None, "UNSEEN")
            if typ != "OK" or not data or not data[0]:
                return 0
            uids = data[0].split()
            if not uids:
                return 0

            # Build a lookup of contact_email → opportunity_id once per poll.
            email_to_opp = self._load_email_index()
            processed = 0

            for uid in uids:
                try:
                    typ, msg_data = conn.fetch(uid, "(RFC822)")
                    if typ != "OK" or not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    sender = parseaddr(msg.get("From") or "")[1].lower().strip()
                    subject = msg.get("Subject") or ""
                    if not sender:
                        continue

                    opp_id = email_to_opp.get(sender)
                    if not opp_id:
                        # Reply from someone we never emailed — leave UNSEEN
                        # so the user sees it normally.
                        continue

                    body_excerpt = self._extract_text(msg)[:500]
                    self._record_reply(
                        opp_id, sender, subject, body_excerpt, msg.get("Message-ID")
                    )
                    # Mark this UID seen so we don't reprocess.
                    conn.store(uid, "+FLAGS", "\\Seen")
                    processed += 1
                except Exception as e:
                    logger.warning(f"Failed processing UID {uid}: {e}")
                    continue
            return processed
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def _load_email_index(self) -> dict[str, str]:
        """Map every opportunity's lower-cased contact_email → its id."""
        resp = (
            get_client()
            .table("opportunities")
            .select("id, contact_email")
            .neq("contact_email", "")
            .execute()
        )
        out: dict[str, str] = {}
        for r in resp.data or []:
            email_addr = (r.get("contact_email") or "").lower().strip()
            if email_addr:
                out[email_addr] = r["id"]
        return out

    def _record_reply(
        self, opp_id: str, sender: str, subject: str,
        body_excerpt: str, message_id: str | None,
    ) -> None:
        client = get_client()

        # 1. Log the reply event.
        client.table("email_events").insert({
            "opportunity_id": opp_id,
            "event_type": "replied",
            "subject": subject,
            "to_email": sender,  # technically the sender now, but the column re-purposes cleanly
            "message_id": message_id,
            "body_excerpt": body_excerpt,
        }).execute()

        # 2. Pause any active sequence enrollments for this lead.
        paused = mark_replied(opp_id)
        logger.info(f"IMAP reply from {sender} → opp {opp_id} (paused {paused} enrollments)")

        # 3. Advance stage to 'replied' if currently 'contacted'/'researching'/'new'.
        opp_resp = (
            client.table("opportunities")
            .select("stage")
            .eq("id", opp_id)
            .limit(1)
            .execute()
        )
        opps = opp_resp.data or []
        if opps:
            current = (opps[0].get("stage") or "new").lower()
            if current in ("new", "researching", "contacted"):
                update_opp_stage(opp_id, "replied")

    @staticmethod
    def _extract_text(msg: email.message.Message) -> str:
        """Return the plain-text body of an email message — handles both
        single-part and multi-part MIME."""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            return payload.decode(
                                part.get_content_charset() or "utf-8",
                                errors="replace",
                            )
                    except Exception:
                        continue
            return ""
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(
                    msg.get_content_charset() or "utf-8",
                    errors="replace",
                )
        except Exception:
            pass
        return ""
