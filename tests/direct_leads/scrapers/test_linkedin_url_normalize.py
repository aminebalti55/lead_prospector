"""Tests for LinkedIn URL normalization (strip session tracking params)."""
from __future__ import annotations

import pytest

from src.direct_leads.scrapers.linkedin_jobs import _strip_linkedin_session_params


def test_strips_refId_and_trackingId():
    url = "https://www.linkedin.com/jobs/view/12345?refId=ABC&trackingId=XYZ"
    assert _strip_linkedin_session_params(url) == "https://www.linkedin.com/jobs/view/12345"


def test_strips_all_query_string():
    url = "https://www.linkedin.com/jobs/view/12345?refId=ABC&someOther=DEF"
    assert _strip_linkedin_session_params(url) == "https://www.linkedin.com/jobs/view/12345"


def test_passthrough_when_no_query():
    url = "https://www.linkedin.com/jobs/view/12345"
    assert _strip_linkedin_session_params(url) == url


def test_handles_empty():
    assert _strip_linkedin_session_params("") == ""
    assert _strip_linkedin_session_params(None) == ""


def test_strips_fragment_too():
    url = "https://www.linkedin.com/jobs/view/12345?refId=ABC#section"
    assert _strip_linkedin_session_params(url) == "https://www.linkedin.com/jobs/view/12345"
