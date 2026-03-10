"""Tests for RelevanceMatcher (Task 15)."""

import pytest
from src.direct_leads.matcher import RelevanceMatcher


@pytest.fixture
def matcher():
    return RelevanceMatcher(
        skills=["python", "react", "fastapi"],
        services=["web app", "api", "automation"],
    )


class TestScore:
    def test_no_match_returns_zero(self, matcher):
        assert matcher.score("unrelated posting about gardening") == 0

    def test_single_skill_match(self, matcher):
        score = matcher.score("Looking for a python developer")
        assert score >= 10  # at least one skill

    def test_multiple_skill_matches(self, matcher):
        score = matcher.score("Need python and react developer with fastapi experience")
        # 3 skills * 10 = 30
        assert score >= 30

    def test_skill_cap_at_40(self, matcher):
        """Even if all skills match, skill score is capped at SKILL_CAP."""
        m = RelevanceMatcher(
            skills=["python", "react", "fastapi", "django", "flask"],
            services=["zzz_no_match"],
        )
        score = m.score("python react fastapi django flask")
        # 5 * 10 = 50 but capped at 40
        assert score == 40

    def test_service_match(self, matcher):
        score = matcher.score("We need someone to build a web app")
        assert score >= 15

    def test_service_cap_at_30(self, matcher):
        score = matcher.score("Build a web app with api and automation features")
        # 3 services * 15 = 45, capped at 30
        assert score <= 100
        # Verify capping: services alone should give 30 max
        m = RelevanceMatcher(skills=[], services=["web app", "api", "automation"])
        svc_score = m.score("web app api automation")
        assert svc_score == 30

    def test_budget_flag(self, matcher):
        base = matcher.score("python developer needed")
        with_budget = matcher.score("python developer needed", has_budget=True)
        assert with_budget == base + 10

    def test_budget_keyword_in_text(self, matcher):
        base = matcher.score("python developer needed")
        with_budget_text = matcher.score("python developer needed, budget $5000")
        assert with_budget_text >= base + 10

    def test_urgency_keyword(self, matcher):
        base = matcher.score("python developer")
        urgent = matcher.score("python developer needed asap")
        assert urgent == base + 10

    def test_remote_flag(self, matcher):
        base = matcher.score("python developer")
        remote = matcher.score("python developer", is_remote=True)
        assert remote == base + 5

    def test_remote_keyword_in_text(self, matcher):
        base = matcher.score("python developer")
        remote_text = matcher.score("python developer remote position")
        assert remote_text == base + 5

    def test_contact_bonus(self, matcher):
        base = matcher.score("python developer")
        with_contact = matcher.score("python developer", has_contact=True)
        assert with_contact == base + 10

    def test_recency_under_24h(self, matcher):
        base = matcher.score("python developer")
        recent = matcher.score("python developer", posted_hours_ago=12)
        assert recent == base + 10

    def test_recency_under_72h(self, matcher):
        base = matcher.score("python developer")
        medium = matcher.score("python developer", posted_hours_ago=48)
        assert medium == base + 5

    def test_recency_over_72h(self, matcher):
        base = matcher.score("python developer")
        old = matcher.score("python developer", posted_hours_ago=100)
        assert old == base

    def test_max_score_capped_at_100(self, matcher):
        # Throw everything at it
        score = matcher.score(
            "python react fastapi web app api automation urgent asap remote budget $10k",
            posted_hours_ago=1,
            has_budget=True,
            has_contact=True,
            is_remote=True,
        )
        assert score <= 100

    def test_case_insensitive(self, matcher):
        lower = matcher.score("python developer")
        upper = matcher.score("PYTHON Developer")
        assert lower == upper


class TestGetPriority:
    def test_hot(self, matcher):
        assert matcher.get_priority(60) == "hot"
        assert matcher.get_priority(80) == "hot"
        assert matcher.get_priority(100) == "hot"

    def test_warm(self, matcher):
        assert matcher.get_priority(35) == "warm"
        assert matcher.get_priority(50) == "warm"
        assert matcher.get_priority(59) == "warm"

    def test_cold(self, matcher):
        assert matcher.get_priority(0) == "cold"
        assert matcher.get_priority(20) == "cold"
        assert matcher.get_priority(34) == "cold"


class TestGetMatchedSkills:
    def test_returns_matched(self, matcher):
        matched = matcher.get_matched_skills("Looking for python and react developer")
        assert "python" in matched
        assert "react" in matched
        assert "fastapi" not in matched

    def test_returns_empty_on_no_match(self, matcher):
        matched = matcher.get_matched_skills("Java and C# developer needed")
        assert matched == []

    def test_word_boundary(self, matcher):
        """'react' should not match 'reactive'."""
        matched = matcher.get_matched_skills("reactive programming expert")
        assert "react" not in matched
