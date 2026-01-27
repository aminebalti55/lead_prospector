"""FastAPI backend for Lead Prospector web app."""

import sys
import os
import asyncio

# Fix for Windows: Playwright requires subprocess support which needs
# WindowsProactorEventLoopPolicy. This must be set before any async code runs.
#
# This fix is required because:
# 1. Playwright spawns browser processes using asyncio.create_subprocess_exec()
# 2. On Windows, the default SelectorEventLoop doesn't support subprocesses
# 3. We need ProactorEventLoop which has subprocess support
#
# Note: This runs when the backend module is imported (both in main process
# and in uvicorn reload worker processes)
if sys.platform == "win32":
    # Check if we're in a reloaded worker or main process
    if os.environ.get("LEAD_PROSPECTOR_WINDOWS_FIX") or True:
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass  # Policy may already be set
