"""Quick test for improved email extractor."""

import asyncio
import logging

# Enable debug logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from src.scrapers.email_extractor import EmailExtractor, PLAYWRIGHT_AVAILABLE


async def test_websites():
    """Test the email extractor on a few websites."""

    print("=" * 60)
    print("IMPROVED EMAIL EXTRACTOR TEST")
    print("=" * 60)
    print(f"Playwright available: {PLAYWRIGHT_AVAILABLE}")
    print()

    # Test websites - mix of easy and hard to scrape
    test_cases = [
        # Known working sites
        ("https://www.craigsplumbingla.com", "Craig's Plumbing"),
        ("https://www.papasplumbinginc.com", "Papa's Plumbing"),
        # Sites that might have JS or protection
        (
            "https://www.yelp.com/biz/roto-rooter-plumbing-and-water-cleanup-los-angeles",
            "Roto-Rooter (Yelp)",
        ),
    ]

    results = []

    async with EmailExtractor(timeout=20.0) as extractor:
        for url, name in test_cases:
            print(f"\nTesting: {name}")
            print(f"URL: {url}")
            print("-" * 40)

            result = await extractor.extract_email(
                website_url=url, business_name=name, city="Los Angeles", state="CA"
            )

            print(f"  Email: {result.email}")
            print(f"  Source: {result.source}")
            print(f"  Confidence: {result.confidence}")
            print(f"  Notes: {result.extraction_notes}")

            results.append(
                {
                    "name": name,
                    "email": result.email,
                    "source": result.source,
                    "confidence": result.confidence,
                }
            )

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    high_conf = [r for r in results if r["confidence"] == "high"]
    low_conf = [r for r in results if r["confidence"] == "low"]
    no_email = [r for r in results if r["email"] is None]

    print(f"Total tested: {len(results)}")
    print(f"High confidence emails: {len(high_conf)}")
    print(f"Low confidence (guessed): {len(low_conf)}")
    print(f"No email found: {len(no_email)}")

    if high_conf:
        print("\nHigh confidence emails found:")
        for r in high_conf:
            print(f"  - {r['name']}: {r['email']}")


if __name__ == "__main__":
    asyncio.run(test_websites())
