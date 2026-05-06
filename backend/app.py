from __future__ import annotations

# === CRITICAL FIX FOR PYTHON 3.13 ON WINDOWS ===
# Must be before ANY other imports that might touch asyncio
import sys
import os
import asyncio

# Force unbuffered output
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ===============================================

print("[APP] Backend module loading...", flush=True)

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import cold_outreach, direct_leads, hub, opportunities, outreach, settings as settings_router, shared, sources, templates
from backend.scheduler import Scheduler
from backend.services.imap_poller import ImapPoller
from backend.services.sequence_worker import SequenceWorker

app = FastAPI(title="Lead Prospector API", version="2.0.0")

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

app.include_router(cold_outreach.router)
app.include_router(direct_leads.router)
app.include_router(shared.router)
app.include_router(opportunities.router)
app.include_router(hub.router)
app.include_router(sources.router)
app.include_router(settings_router.router)
app.include_router(templates.router)
app.include_router(outreach.router)

from backend.routers import sequences as sequences_router
app.include_router(sequences_router.router)

scheduler = Scheduler()
sequence_worker = SequenceWorker()
imap_poller = ImapPoller()


@app.on_event("startup")
async def startup():
    await scheduler.start()
    await sequence_worker.start()
    await imap_poller.start()


@app.on_event("shutdown")
async def shutdown():
    await scheduler.stop()
    await sequence_worker.stop()
    await imap_poller.stop()


# Serve frontend if built
_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
