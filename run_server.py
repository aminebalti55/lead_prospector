#!/usr/bin/env python
"""
Lead Prospector Backend Server Runner

This script starts the FastAPI backend server with uvicorn.

The application uses undetected-chromedriver for browser automation,
which provides:
- Excellent anti-bot detection evasion
- Zero asyncio subprocess issues (uses WebDriver HTTP protocol)
- Automatic Chrome driver management

Usage:
    python run_server.py
    python run_server.py --port 8080
    python run_server.py --no-reload
"""

import sys
import os
import argparse

# Force unbuffered output for immediate logging
os.environ["PYTHONUNBUFFERED"] = "1"


def main():
    parser = argparse.ArgumentParser(description="Run Lead Prospector backend")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    import uvicorn

    print()
    print("=" * 60)
    print("  Lead Prospector Backend Server")
    print("=" * 60)
    print(f"  Platform:     {sys.platform}")
    print(f"  Python:       {sys.version.split()[0]}")
    print(f"  Host:         http://{args.host}:{args.port}")
    print(f"  API Docs:     http://localhost:{args.port}/docs")
    print(f"  Auto-reload:  {not args.no_reload}")
    print()
    print("  Browser:      undetected-chromedriver (anti-detection)")
    print("  Protocol:     WebDriver (HTTP) - no asyncio issues")
    print("=" * 60)
    print()

    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
