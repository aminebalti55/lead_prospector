"""Quick test to check if Yelp scraping works."""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


async def test_yelp():
    from playwright.async_api import async_playwright

    print("Starting Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Navigating to Yelp...")
        url = "https://www.yelp.com/search?find_desc=plumber&find_loc=Miami%2C+FL"
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        print("Waiting for content...")
        await asyncio.sleep(5)

        # Check page title
        title = await page.title()
        print(f"Title: {title}")

        # Check for main element
        main = await page.query_selector("main")
        print(f"Main element found: {main is not None}")

        # Check for listings
        listings = await page.query_selector_all('li:has(a[href*="/biz/"])')
        print(f"Listings found (strategy 1): {len(listings)}")

        # Try alternative selectors
        listings2 = await page.query_selector_all('div:has(h3 a[href*="/biz/"])')
        print(f"Listings found (strategy 2): {len(listings2)}")

        listings3 = await page.query_selector_all('a[href*="/biz/"]')
        print(f"Biz links found: {len(listings3)}")

        # Get page text length
        text = await page.inner_text("body")
        print(f"Body text length: {len(text)}")

        # Check for captcha/verification
        if "device verification" in text.lower() or "captcha" in text.lower():
            print("WARNING: Captcha/verification detected!")

        # Print first 500 chars of body text
        print(f"\nFirst 500 chars of body:\n{text[:500]}\n")

        await browser.close()
        print("Test complete!")


if __name__ == "__main__":
    asyncio.run(test_yelp())
