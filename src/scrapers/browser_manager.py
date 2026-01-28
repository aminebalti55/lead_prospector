"""
Browser Manager for undetected-chromedriver.

Provides a shared browser pool and utilities for running Chrome
with anti-detection features. Uses WebDriver protocol (HTTP-based)
which has zero asyncio subprocess issues on Windows.
"""

import asyncio
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Optional, Callable, Any

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

logger = logging.getLogger(__name__)

# User agent rotation pool (modern browsers 2025/2026)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# Thread pool for browser operations
_browser_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def get_browser_executor() -> ThreadPoolExecutor:
    """Get or create the shared thread pool for browser operations."""
    global _browser_executor
    with _executor_lock:
        if _browser_executor is None:
            _browser_executor = ThreadPoolExecutor(
                max_workers=3,
                thread_name_prefix="browser"
            )
            logger.info("Created Browser ThreadPoolExecutor")
        return _browser_executor


def shutdown_browser_executor():
    """Shutdown the browser thread pool."""
    global _browser_executor
    with _executor_lock:
        if _browser_executor is not None:
            _browser_executor.shutdown(wait=True, cancel_futures=False)
            _browser_executor = None
            logger.info("Shutdown Browser ThreadPoolExecutor")


def create_chrome_options(headless: bool = True) -> uc.ChromeOptions:
    """Create Chrome options with anti-detection settings."""
    options = uc.ChromeOptions()
    
    if headless:
        options.add_argument("--headless=new")
    
    # Anti-detection arguments
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    
    # Stealth preferences
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    
    # Language settings
    options.add_argument("--lang=en-US")
    options.add_experimental_option("prefs", {
        "intl.accept_languages": "en-US,en",
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    })
    
    return options


def create_driver(headless: bool = True) -> uc.Chrome:
    """
    Create a new undetected Chrome driver instance.
    
    This uses undetected-chromedriver which automatically:
    - Patches Chrome to remove automation fingerprints
    - Evades Cloudflare, Google, and other bot detection
    - Downloads and manages chromedriver automatically
    """
    import sys
    print(f"[BROWSER] Creating Chrome driver (headless={headless})...", flush=True)
    sys.stdout.flush()
    logger.info(f"Creating Chrome driver (headless={headless})")
    
    options = create_chrome_options(headless)
    print("[BROWSER] Chrome options created", flush=True)
    
    try:
        print("[BROWSER] Launching undetected-chromedriver...", flush=True)
        driver = uc.Chrome(
            options=options,
            use_subprocess=True,  # Required for Windows
            version_main=None,    # Auto-detect Chrome version
        )
        print("[BROWSER] Chrome driver created successfully!", flush=True)
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)
        print("[BROWSER] Timeouts set", flush=True)
        
        # Execute stealth scripts
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            """
        })
        print("[BROWSER] Stealth scripts injected", flush=True)
        
        logger.info("Created new Chrome driver successfully")
        return driver
        
    except Exception as e:
        print(f"[BROWSER] ERROR creating Chrome driver: {e}", flush=True)
        logger.error(f"Failed to create Chrome driver: {e}")
        raise


class BrowserSession:
    """
    Managed browser session for scraping.
    
    Usage:
        async with BrowserSession() as session:
            results = await session.run(scrape_function, url)
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._driver: Optional[uc.Chrome] = None
        self._lock = threading.Lock()
    
    def _ensure_driver(self):
        """Create driver if not exists."""
        if self._driver is None:
            self._driver = create_driver(self.headless)
    
    def _quit_driver(self):
        """Quit driver if exists."""
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception as e:
                logger.debug(f"Error quitting driver: {e}")
            finally:
                self._driver = None
    
    async def __aenter__(self):
        """Async context manager entry - create driver in thread pool."""
        print("[SESSION] Starting browser session...", flush=True)
        logger.info("Starting browser session")
        loop = asyncio.get_running_loop()
        executor = get_browser_executor()
        await loop.run_in_executor(executor, self._ensure_driver)
        print("[SESSION] Browser session started!", flush=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - quit driver in thread pool."""
        print("[SESSION] Closing browser session...", flush=True)
        loop = asyncio.get_running_loop()
        executor = get_browser_executor()
        await loop.run_in_executor(executor, self._quit_driver)
        print("[SESSION] Browser session closed", flush=True)
    
    async def run(self, func: Callable, *args, **kwargs) -> Any:
        """
        Run a function with the browser driver.
        
        The function receives (driver, *args, **kwargs) and runs in thread pool.
        """
        print(f"[SESSION.RUN] Preparing to run function in thread pool...", flush=True)
        if self._driver is None:
            print("[SESSION.RUN] ERROR: Driver is None!", flush=True)
            raise RuntimeError("Browser not started. Use async context manager.")
        
        def _run():
            print(f"[SESSION.RUN] Inside thread pool, executing function...", flush=True)
            try:
                result = func(self._driver, *args, **kwargs)
                print(f"[SESSION.RUN] Function executed successfully in thread pool", flush=True)
                return result
            except Exception as e:
                print(f"[SESSION.RUN] ERROR in thread pool: {e}", flush=True)
                raise
        
        loop = asyncio.get_running_loop()
        executor = get_browser_executor()
        print(f"[SESSION.RUN] Submitting to executor...", flush=True)
        return await loop.run_in_executor(executor, _run)
    
    @property
    def driver(self) -> Optional[uc.Chrome]:
        """Get the underlying driver (for sync operations in thread pool)."""
        return self._driver


# Utility functions for common browser operations

def safe_get(driver: uc.Chrome, url: str, wait_time: float = 2.0) -> bool:
    """
    Safely navigate to a URL with random delay.
    
    Returns True if successful, False otherwise.
    """
    try:
        print(f"[SAFE_GET] Navigating to: {url}")
        driver.get(url)
        wait = random.uniform(wait_time * 0.5, wait_time * 1.5)
        print(f"[SAFE_GET] Page loaded, waiting {wait:.2f}s...")
        time.sleep(wait)
        print(f"[SAFE_GET] Navigation complete")
        return True
    except TimeoutException:
        print(f"[SAFE_GET] Timeout loading {url}")
        logger.warning(f"Timeout loading {url}")
        return False
    except Exception as e:
        print(f"[SAFE_GET] Error loading {url}: {e}")
        return False
    except WebDriverException as e:
        logger.warning(f"Error loading {url}: {e}")
        return False


def safe_find_element(driver: uc.Chrome, by: By, value: str, timeout: int = 10):
    """Find element with explicit wait, returns None if not found."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        return None


def safe_find_elements(driver: uc.Chrome, by: By, value: str, timeout: int = 10) -> list:
    """Find elements with explicit wait, returns empty list if none found."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return driver.find_elements(by, value)
    except (TimeoutException, NoSuchElementException):
        return []


def safe_click(element, delay: float = 0.5) -> bool:
    """Safely click an element with delay."""
    try:
        element.click()
        time.sleep(delay)
        return True
    except (StaleElementReferenceException, WebDriverException) as e:
        logger.debug(f"Click failed: {e}")
        return False


def scroll_page(driver: uc.Chrome, scroll_pause: float = 1.0, max_scrolls: int = 10):
    """Scroll page to load dynamic content."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause + random.uniform(0, 0.5))
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def scroll_element(driver: uc.Chrome, element, scroll_pause: float = 1.0, max_scrolls: int = 10):
    """Scroll within a specific element (e.g., Google Maps results panel)."""
    for i in range(max_scrolls):
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight", 
            element
        )
        time.sleep(scroll_pause + random.uniform(0, 0.5))


def get_text_safe(element) -> str:
    """Safely get text from element."""
    try:
        return element.text.strip() if element else ""
    except StaleElementReferenceException:
        return ""


def get_attribute_safe(element, attr: str) -> Optional[str]:
    """Safely get attribute from element."""
    try:
        return element.get_attribute(attr) if element else None
    except StaleElementReferenceException:
        return None
