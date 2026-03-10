import re
import logging
from src.core.config import settings

logger = logging.getLogger(__name__)


class RelevanceMatcher:
    """Scores job postings/leads against user's skill profile."""

    SKILL_CAP = 40
    SERVICE_CAP = 30

    URGENCY_WORDS = [
        "asap", "urgent", "immediately", "this week",
        "right away", "rush", "fast turnaround",
    ]
    BUDGET_WORDS = [
        "budget", "$", "pay", "rate", "compensation",
        "salary", "hourly", "fixed price",
    ]
    REMOTE_WORDS = [
        "remote", "work from home", "wfh", "distributed", "anywhere",
    ]

    def __init__(
        self,
        skills: list[str] | None = None,
        services: list[str] | None = None,
    ):
        self.skills = [s.lower() for s in (skills or settings.direct_leads.your_skills)]
        self.services = [s.lower() for s in (services or settings.direct_leads.your_services)]

    def score(
        self,
        description: str,
        posted_hours_ago: float | None = None,
        has_budget: bool = False,
        has_contact: bool = False,
        is_remote: bool = False,
    ) -> int:
        """Score a job/lead description for relevance. Returns 0-100."""
        text = description.lower()
        total = 0

        # Skill matches (+10 each, capped at 40)
        skill_score = 0
        for skill in self.skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text):
                skill_score += 10
        total += min(skill_score, self.SKILL_CAP)

        # Service matches (+15 each, capped at 30)
        svc_score = 0
        for svc in self.services:
            if svc in text:
                svc_score += 15
        total += min(svc_score, self.SERVICE_CAP)

        # Budget mentioned
        if has_budget or any(w in text for w in self.BUDGET_WORDS):
            total += 10

        # Urgency
        if any(w in text for w in self.URGENCY_WORDS):
            total += 10

        # Remote
        if is_remote or any(w in text for w in self.REMOTE_WORDS):
            total += 5

        # Direct contact
        if has_contact:
            total += 10

        # Recency
        if posted_hours_ago is not None:
            if posted_hours_ago < 24:
                total += 10
            elif posted_hours_ago < 72:
                total += 5

        return min(total, 100)

    def get_priority(self, score: int) -> str:
        if score >= 60:
            return "hot"
        elif score >= 35:
            return "warm"
        return "cold"

    def get_matched_skills(self, description: str) -> list[str]:
        text = description.lower()
        return [s for s in self.skills if re.search(r'\b' + re.escape(s) + r'\b', text)]
