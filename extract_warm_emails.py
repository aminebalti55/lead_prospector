"""
Quick email extraction script for WARM leads.
Run with: python extract_warm_emails.py
"""

import asyncio
import csv
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.scrapers.email_extractor import EmailExtractor


# WARM leads with websites
WARM_LEADS = [
    {
        "name": "Acosta Plumbing Service",
        "phone": "(305) 634-6676",
        "website": "acostaplumbing.com",
        "priority": 23,
    },
    {
        "name": "Douglas Orr Plumbing, Inc.",
        "phone": "(305) 887-1687",
        "website": "orrplumbing.com",
        "priority": 24,
    },
    {
        "name": "Bay Plumbing Co",
        "phone": "(305) 446-8141",
        "website": "bayplumbingco.com",
        "priority": 25,
    },
    {
        "name": "Main Plumbing Services",
        "phone": "(786) 269-3783",
        "website": "mainplumbingmiami.com",
        "priority": 26,
    },
    {
        "name": "EZ Miami Plumbing",
        "phone": "(305) 250-8557",
        "website": "ezmiamiplumbing.com",
        "priority": 27,
    },
    {
        "name": "Jehveh Plumbing Company",
        "phone": "(305) 714-0343",
        "website": "jehvehplumbers.com",
        "priority": 28,
    },
    {
        "name": "CSM Contractors",
        "phone": "(305) 323-5330",
        "website": "csmcontractors.com",
        "priority": 29,
    },
]


async def extract_emails():
    """Extract emails from WARM leads."""
    results = []

    async with EmailExtractor() as extractor:
        for lead in WARM_LEADS:
            print(f"\n[{lead['priority']}] {lead['name']}")
            print(f"    Website: {lead['website']}")

            # Add https if not present
            url = lead["website"]
            if not url.startswith("http"):
                url = f"https://{url}"

            try:
                result = await extractor.extract_email(
                    business_name=lead["name"], website_url=url
                )

                if result.email:
                    print(f"    Email: {result.email}")
                    print(f"    Source: {result.source}")
                    print(f"    Confidence: {result.confidence}")
                else:
                    print(f"    No email found")
                    if result.extraction_notes:
                        print(f"    Notes: {result.extraction_notes}")

                results.append(
                    {
                        "Priority": lead["priority"],
                        "Business_Name": lead["name"],
                        "Phone": lead["phone"],
                        "Website": lead["website"],
                        "Email": result.email or "",
                        "Email_Source": result.source or "",
                        "Email_Confidence": result.confidence or "",
                        "All_Emails_Found": ", ".join(result.all_emails_found)
                        if result.all_emails_found
                        else "",
                        "Notes": result.extraction_notes or "",
                    }
                )

            except Exception as e:
                print(f"    Error: {e}")
                results.append(
                    {
                        "Priority": lead["priority"],
                        "Business_Name": lead["name"],
                        "Phone": lead["phone"],
                        "Website": lead["website"],
                        "Email": "",
                        "Email_Source": "",
                        "Email_Confidence": "",
                        "All_Emails_Found": "",
                        "Notes": f"Error: {str(e)}",
                    }
                )

            # Rate limit
            await asyncio.sleep(1)

    return results


def save_results(results):
    """Save results to CSV."""
    output_path = Path("output") / "WARM_LEADS_WITH_EMAILS.csv"
    output_path.parent.mkdir(exist_ok=True)

    fieldnames = [
        "Priority",
        "Business_Name",
        "Phone",
        "Website",
        "Email",
        "Email_Source",
        "Email_Confidence",
        "All_Emails_Found",
        "Notes",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n\nResults saved to: {output_path}")
    return output_path


def main():
    print("=" * 60)
    print("WARM Lead Email Extraction")
    print("=" * 60)

    results = asyncio.run(extract_emails())
    output_path = save_results(results)

    # Summary
    found = sum(1 for r in results if r["Email"])
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: Found {found}/{len(results)} emails")
    print(f"{'=' * 60}")

    for r in results:
        status = f"[{r['Email']}]" if r["Email"] else "[No email]"
        print(f"  {r['Priority']}. {r['Business_Name']}: {status}")


if __name__ == "__main__":
    main()
