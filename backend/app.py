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

from backend.routers import cold_outreach, direct_leads, shared
from backend.scheduler import Scheduler

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

scheduler = Scheduler()


@app.on_event("startup")
async def startup():
    await scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    await scheduler.stop()


# Serve frontend if built
_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
