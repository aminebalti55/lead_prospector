#!/usr/bin/env python
"""
Lead Prospector Backend Server Runner

This script starts the FastAPI backend server with uvicorn.

The application uses sync Playwright API in a dedicated thread pool to avoid
asyncio event loop compatibility issues on Windows. This approach works
regardless of which event loop policy uvicorn uses.

Usage:
    python run_server.py
    python run_server.py --port 8080
    python run_server.py --no-reload
"""

import sys
import argparse


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
    print("  NOTE: Playwright runs via sync API in a thread pool")
    print("        This avoids Windows asyncio subprocess issues")
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
