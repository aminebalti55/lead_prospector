"""
Windows compatibility layer for Playwright scrapers.

On Windows, Playwright requires ProactorEventLoop for subprocess creation.
When running inside uvicorn/FastAPI, the event loop may not be compatible.

This module provides a solution by running Playwright's SYNC API in a 
dedicated thread pool. The sync API creates its own internal event loop,
avoiding conflicts with the main application's event loop.
"""

import asyncio
import sys
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional, List
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Global flag to track if we're on Windows
IS_WINDOWS = sys.platform == "win32"

# Thread pool for Playwright operations
_playwright_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def get_playwright_executor() -> ThreadPoolExecutor:
    """Get or create the shared thread pool for Playwright operations."""
    global _playwright_executor
    with _executor_lock:
        if _playwright_executor is None:
            # Use a small pool - Playwright is resource-intensive
            _playwright_executor = ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="playwright"
            )
            logger.info("Created Playwright ThreadPoolExecutor")
        return _playwright_executor


def shutdown_playwright_executor():
    """Shutdown the Playwright thread pool."""
    global _playwright_executor
    with _executor_lock:
        if _playwright_executor is not None:
            _playwright_executor.shutdown(wait=True, cancel_futures=False)
            _playwright_executor = None
            logger.info("Shutdown Playwright ThreadPoolExecutor")


class SyncPlaywrightWrapper:
    """
    Wrapper that runs Playwright's sync API in a thread pool.
    
    This avoids the asyncio event loop conflicts on Windows by using
    Playwright's sync API (which manages its own event loop internally).
    
    Usage:
        wrapper = SyncPlaywrightWrapper()
        await wrapper.start()
        
        results = await wrapper.run_scrape(scrape_function, url, params)
        
        await wrapper.stop()
    """
    
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._started = False
        self._lock = threading.Lock()
    
    async def start(self, headless: bool = True) -> None:
        """Start Playwright browser in thread pool."""
        if self._started:
            return
        
        def _init():
            from playwright.sync_api import sync_playwright
            import random
            
            USER_AGENTS = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
            
            pw = sync_playwright().start()
            browser = pw.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(USER_AGENTS),
                locale="en-US",
                timezone_id="America/New_York",
            )
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            return pw, browser, context
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        self._playwright, self._browser, self._context = await loop.run_in_executor(
            executor, _init
        )
        self._started = True
        logger.info("SyncPlaywrightWrapper started")
    
    async def stop(self) -> None:
        """Stop Playwright browser."""
        if not self._started:
            return
        
        def _cleanup():
            try:
                if self._context:
                    self._context.close()
                if self._browser:
                    self._browser.close()
                if self._playwright:
                    self._playwright.stop()
            except Exception as e:
                logger.debug(f"Error during cleanup: {e}")
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        await loop.run_in_executor(executor, _cleanup)
        
        self._context = None
        self._browser = None
        self._playwright = None
        self._started = False
        logger.info("SyncPlaywrightWrapper stopped")
    
    async def run_in_browser(self, func: Callable, *args, **kwargs) -> Any:
        """
        Run a function in the browser context.
        
        The function receives (context, *args, **kwargs) and runs in the thread pool.
        """
        if not self._started:
            raise RuntimeError("Browser not started. Call start() first.")
        
        def _run():
            return func(self._context, *args, **kwargs)
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        return await loop.run_in_executor(executor, _run)
    
    async def new_page_and_run(self, func: Callable, *args, **kwargs) -> Any:
        """
        Create a new page, run a function, and close the page.
        
        The function receives (page, *args, **kwargs) and runs in the thread pool.
        Returns the function's result.
        """
        if not self._started:
            raise RuntimeError("Browser not started. Call start() first.")
        
        def _run():
            page = self._context.new_page()
            try:
                return func(page, *args, **kwargs)
            finally:
                page.close()
        
        loop = asyncio.get_running_loop()
        executor = get_playwright_executor()
        
        return await loop.run_in_executor(executor, _run)


async def run_sync_playwright(func: Callable, headless: bool = True) -> Any:
    """
    Convenience function to run a one-off Playwright operation.
    
    The function receives (browser, context) as arguments.
    
    Example:
        async def my_scrape():
            def scrape(browser, context):
                page = context.new_page()
                page.goto("https://example.com")
                return page.title()
            
            return await run_sync_playwright(scrape)
    """
    def _run():
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)
                return func(browser, context)
            finally:
                browser.close()
    
    loop = asyncio.get_running_loop()
    executor = get_playwright_executor()
    
    return await loop.run_in_executor(executor, _run)


# Legacy compatibility - these functions delegate to the new implementation
def ensure_proactor_policy():
    """
    Ensure the Windows Proactor event loop policy is set.
    
    Note: With the sync API approach, this is less critical but still good practice.
    """
    if IS_WINDOWS:
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            logger.debug("Windows Proactor Event Loop Policy set")
        except Exception as e:
            logger.warning(f"Failed to set Proactor policy: {e}")


def check_subprocess_support() -> bool:
    """Check if the current event loop supports subprocess creation."""
    if not IS_WINDOWS:
        return True
    
    try:
        loop = asyncio.get_running_loop()
        return hasattr(loop, "_proactor")
    except RuntimeError:
        return False
