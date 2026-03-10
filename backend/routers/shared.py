"""Shared router — health, stats, email endpoints extracted from backend/app.py."""
from __future__ import annotations

import asyncio
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from fastapi import APIRouter, HTTPException

from src.core.storage import list_files, read_leads
from backend.models import (
    DashboardStats,
    NicheBreakdown,
    SourceBreakdown,
    ScoreDistribution,
    EmailSendRequest,
    EmailSendResponse,
    EmailTemplate,
    EmailTemplatesResponse,
    BatchEmailRequest,
    BatchEmailResponse,
    BatchEmailResult,
)

router = APIRouter(tags=["shared"])

# ── Email templates ───────────────────────────────────────────────────

EMAIL_TEMPLATES = [
    EmailTemplate(
        id="initial",
        name="Initial Outreach",
        subject="Quick idea for {business_name}",
        body=(
            "Hi there,\n\n"
            "I was doing some research on local businesses in {city} and came across {business_name}.\n\n"
            "Here's what I noticed: most customers today search online before making a decision. "
            "They look for reviews, compare options, and often choose whoever shows up first and looks the most professional.\n\n"
            "The challenge? Many great businesses like yours get overlooked \u2014 not because of the quality of your work, "
            "but because your online presence isn't working as hard as it could.\n\n"
            "I'm Amine, a software engineer who helps local businesses:\n"
            "\u2022 Rank higher on Google for searches like \"{niche} near me\"\n"
            "\u2022 Turn website visitors into actual phone calls\n"
            "\u2022 Build a modern online presence that builds trust instantly\n\n"
            "I'd love to share a few ideas specific to your business \u2014 no cost, no commitment.\n\n"
            "Worth a quick 10-minute chat this week?\n\n"
            "Best,\nAmine\n\n"
            "P.S. You can see some of my work here: https://aminebdev.vercel.app/"
        ),
    ),
    EmailTemplate(
        id="initial_with_review",
        name="Initial Outreach (with Insights)",
        subject="I took a look at {business_name}'s online presence",
        body=(
            "Hi there,\n\n"
            "I spent a few minutes looking at {business_name}'s online presence, and I wanted to share what I found.\n\n"
            "Here's the reality most business owners don't realize: when someone in {city} searches for a {niche}, "
            "they make a decision in seconds. Your website, your reviews, your Google listing \u2014 they all need to "
            "work together to say \"call us.\"\n\n"
            "What I noticed about your business:\n"
            "{website_review}\n\n"
            "These aren't criticisms \u2014 they're opportunities. Small improvements here could mean the difference "
            "between getting that call... or losing it to a competitor.\n\n"
            "I'm Amine, a software engineer who specializes in helping local businesses get more customers through:\n"
            "\u2022 Modern, fast websites that convert visitors into calls\n"
            "\u2022 SEO that puts you at the top of \"near me\" searches\n"
            "\u2022 Systems that help you manage leads and follow up automatically\n\n"
            "Would you be open to a quick call to discuss? No pitch, no pressure \u2014 just some ideas tailored "
            "to {business_name}.\n\n"
            "Best,\nAmine\n\nSee my work: https://aminebdev.vercel.app/"
        ),
    ),
    EmailTemplate(
        id="followup",
        name="Follow-up",
        subject="Following up - {business_name}",
        body=(
            "Hi again,\n\n"
            "Just wanted to float this back up in case it got buried under everything else.\n\n"
            "I know running a {niche} business keeps you busy \u2014 the last thing you need is another sales pitch. "
            "So I'll keep it simple:\n\n"
            "If you've ever wondered why competitors seem to get more calls even though your work is just as good "
            "(or better), it usually comes down to online presence.\n\n"
            "I help businesses like {business_name} fix that \u2014 quickly and affordably.\n\n"
            "Happy to share 2-3 specific ideas for your business. No strings attached.\n\n"
            "Worth a quick chat?\n\n"
            "Best,\nAmine\nhttps://aminebdev.vercel.app/"
        ),
    ),
    EmailTemplate(
        id="final",
        name="Final Follow-up",
        subject="Last note - {business_name}",
        body=(
            "Hi there,\n\n"
            "I'll keep this short \u2014 I know you're busy running your business.\n\n"
            "If getting more calls from Google is on your radar for this year, I'd genuinely love to help "
            "{business_name} get there.\n\n"
            "If the timing isn't right, no worries at all \u2014 I'll stop reaching out.\n\n"
            "Wishing you continued success either way.\n\n"
            "Best,\nAmine\nhttps://aminebdev.vercel.app/\n{sender_name}"
        ),
    ),
]


# ── Health ────────────────────────────────────────────────────────────

@router.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True}


# ── Stats ─────────────────────────────────────────────────────────────

def _compute_stats_for_section(section: str, file_list: list[dict]) -> dict:
    """Compute lead stats for a given file list."""
    total_leads = 0
    total_emails = 0
    hot_leads = 0
    warm_leads = 0
    cold_leads = 0
    all_scores: list[float] = []
    niche_counts: dict[str, dict] = {}
    source_counts: dict[str, int] = {}
    score_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}

    for file_info in file_list[:10]:
        try:
            columns, rows = read_leads(file_info["name"], section)
            for row in rows:
                total_leads += 1

                email = row.get("Email") or row.get("email") or ""
                if email and "@" in str(email):
                    total_emails += 1

                priority = str(row.get("Priority", row.get("priority", "cold"))).lower()
                if priority == "hot":
                    hot_leads += 1
                elif priority == "warm":
                    warm_leads += 1
                else:
                    cold_leads += 1

                score = row.get("Score") or row.get("total_score") or row.get("Total_Score") or 0
                try:
                    score = float(score)
                    all_scores.append(score)
                    if score <= 20:
                        score_buckets["0-20"] += 1
                    elif score <= 40:
                        score_buckets["21-40"] += 1
                    elif score <= 60:
                        score_buckets["41-60"] += 1
                    elif score <= 80:
                        score_buckets["61-80"] += 1
                    else:
                        score_buckets["81-100"] += 1
                except (ValueError, TypeError):
                    pass

                niche = str(row.get("Niche", row.get("niche", "unknown"))).lower()
                niche_counts.setdefault(niche, {"count": 0, "hot": 0, "warm": 0, "cold": 0})
                niche_counts[niche]["count"] += 1
                if priority == "hot":
                    niche_counts[niche]["hot"] += 1
                elif priority == "warm":
                    niche_counts[niche]["warm"] += 1
                else:
                    niche_counts[niche]["cold"] += 1

                source = str(row.get("Source", row.get("source", "scraped")))
                source_counts[source] = source_counts.get(source, 0) + 1
        except Exception:
            continue

    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    conversion_rate = (total_emails / total_leads * 100) if total_leads > 0 else 0.0

    return {
        "total_files": len(file_list),
        "total_leads": total_leads,
        "total_emails": total_emails,
        "hot_leads": hot_leads,
        "warm_leads": warm_leads,
        "cold_leads": cold_leads,
        "avg_score": round(avg_score, 1),
        "conversion_rate": round(conversion_rate, 1),
        "niche_counts": niche_counts,
        "source_counts": source_counts,
        "score_buckets": score_buckets,
    }


def _build_dashboard_stats(raw: dict, recent_runs: int = 0) -> DashboardStats:
    leads_by_niche = [
        NicheBreakdown(
            niche=niche.title(),
            count=data["count"],
            hot=data["hot"],
            warm=data["warm"],
            cold=data["cold"],
        )
        for niche, data in raw["niche_counts"].items()
    ]
    leads_by_source = [
        SourceBreakdown(source=source, count=count)
        for source, count in raw["source_counts"].items()
    ]
    score_distribution = [
        ScoreDistribution(range=r, count=c)
        for r, c in raw["score_buckets"].items()
    ]
    return DashboardStats(
        total_files=raw["total_files"],
        total_leads=raw["total_leads"],
        total_emails=raw["total_emails"],
        hot_leads=raw["hot_leads"],
        warm_leads=raw["warm_leads"],
        cold_leads=raw["cold_leads"],
        avg_score=raw["avg_score"],
        leads_by_niche=leads_by_niche,
        leads_by_source=leads_by_source,
        score_distribution=score_distribution,
        recent_runs=recent_runs,
        conversion_rate=raw["conversion_rate"],
    )


@router.get("/api/stats", response_model=DashboardStats)
async def get_dashboard_stats() -> DashboardStats:
    """Aggregate stats from both cold and direct pipelines."""
    cold_files = list_files("cold") + list_files("legacy")
    direct_files = list_files("direct")

    cold_raw = _compute_stats_for_section("cold", list_files("cold"))
    legacy_raw = _compute_stats_for_section("legacy", list_files("legacy"))
    direct_raw = _compute_stats_for_section("direct", direct_files)

    # Merge
    merged = {
        "total_files": cold_raw["total_files"] + legacy_raw["total_files"] + direct_raw["total_files"],
        "total_leads": cold_raw["total_leads"] + legacy_raw["total_leads"] + direct_raw["total_leads"],
        "total_emails": cold_raw["total_emails"] + legacy_raw["total_emails"] + direct_raw["total_emails"],
        "hot_leads": cold_raw["hot_leads"] + legacy_raw["hot_leads"] + direct_raw["hot_leads"],
        "warm_leads": cold_raw["warm_leads"] + legacy_raw["warm_leads"] + direct_raw["warm_leads"],
        "cold_leads": cold_raw["cold_leads"] + legacy_raw["cold_leads"] + direct_raw["cold_leads"],
        "avg_score": 0.0,
        "conversion_rate": 0.0,
        "niche_counts": {},
        "source_counts": {},
        "score_buckets": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
    }

    total = merged["total_leads"]
    if total > 0:
        # Weighted average score
        total_score_sum = (
            cold_raw["avg_score"] * cold_raw["total_leads"]
            + legacy_raw["avg_score"] * legacy_raw["total_leads"]
            + direct_raw["avg_score"] * direct_raw["total_leads"]
        )
        merged["avg_score"] = round(total_score_sum / total, 1) if total else 0.0
        merged["conversion_rate"] = round(merged["total_emails"] / total * 100, 1)

    for raw in [cold_raw, legacy_raw, direct_raw]:
        for niche, data in raw["niche_counts"].items():
            merged["niche_counts"].setdefault(niche, {"count": 0, "hot": 0, "warm": 0, "cold": 0})
            for key in ("count", "hot", "warm", "cold"):
                merged["niche_counts"][niche][key] += data[key]
        for source, count in raw["source_counts"].items():
            merged["source_counts"][source] = merged["source_counts"].get(source, 0) + count
        for bucket in merged["score_buckets"]:
            merged["score_buckets"][bucket] += raw["score_buckets"].get(bucket, 0)

    return _build_dashboard_stats(merged)


@router.get("/api/stats/cold", response_model=DashboardStats)
async def get_cold_stats() -> DashboardStats:
    cold_files = list_files("cold") + list_files("legacy")
    raw = _compute_stats_for_section("cold", list_files("cold"))
    legacy_raw = _compute_stats_for_section("legacy", list_files("legacy"))
    # Merge cold + legacy
    for key in ["total_files", "total_leads", "total_emails", "hot_leads", "warm_leads", "cold_leads"]:
        raw[key] += legacy_raw[key]
    if raw["total_leads"] > 0:
        raw["avg_score"] = round(
            (raw["avg_score"] * (raw["total_leads"] - legacy_raw["total_leads"])
             + legacy_raw["avg_score"] * legacy_raw["total_leads"])
            / raw["total_leads"], 1
        ) if raw["total_leads"] else 0.0
        raw["conversion_rate"] = round(raw["total_emails"] / raw["total_leads"] * 100, 1)
    for niche, data in legacy_raw["niche_counts"].items():
        raw["niche_counts"].setdefault(niche, {"count": 0, "hot": 0, "warm": 0, "cold": 0})
        for k in ("count", "hot", "warm", "cold"):
            raw["niche_counts"][niche][k] += data[k]
    for source, count in legacy_raw["source_counts"].items():
        raw["source_counts"][source] = raw["source_counts"].get(source, 0) + count
    for bucket in raw["score_buckets"]:
        raw["score_buckets"][bucket] += legacy_raw["score_buckets"].get(bucket, 0)
    return _build_dashboard_stats(raw)


@router.get("/api/stats/direct", response_model=DashboardStats)
async def get_direct_stats() -> DashboardStats:
    direct_files = list_files("direct")
    raw = _compute_stats_for_section("direct", direct_files)
    return _build_dashboard_stats(raw)


# ── Email endpoints ───────────────────────────────────────────────────

@router.get("/api/email/templates", response_model=EmailTemplatesResponse)
async def get_email_templates() -> EmailTemplatesResponse:
    return EmailTemplatesResponse(templates=EMAIL_TEMPLATES)


@router.post("/api/email/send", response_model=EmailSendResponse)
async def send_email(body: EmailSendRequest) -> EmailSendResponse:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_name = os.getenv("SENDER_NAME", "Lead Prospector")

    if not smtp_user or not smtp_password:
        return EmailSendResponse(
            success=False,
            message="Email not configured. Set SMTP_USER and SMTP_PASSWORD environment variables.",
        )

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{smtp_user}>"
        msg["To"] = f"{body.to_name} <{body.to_email}>"
        msg["Subject"] = body.subject
        msg.attach(MIMEText(body.body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        if body.lead_id and body.filename:
            try:
                from src.core.storage import update_lead as _update
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                _update(
                    body.filename, body.lead_id,
                    {"Outreach_Status": "Contacted", "Last_Contacted": now},
                    "cold",
                )
            except Exception as e:
                print(f"[EMAIL] Warning: Could not update Excel: {e}", flush=True)

        return EmailSendResponse(
            success=True,
            message=f"Email sent to {body.to_email}",
            sent_at=datetime.utcnow(),
        )
    except smtplib.SMTPAuthenticationError:
        return EmailSendResponse(success=False, message="SMTP authentication failed. Check your credentials.")
    except smtplib.SMTPException as e:
        return EmailSendResponse(success=False, message=f"SMTP error: {str(e)}")
    except Exception as e:
        return EmailSendResponse(success=False, message=f"Failed to send email: {str(e)}")


@router.post("/api/email/batch", response_model=BatchEmailResponse)
async def send_batch_emails(request: BatchEmailRequest) -> BatchEmailResponse:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_name = os.getenv("SENDER_NAME", "Lead Prospector")

    if not smtp_user or not smtp_password:
        return BatchEmailResponse(
            total=len(request.recipients),
            sent=0,
            failed=len(request.recipients),
            results=[
                BatchEmailResult(
                    to_email=r.to_email, to_name=r.to_name,
                    success=False, message="Email not configured",
                )
                for r in request.recipients
            ],
        )

    template = next((t for t in EMAIL_TEMPLATES if t.id == request.template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    results: list[BatchEmailResult] = []
    sent_count = 0
    failed_count = 0

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)

            for i, recipient in enumerate(request.recipients):
                try:
                    subject = request.custom_subject or template.subject
                    body_text = request.custom_body or template.body
                    variables = {"sender_name": sender_name, **recipient.variables}
                    for key, value in variables.items():
                        placeholder = "{" + key + "}"
                        subject = subject.replace(placeholder, str(value))
                        body_text = body_text.replace(placeholder, str(value))

                    msg = MIMEMultipart()
                    msg["From"] = f"{sender_name} <{smtp_user}>"
                    msg["To"] = f"{recipient.to_name} <{recipient.to_email}>"
                    msg["Subject"] = subject
                    msg.attach(MIMEText(body_text, "plain"))
                    server.send_message(msg)

                    if recipient.lead_id and request.filename:
                        try:
                            from src.core.storage import update_lead as _update
                            now = datetime.now().strftime("%Y-%m-%d %H:%M")
                            _update(
                                request.filename, recipient.lead_id,
                                {"Outreach_Status": "Contacted", "Last_Contacted": now},
                                "cold",
                            )
                        except Exception as e:
                            print(f"[BATCH] Warning: Excel update failed: {e}", flush=True)

                    results.append(BatchEmailResult(
                        to_email=recipient.to_email, to_name=recipient.to_name,
                        success=True, message="Sent successfully",
                        sent_at=datetime.utcnow(),
                    ))
                    sent_count += 1

                    if i < len(request.recipients) - 1:
                        await asyncio.sleep(request.delay_seconds)
                except Exception as e:
                    results.append(BatchEmailResult(
                        to_email=recipient.to_email, to_name=recipient.to_name,
                        success=False, message=str(e),
                    ))
                    failed_count += 1

    except smtplib.SMTPAuthenticationError:
        for recipient in request.recipients:
            if not any(r.to_email == recipient.to_email for r in results):
                results.append(BatchEmailResult(
                    to_email=recipient.to_email, to_name=recipient.to_name,
                    success=False, message="SMTP authentication failed",
                ))
                failed_count += 1
    except Exception as e:
        for recipient in request.recipients:
            if not any(r.to_email == recipient.to_email for r in results):
                results.append(BatchEmailResult(
                    to_email=recipient.to_email, to_name=recipient.to_name,
                    success=False, message=f"Connection error: {str(e)}",
                ))
                failed_count += 1

    return BatchEmailResponse(
        total=len(request.recipients),
        sent=sent_count,
        failed=failed_count,
        results=results,
    )


@router.post("/api/email/preview")
async def preview_email(body: dict) -> dict:
    template_id = body.get("template_id", "initial")
    variables = body.get("variables", {})

    template = next((t for t in EMAIL_TEMPLATES if t.id == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    subject = template.subject
    body_text = template.body
    for key, value in variables.items():
        placeholder = "{" + key + "}"
        subject = subject.replace(placeholder, str(value))
        body_text = body_text.replace(placeholder, str(value))

    return {"subject": subject, "body": body_text}
