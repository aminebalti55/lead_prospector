"""Tests for the DirectLeadsPipeline class."""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from src.core.models import DirectLead
from src.direct_leads.pipeline import DirectLeadsPipeline


@pytest.fixture
def pipeline():
    """Create a pipeline with mocked dependencies."""
    with patch("src.direct_leads.pipeline.ScraperEngine"), \
         patch("src.direct_leads.pipeline.RelevanceMatcher") as mock_matcher_cls, \
         patch("src.direct_leads.pipeline.LeadEnricher") as mock_enricher_cls:
        mock_matcher = mock_matcher_cls.return_value
        mock_matcher.score.return_value = 50
        mock_matcher.get_matched_skills.return_value = ["python"]
        mock_matcher.get_priority.return_value = "warm"

        mock_enricher = mock_enricher_cls.return_value
        mock_enricher.enrich_many.side_effect = lambda leads: leads

        p = DirectLeadsPipeline()
        yield p


class TestDeduplicate:
    """Tests for DirectLeadsPipeline._deduplicate."""

    def test_removes_existing_urls(self, pipeline):
        leads = [
            DirectLead(source="reddit", title="A", url="http://a.com"),
            DirectLead(source="reddit", title="B", url="http://b.com"),
        ]
        existing = {"http://a.com"}
        result = pipeline._deduplicate(leads, existing)
        assert len(result) == 1
        assert result[0].url == "http://b.com"

    def test_removes_duplicate_urls_within_batch(self, pipeline):
        leads = [
            DirectLead(source="reddit", title="A", url="http://same.com"),
            DirectLead(source="indeed", title="B", url="http://same.com"),
        ]
        result = pipeline._deduplicate(leads, set())
        assert len(result) == 1
        assert result[0].source == "reddit"

    def test_empty_leads(self, pipeline):
        result = pipeline._deduplicate([], set())
        assert result == []

    def test_no_existing_urls(self, pipeline):
        leads = [
            DirectLead(source="reddit", title="A", url="http://a.com"),
            DirectLead(source="indeed", title="B", url="http://b.com"),
        ]
        result = pipeline._deduplicate(leads, set())
        assert len(result) == 2

    def test_skips_leads_without_url(self, pipeline):
        leads = [
            DirectLead(source="reddit", title="A", url=""),
            DirectLead(source="reddit", title="B", url="http://b.com"),
        ]
        result = pipeline._deduplicate(leads, set())
        assert len(result) == 1
        assert result[0].url == "http://b.com"


class TestDetectBudget:
    """Tests for DirectLeadsPipeline._detect_budget."""

    def test_high_budget(self, pipeline):
        assert pipeline._detect_budget("We have a $10,000 budget for this project") == "high"
        assert pipeline._detect_budget("Budget: $5000") == "high"

    def test_medium_budget(self, pipeline):
        assert pipeline._detect_budget("Budget is $2,000") == "medium"
        assert pipeline._detect_budget("$1000 for the project") == "medium"

    def test_low_budget(self, pipeline):
        assert pipeline._detect_budget("$500 max") == "low"
        assert pipeline._detect_budget("$100 job") == "low"

    def test_budget_keyword(self, pipeline):
        assert pipeline._detect_budget("We have a budget allocated") == "medium"
        assert pipeline._detect_budget("We pay well for quality work") == "medium"
        assert pipeline._detect_budget("Competitive rate offered") == "medium"

    def test_no_budget_signal(self, pipeline):
        assert pipeline._detect_budget("Looking for a python developer") is None
        assert pipeline._detect_budget("") is None

    def test_first_amount_used(self, pipeline):
        # First dollar amount determines the signal
        assert pipeline._detect_budget("$500 to $10,000 range") == "low"


class TestDetectUrgency:
    """Tests for DirectLeadsPipeline._detect_urgency."""

    def test_urgent(self, pipeline):
        assert pipeline._detect_urgency("Need this done ASAP") == "urgent"
        assert pipeline._detect_urgency("URGENT: looking for developer") == "urgent"
        assert pipeline._detect_urgency("Need someone immediately") == "urgent"
        assert pipeline._detect_urgency("Must be done this week") == "urgent"

    def test_normal(self, pipeline):
        assert pipeline._detect_urgency("Starting soon") == "normal"
        assert pipeline._detect_urgency("Hoping to start next week") == "normal"
        assert pipeline._detect_urgency("Within a month ideally") == "normal"

    def test_no_urgency(self, pipeline):
        assert pipeline._detect_urgency("Looking for a python developer") is None
        assert pipeline._detect_urgency("") is None


class TestExport:
    """Tests for DirectLeadsPipeline._export."""

    def test_export_creates_file(self, pipeline, tmp_path):
        with patch("src.direct_leads.pipeline.DIRECT_OUTPUT_DIR", tmp_path):
            leads = [
                DirectLead(
                    source="reddit",
                    title="Python Dev Needed",
                    description="Looking for a python developer",
                    url="http://reddit.com/post/1",
                    relevance_score=75,
                    matched_skills=["python"],
                ),
            ]
            # Need to set up the matcher for priority
            pipeline.matcher.get_priority = MagicMock(return_value="hot")

            result = pipeline._export(leads, ["python", "developer"])

        assert len(result) == 1
        assert "direct_python_developer" in result[0]
        assert result[0].endswith(".xlsx")

        import pandas as pd
        df = pd.read_excel(result[0])
        assert len(df) == 1
        assert df.iloc[0]["Source"] == "reddit"
        assert df.iloc[0]["Title"] == "Python Dev Needed"
        assert df.iloc[0]["Priority"] == "HOT"

    def test_export_sorts_by_priority(self, pipeline, tmp_path):
        with patch("src.direct_leads.pipeline.DIRECT_OUTPUT_DIR", tmp_path):
            leads = [
                DirectLead(source="a", title="Cold", url="http://a.com", relevance_score=10, matched_skills=[]),
                DirectLead(source="b", title="Hot", url="http://b.com", relevance_score=90, matched_skills=["python"]),
                DirectLead(source="c", title="Warm", url="http://c.com", relevance_score=50, matched_skills=[]),
            ]

            def mock_priority(score):
                if score >= 60:
                    return "hot"
                elif score >= 35:
                    return "warm"
                return "cold"

            pipeline.matcher.get_priority = mock_priority
            result = pipeline._export(leads, ["test"])

        import pandas as pd
        df = pd.read_excel(result[0])
        assert list(df["Priority"]) == ["HOT", "WARM", "COLD"]


class TestRunPipeline:
    """Integration-style tests for the run method."""

    def _make_pipeline(self):
        """Create a pipeline with properly mocked dependencies."""
        pipeline = DirectLeadsPipeline()
        pipeline.enricher = MagicMock()
        pipeline.enricher.enrich_many = MagicMock(side_effect=lambda leads: leads)
        pipeline.matcher = MagicMock()
        pipeline.matcher.score.return_value = 50
        pipeline.matcher.get_matched_skills.return_value = []
        pipeline.matcher.get_priority.return_value = "warm"
        return pipeline

    def test_run_returns_empty_when_no_leads(self):
        with patch("src.direct_leads.pipeline.ScraperEngine"), \
             patch("src.direct_leads.pipeline.get_existing_direct_lead_urls", return_value=set()):

            pipeline = self._make_pipeline()

            with patch.dict("src.direct_leads.pipeline.SCRAPER_CLASSES", {
                "reddit": MagicMock(return_value=MagicMock(search=AsyncMock(return_value=[]))),
            }):
                result = asyncio.run(pipeline.run(["python"], sources=["reddit"]))

        assert result == []

    def test_run_skips_unknown_source(self):
        with patch("src.direct_leads.pipeline.ScraperEngine"), \
             patch("src.direct_leads.pipeline.get_existing_direct_lead_urls", return_value=set()):

            pipeline = self._make_pipeline()
            result = asyncio.run(pipeline.run(["python"], sources=["nonexistent_source"]))

        assert result == []

    def test_run_handles_scraper_exception(self):
        with patch("src.direct_leads.pipeline.ScraperEngine"), \
             patch("src.direct_leads.pipeline.get_existing_direct_lead_urls", return_value=set()):

            pipeline = self._make_pipeline()

            failing_scraper = MagicMock()
            failing_scraper.return_value.search = AsyncMock(side_effect=Exception("Network error"))

            with patch.dict("src.direct_leads.pipeline.SCRAPER_CLASSES", {
                "reddit": failing_scraper,
            }):
                result = asyncio.run(pipeline.run(["python"], sources=["reddit"]))

        assert result == []
