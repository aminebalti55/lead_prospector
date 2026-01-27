"""
Export Module
Exports lead data to CSV and Excel formats.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import OUTPUT_DIR
from src.utils.lead_id import compute_lead_id

logger = logging.getLogger(__name__)


class LeadExporter:
    """Exports processed leads to various formats."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(exist_ok=True)

    def export(
        self,
        leads: list,
        filename: str = "lead_prospects",
        format: str = "both",  # csv, xlsx, or both
    ) -> list[Path]:
        """
        Export leads to file(s).

        Args:
            leads: List of ProcessedLead objects
            filename: Base filename (without extension)
            format: Output format - csv, xlsx, or both

        Returns:
            List of output file paths
        """
        if not leads:
            logger.warning("No leads to export")
            return []

        # Convert to DataFrame
        df = self._leads_to_dataframe(leads)

        # Sort by priority and score
        priority_order = {"HOT": 0, "WARM": 1, "COLD": 2}
        df["_priority_order"] = df["Priority"].map(lambda x: priority_order.get(x, 3))
        df = df.sort_values(["_priority_order", "Score"], ascending=[True, False])
        df = df.drop("_priority_order", axis=1)

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        output_files = []

        if format in ("csv", "both"):
            csv_path = self._export_csv(df, filename, timestamp)
            output_files.append(csv_path)

        if format in ("xlsx", "both"):
            xlsx_path = self._export_xlsx(df, filename, timestamp)
            output_files.append(xlsx_path)

        return output_files

    def _leads_to_dataframe(self, leads: list) -> pd.DataFrame:
        """Convert leads to pandas DataFrame."""
        records = []

        for lead in leads:
            lead_id = compute_lead_id(
                business_name=lead.name,
                address=lead.address,
                phone=lead.phone,
                website=lead.website,
            )
            record = {
                # Stable row identifier (used by the web app to update Excel rows)
                "Lead_ID": lead_id,
                # Priority columns first
                "Priority": lead.priority.upper(),
                "Score": lead.total_score,
                "Recommended_Offer": lead.recommended_offer.replace("_", " ").title(),
                # Business info
                "Business_Name": lead.name,
                "Niche": lead.niche.replace("_", " ").title(),
                "Address": lead.address,
                "City": lead.city,
                "State": lead.state,
                "Phone": lead.phone,
                "Website": lead.website,
                # Email info
                "Email": getattr(lead, "email", "") or "",
                "Email_Source": getattr(lead, "email_source", "") or "",
                "Email_Confidence": getattr(lead, "email_confidence", "") or "",
                # Pain signals
                "Pain_Tags": lead.pain_tags_str,
                "Offer_Reasoning": lead.offer_reasoning,
                # Ratings
                "Google_Rating": lead.google_rating,
                "Google_Reviews": lead.google_review_count,
                "Yelp_Rating": lead.yelp_rating,
                "Yelp_Reviews": lead.yelp_review_count,
                # Website audit
                "Has_SSL": "Yes" if lead.has_ssl else "No",
                "Has_Booking_CTA": "Yes" if lead.has_booking_cta else "No",
                "Has_Contact_Form": "Yes" if lead.has_contact_form else "No",
                "Mobile_Friendly": "Yes" if lead.is_mobile_friendly else "No",
                "Page_Load_ms": lead.page_load_time_ms,
                # Review insights
                "Ops_Pain_Mentions": lead.ops_pain_count,
                "Conversion_Pain_Mentions": lead.conversion_pain_count,
                "Negative_Reviews": lead.negative_review_count,
                # Score breakdown
                "Website_Score": lead.website_score,
                "Conversion_Score": lead.conversion_score,
                "Ops_Score": lead.ops_score,
                "Reputation_Score": lead.reputation_score,
                # Source info
                "Source": lead.source,
                "Yelp_URL": lead.yelp_url,
                "Google_Place_ID": lead.google_place_id,
                "Yelp_ID": lead.yelp_id,
                # User-managed columns (treated as "DB fields" in the web app)
                "Outreach_Status": getattr(lead, "outreach_status", "") or "",
                "Notes": getattr(lead, "notes", "") or "",
                "Owner": getattr(lead, "owner", "") or "",
                "Last_Contacted": getattr(lead, "last_contacted", "") or "",
                "Follow_Up_Date": getattr(lead, "follow_up_date", "") or "",
            }
            records.append(record)

        return pd.DataFrame(records)

    def _export_csv(self, df: pd.DataFrame, filename: str, timestamp: str) -> Path:
        """Export to CSV format."""
        output_path = self.output_dir / f"{filename}_{timestamp}.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(f"Exported {len(df)} leads to CSV: {output_path}")
        return output_path

    def _export_xlsx(self, df: pd.DataFrame, filename: str, timestamp: str) -> Path:
        """Export to Excel format with formatting."""
        output_path = self.output_dir / f"{filename}_{timestamp}.xlsx"

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name="Leads", index=False)

            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets["Leads"]

            # Auto-adjust column widths
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).map(len).max(), len(col))
                # Cap width at 50
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[
                    chr(65 + idx) if idx < 26 else f"A{chr(65 + idx - 26)}"
                ].width = adjusted_width

            # Add summary sheet
            self._add_summary_sheet(df, writer)

            # Add hot leads sheet
            hot_leads = df[df["Priority"] == "HOT"]
            if not hot_leads.empty:
                hot_leads.to_excel(writer, sheet_name="Hot Leads", index=False)

        logger.info(f"Exported {len(df)} leads to Excel: {output_path}")
        return output_path

    def _add_summary_sheet(self, df: pd.DataFrame, writer: pd.ExcelWriter):
        """Add a summary statistics sheet."""
        summary_data = {
            "Metric": [
                "Total Leads",
                "Hot Leads",
                "Warm Leads",
                "Cold Leads",
                "",
                "By Niche:",
            ],
            "Value": [
                len(df),
                len(df[df["Priority"] == "HOT"]),
                len(df[df["Priority"] == "WARM"]),
                len(df[df["Priority"] == "COLD"]),
                "",
                "",
            ],
        }

        # Add niche breakdown
        for niche in df["Niche"].unique():
            count = len(df[df["Niche"] == niche])
            summary_data["Metric"].append(f"  - {niche}")
            summary_data["Value"].append(count)

        summary_data["Metric"].append("")
        summary_data["Value"].append("")
        summary_data["Metric"].append("By Recommended Offer:")
        summary_data["Value"].append("")

        # Add offer breakdown
        for offer in df["Recommended_Offer"].unique():
            count = len(df[df["Recommended_Offer"] == offer])
            summary_data["Metric"].append(f"  - {offer}")
            summary_data["Value"].append(count)

        summary_data["Metric"].append("")
        summary_data["Value"].append("")
        summary_data["Metric"].append("Top Pain Tags:")
        summary_data["Value"].append("")

        # Count pain tags
        all_tags = []
        for tags in df["Pain_Tags"].dropna():
            all_tags.extend([t.strip() for t in tags.split(",")])

        from collections import Counter

        tag_counts = Counter(all_tags)
        for tag, count in tag_counts.most_common(10):
            if tag:
                summary_data["Metric"].append(f"  - {tag}")
                summary_data["Value"].append(count)

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)


def export_leads(
    leads: list, filename: str = "lead_prospects", format: str = "both"
) -> list[Path]:
    """Convenience function to export leads."""
    exporter = LeadExporter()
    return exporter.export(leads, filename, format)
