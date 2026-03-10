from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    locations: list[str] = Field(min_length=1, description="One or more locations")
    niches: list[Literal["plumbing", "dental", "pest_control"]] = Field(
        default_factory=lambda: ["plumbing", "dental", "pest_control"]
    )
    skip_audit: bool = False
    fetch_details: bool = True  # Enabled by default - needed to get websites from Google Maps
    fetch_emails: bool = False
    skip_scrapers: list[str] = Field(default_factory=list)
    output_format: Literal["xlsx", "csv", "both"] = "xlsx"
    max_results: int = Field(default=20, ge=1, le=100, description="Max results per scraper per location")


class RunCreateResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime


class ProgressStep(BaseModel):
    """Individual progress step for real-time updates."""
    step: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    message: str = ""
    count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RunProgress(BaseModel):
    """Detailed progress for a run."""
    current_phase: str = "Initializing"
    current_step: str = ""
    progress_percent: int = 0
    leads_found: int = 0
    emails_extracted: int = 0
    websites_audited: int = 0
    steps: List[ProgressStep] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)


class RunStatusResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    params: RunCreateRequest
    output_files: list[str] = Field(default_factory=list)
    error: Optional[str] = None
    progress: Optional[RunProgress] = None


class OutputFileInfo(BaseModel):
    name: str
    modified_at: datetime
    size_bytes: int


class OutputFilesResponse(BaseModel):
    files: list[OutputFileInfo]


class LeadsResponse(BaseModel):
    file: str
    columns: list[str]
    rows: list[dict[str, Any]]


class LeadUpdateRequest(BaseModel):
    Outreach_Status: Optional[str] = None
    Notes: Optional[str] = None
    Owner: Optional[str] = None
    Last_Contacted: Optional[str] = None
    Follow_Up_Date: Optional[str] = None


# Dashboard Stats Models
class LeadStats(BaseModel):
    total_leads: int = 0
    hot_leads: int = 0
    warm_leads: int = 0
    cold_leads: int = 0
    with_email: int = 0
    with_website: int = 0
    avg_score: float = 0.0


class NicheBreakdown(BaseModel):
    niche: str
    count: int
    hot: int
    warm: int
    cold: int


class SourceBreakdown(BaseModel):
    source: str
    count: int


class ScoreDistribution(BaseModel):
    range: str
    count: int


class DashboardStats(BaseModel):
    total_files: int = 0
    total_leads: int = 0
    total_emails: int = 0
    hot_leads: int = 0
    warm_leads: int = 0
    cold_leads: int = 0
    avg_score: float = 0.0
    leads_by_niche: List[NicheBreakdown] = Field(default_factory=list)
    leads_by_source: List[SourceBreakdown] = Field(default_factory=list)
    score_distribution: List[ScoreDistribution] = Field(default_factory=list)
    recent_runs: int = 0
    conversion_rate: float = 0.0  # leads with email / total leads


# Email Models
class EmailSendRequest(BaseModel):
    to_email: str
    to_name: str
    subject: str
    body: str
    lead_id: Optional[str] = None
    filename: Optional[str] = None  # Excel file to update


class EmailSendResponse(BaseModel):
    success: bool
    message: str
    sent_at: Optional[datetime] = None


class EmailTemplate(BaseModel):
    id: str
    name: str
    subject: str
    body: str


class EmailTemplatesResponse(BaseModel):
    templates: List[EmailTemplate]


# Batch Email Models
class BatchEmailRecipient(BaseModel):
    to_email: str
    to_name: str
    lead_id: Optional[str] = None
    variables: Dict[str, Any] = {}  # For template personalization


class BatchEmailRequest(BaseModel):
    template_id: str
    recipients: List[BatchEmailRecipient]
    custom_subject: Optional[str] = None  # Override template subject
    custom_body: Optional[str] = None  # Override template body
    delay_seconds: float = 2.0  # Delay between emails to avoid spam flags
    filename: Optional[str] = None  # Excel file to update after sending


class BatchEmailResult(BaseModel):
    to_email: str
    to_name: str
    success: bool
    message: str
    sent_at: Optional[datetime] = None


class BatchEmailResponse(BaseModel):
    total: int
    sent: int
    failed: int
    results: List[BatchEmailResult]
