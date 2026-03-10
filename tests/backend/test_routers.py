"""Tests for the refactored backend routers."""
from __future__ import annotations

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app, raise_server_exceptions=False)


# ── Health ────────────────────────────────────────────────────────────

class TestHealth:
    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


# ── Cold outreach router ─────────────────────────────────────────────

class TestColdOutreach:
    @patch("backend.routers.cold_outreach.list_files")
    def test_list_cold_files(self, mock_list):
        mock_list.return_value = [
            {"name": "test.xlsx", "section": "cold", "modified_at": "2025-01-01T00:00:00", "size_bytes": 1024}
        ]
        resp = client.get("/api/cold/files")
        assert resp.status_code == 200
        data = resp.json()
        assert "files" in data
        # list_files called twice: once for "cold" and once for "legacy"
        assert mock_list.call_count == 2

    @patch("backend.routers.cold_outreach.read_leads")
    def test_get_cold_leads(self, mock_read):
        mock_read.return_value = (["Name", "Phone"], [{"Name": "Acme", "Phone": "555"}])
        resp = client.get("/api/cold/files/test.xlsx/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["file"] == "test.xlsx"
        assert data["columns"] == ["Name", "Phone"]
        assert len(data["rows"]) == 1

    @patch("backend.routers.cold_outreach.read_leads")
    def test_get_cold_leads_fallback_legacy(self, mock_read):
        """If file not found in cold, falls back to legacy."""
        def side_effect(filename, section):
            if section == "cold":
                raise FileNotFoundError(filename)
            return (["Name"], [{"Name": "Legacy"}])

        mock_read.side_effect = side_effect
        resp = client.get("/api/cold/files/old.xlsx/leads")
        assert resp.status_code == 200
        assert resp.json()["rows"][0]["Name"] == "Legacy"

    @patch("backend.routers.cold_outreach.read_leads")
    def test_get_cold_leads_not_found(self, mock_read):
        mock_read.side_effect = FileNotFoundError("nope")
        resp = client.get("/api/cold/files/missing.xlsx/leads")
        assert resp.status_code == 404

    def test_list_cold_runs(self):
        resp = client.get("/api/cold/runs")
        assert resp.status_code == 200
        assert "runs" in resp.json()

    def test_get_cold_run_not_found(self):
        resp = client.get("/api/cold/runs/nonexistent")
        assert resp.status_code == 404


# ── Direct leads router ──────────────────────────────────────────────

class TestDirectLeads:
    @patch("backend.routers.direct_leads.list_files")
    def test_list_direct_leads_empty(self, mock_list):
        mock_list.return_value = []
        resp = client.get("/api/direct/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["leads"] == []
        assert data["total"] == 0

    def test_get_direct_lead_not_found(self):
        with patch("backend.routers.direct_leads.list_files", return_value=[]):
            resp = client.get("/api/direct/leads/abc123")
            assert resp.status_code == 404

    def test_create_scan_placeholder(self):
        resp = client.post("/api/direct/scans", json={"keywords": ["python"]})
        assert resp.status_code == 200
        assert "scan_id" in resp.json()

    def test_list_scans(self):
        resp = client.get("/api/direct/scans")
        assert resp.status_code == 200
        assert resp.json()["scans"] == []


# ── Saved searches ───────────────────────────────────────────────────

class TestSavedSearches:
    @patch("backend.routers.direct_leads.SAVED_SEARCHES_FILE", new_callable=lambda: MagicMock)
    def test_list_saved_searches_empty(self, mock_file):
        """When no file exists, returns empty list."""
        with patch("backend.routers.direct_leads._load_searches", return_value=[]):
            resp = client.get("/api/direct/saved-searches")
            assert resp.status_code == 200
            assert resp.json()["searches"] == []

    def test_crud_saved_search(self, tmp_path):
        """Full create/update/delete cycle with a temp file."""
        tmp_file = tmp_path / "saved_searches.json"
        with patch("backend.routers.direct_leads.SAVED_SEARCHES_FILE", tmp_file):
            # Create
            resp = client.post("/api/direct/saved-searches", json={"keywords": ["react"], "frequency": "daily"})
            assert resp.status_code == 200
            search = resp.json()
            search_id = search["id"]
            assert search["keywords"] == ["react"]
            assert search["enabled"] is True

            # List
            resp = client.get("/api/direct/saved-searches")
            assert resp.status_code == 200
            assert len(resp.json()["searches"]) == 1

            # Update
            resp = client.put(f"/api/direct/saved-searches/{search_id}", json={"enabled": False})
            assert resp.status_code == 200
            assert resp.json()["enabled"] is False

            # Delete
            resp = client.delete(f"/api/direct/saved-searches/{search_id}")
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

            # Verify empty
            resp = client.get("/api/direct/saved-searches")
            assert resp.status_code == 200
            assert len(resp.json()["searches"]) == 0


# ── Shared router ────────────────────────────────────────────────────

class TestShared:
    def test_email_templates(self):
        resp = client.get("/api/email/templates")
        assert resp.status_code == 200
        templates = resp.json()["templates"]
        assert len(templates) >= 3
        ids = [t["id"] for t in templates]
        assert "initial" in ids
        assert "followup" in ids

    def test_email_preview(self):
        resp = client.post("/api/email/preview", json={
            "template_id": "initial",
            "variables": {"business_name": "TestBiz", "city": "NYC", "niche": "plumbing"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "TestBiz" in data["subject"]
        assert "NYC" in data["body"]

    def test_email_preview_missing_template(self):
        resp = client.post("/api/email/preview", json={"template_id": "nonexistent"})
        assert resp.status_code == 404

    @patch("backend.routers.shared.list_files")
    def test_stats_empty(self, mock_list):
        mock_list.return_value = []
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_leads"] == 0

    @patch("backend.routers.shared.list_files")
    def test_cold_stats_empty(self, mock_list):
        mock_list.return_value = []
        resp = client.get("/api/stats/cold")
        assert resp.status_code == 200

    @patch("backend.routers.shared.list_files")
    def test_direct_stats_empty(self, mock_list):
        mock_list.return_value = []
        resp = client.get("/api/stats/direct")
        assert resp.status_code == 200


# ── Scheduler unit test ──────────────────────────────────────────────

class TestScheduler:
    def test_parse_frequency(self):
        from backend.scheduler import Scheduler
        s = Scheduler()
        assert s._parse_frequency("daily") == 24
        assert s._parse_frequency("weekly") == 168
        assert s._parse_frequency("6hours") == 6.0
        assert s._parse_frequency("12 hours") == 12.0
        assert s._parse_frequency("unknown") == 24


# ── Models ────────────────────────────────────────────────────────────

class TestModels:
    def test_direct_scan_create_request(self):
        from backend.models import DirectScanCreateRequest
        req = DirectScanCreateRequest(keywords=["python", "react"])
        assert req.keywords == ["python", "react"]
        assert req.max_results == 20
        assert req.sources is None

    def test_saved_search_request(self):
        from backend.models import SavedSearchRequest
        req = SavedSearchRequest(keywords=["fastapi"], frequency="weekly", max_results=50)
        assert req.frequency == "weekly"
        assert req.max_results == 50

    def test_existing_models_preserved(self):
        from backend.models import RunCreateRequest, DashboardStats, EmailTemplate
        # Existing models still importable
        req = RunCreateRequest(locations=["NYC"])
        assert req.locations == ["NYC"]
