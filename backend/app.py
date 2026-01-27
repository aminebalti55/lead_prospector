from __future__ import annotations

# === CRITICAL FIX FOR PYTHON 3.13 ON WINDOWS ===
# Must be before ANY other imports that might touch asyncio
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ===============================================

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.excel_store import (
    list_output_excel_files,
    read_leads_from_excel,
    update_lead_in_excel,
)
from backend.models import (
    LeadUpdateRequest,
    LeadsResponse,
    OutputFileInfo,
    OutputFilesResponse,
    RunCreateRequest,
    RunCreateResponse,
    RunStatusResponse,
    DashboardStats,
    NicheBreakdown,
    SourceBreakdown,
    ScoreDistribution,
    EmailSendRequest,
    EmailSendResponse,
    EmailTemplate,
    EmailTemplatesResponse,
)
from backend.run_manager import RunManager


app = FastAPI(title="Lead Prospector API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

run_manager = RunManager()


# Email templates storage (in-memory for now)
EMAIL_TEMPLATES = [
    EmailTemplate(
        id="initial",
        name="Initial Outreach",
        subject="{business_name} - Quick question about your website",
        body="""Hi {business_name} team,

I came across {website} while researching {niche}s in {city} and noticed a few opportunities to get more calls from Google.

Specifically:
- Your site could rank higher for "{niche} near me" and "emergency {niche} {city}"
- A few quick fixes could improve load speed and mobile experience
- Your reviews deserve more visibility online

I help local {niche}s get more leads through website improvements and SEO.

Would a quick 10-minute call this week make sense?

Best,
{sender_name}""",
    ),
    EmailTemplate(
        id="followup",
        name="Follow-up",
        subject="Re: {business_name} - Quick question about your website",
        body="""Hi again,

Just floating this back up in case it got buried.

I noticed {business_name} could benefit from a few website tweaks — with some updates, you could turn more visitors into phone calls.

Happy to share 2-3 specific ideas for {website} — no strings attached.

Worth a quick chat?

{sender_name}""",
    ),
    EmailTemplate(
        id="final",
        name="Final Follow-up",
        subject="Closing the loop - {business_name}",
        body="""Hi {business_name} team,

I'll keep this short — I know you're busy.

If getting more calls from Google is on your radar, I'd love to help.

If not, no worries — I'll stop reaching out.

Best of luck,
{sender_name}""",
    ),
]


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True}


@app.get("/api/files", response_model=OutputFilesResponse)
async def list_files() -> OutputFilesResponse:
    files = [OutputFileInfo(**f) for f in list_output_excel_files()]
    return OutputFilesResponse(files=files)


@app.get("/api/files/{filename}/download")
async def download_file(filename: str):
    from src.config import OUTPUT_DIR

    safe_name = Path(filename).name
    path = OUTPUT_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=safe_name)


@app.get("/api/files/{filename}/leads", response_model=LeadsResponse)
async def get_leads(filename: str) -> LeadsResponse:
    try:
        columns, rows = read_leads_from_excel(filename)
        return LeadsResponse(file=Path(filename).name, columns=columns, rows=rows)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@app.patch("/api/files/{filename}/leads/{lead_id}")
async def update_lead(filename: str, lead_id: str, body: LeadUpdateRequest):
    try:
        update_lead_in_excel(filename, lead_id, body.model_dump())
        return {"ok": True}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/runs", response_model=RunCreateResponse)
async def create_run(body: RunCreateRequest) -> RunCreateResponse:
    state = await run_manager.create_run(body)
    return RunCreateResponse(
        run_id=state.run_id, status=state.status, created_at=state.created_at
    )


@app.get("/api/runs/{run_id}", response_model=RunStatusResponse)
async def get_run(run_id: str) -> RunStatusResponse:
    try:
        state = await run_manager.get_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunStatusResponse(
        run_id=state.run_id,
        status=state.status,
        created_at=state.created_at,
        started_at=state.started_at,
        finished_at=state.finished_at,
        params=state.params,
        output_files=state.output_files,
        error=state.error,
        progress=state.progress,
    )


@app.get("/api/stats", response_model=DashboardStats)
async def get_dashboard_stats() -> DashboardStats:
    """Get aggregated dashboard statistics from all Excel files."""
    files = list_output_excel_files()

    total_leads = 0
    total_emails = 0
    hot_leads = 0
    warm_leads = 0
    cold_leads = 0
    all_scores = []
    niche_counts = {}
    source_counts = {}
    score_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}

    for file_info in files[:10]:  # Limit to last 10 files for performance
        try:
            columns, rows = read_leads_from_excel(file_info["name"])

            for row in rows:
                total_leads += 1

                # Count emails
                email = row.get("Email") or row.get("email") or ""
                if email and "@" in str(email):
                    total_emails += 1

                # Count priorities
                priority = str(row.get("Priority", row.get("priority", "cold"))).lower()
                if priority == "hot":
                    hot_leads += 1
                elif priority == "warm":
                    warm_leads += 1
                else:
                    cold_leads += 1

                # Collect scores
                score = (
                    row.get("Score")
                    or row.get("total_score")
                    or row.get("Total_Score")
                    or 0
                )
                try:
                    score = float(score)
                    all_scores.append(score)

                    # Score distribution
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

                # Count by niche
                niche = str(row.get("Niche", row.get("niche", "unknown"))).lower()
                niche_counts[niche] = niche_counts.get(
                    niche, {"count": 0, "hot": 0, "warm": 0, "cold": 0}
                )
                niche_counts[niche]["count"] += 1
                if priority == "hot":
                    niche_counts[niche]["hot"] += 1
                elif priority == "warm":
                    niche_counts[niche]["warm"] += 1
                else:
                    niche_counts[niche]["cold"] += 1

                # Count by source
                source = str(row.get("Source", row.get("source", "scraped")))
                source_counts[source] = source_counts.get(source, 0) + 1

        except Exception:
            continue

    # Calculate average score
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

    # Build response
    leads_by_niche = [
        NicheBreakdown(
            niche=niche.title(),
            count=data["count"],
            hot=data["hot"],
            warm=data["warm"],
            cold=data["cold"],
        )
        for niche, data in niche_counts.items()
    ]

    leads_by_source = [
        SourceBreakdown(source=source, count=count)
        for source, count in source_counts.items()
    ]

    score_distribution = [
        ScoreDistribution(range=range_str, count=count)
        for range_str, count in score_buckets.items()
    ]

    # Get recent runs count
    runs = await run_manager.list_runs()
    recent_runs = len([r for r in runs if r.status == "completed"])

    # Conversion rate
    conversion_rate = (total_emails / total_leads * 100) if total_leads > 0 else 0.0

    return DashboardStats(
        total_files=len(files),
        total_leads=total_leads,
        total_emails=total_emails,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        avg_score=round(avg_score, 1),
        leads_by_niche=leads_by_niche,
        leads_by_source=leads_by_source,
        score_distribution=score_distribution,
        recent_runs=recent_runs,
        conversion_rate=round(conversion_rate, 1),
    )


@app.get("/api/email/templates", response_model=EmailTemplatesResponse)
async def get_email_templates() -> EmailTemplatesResponse:
    """Get available email templates."""
    return EmailTemplatesResponse(templates=EMAIL_TEMPLATES)


@app.post("/api/email/send", response_model=EmailSendResponse)
async def send_email(body: EmailSendRequest) -> EmailSendResponse:
    """
    Send an email using SMTP.

    Requires environment variables:
    - SMTP_HOST (default: smtp.gmail.com)
    - SMTP_PORT (default: 587)
    - SMTP_USER (your email)
    - SMTP_PASSWORD (app password for Gmail)
    - SENDER_NAME (your name)
    """
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
        # Create message
        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{smtp_user}>"
        msg["To"] = f"{body.to_name} <{body.to_email}>"
        msg["Subject"] = body.subject

        msg.attach(MIMEText(body.body, "plain"))

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        # Update lead status if lead_id provided
        # TODO: Update Excel with outreach status

        return EmailSendResponse(
            success=True,
            message=f"Email sent to {body.to_email}",
            sent_at=datetime.utcnow(),
        )

    except smtplib.SMTPAuthenticationError:
        return EmailSendResponse(
            success=False, message="SMTP authentication failed. Check your credentials."
        )
    except smtplib.SMTPException as e:
        return EmailSendResponse(success=False, message=f"SMTP error: {str(e)}")
    except Exception as e:
        return EmailSendResponse(
            success=False, message=f"Failed to send email: {str(e)}"
        )


@app.post("/api/email/preview")
async def preview_email(body: dict) -> dict:
    """Preview an email with template variables replaced."""
    template_id = body.get("template_id", "initial")
    variables = body.get("variables", {})

    template = next((t for t in EMAIL_TEMPLATES if t.id == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    subject = template.subject
    body_text = template.body

    # Replace variables
    for key, value in variables.items():
        placeholder = "{" + key + "}"
        subject = subject.replace(placeholder, str(value))
        body_text = body_text.replace(placeholder, str(value))

    return {"subject": subject, "body": body_text}


# Optional: serve built frontend if present (npm run build -> frontend/dist)
_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
