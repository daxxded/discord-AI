from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    approved: bool
    escalate: bool
    summary: str
    risks: List[str]


class AI2Reviewer:
    def __init__(self, max_lines_before_escalation: int = 60) -> None:
        self.max_lines_before_escalation = max_lines_before_escalation

    def review(self, script: str) -> ReviewResult:
        normalized = script.lower()
        risks: List[str] = []

        if "requests" in normalized or "http" in normalized:
            risks.append("External network usage detected")
        if "sleep(" in normalized or "asyncio.sleep" in normalized:
            risks.append("Timed or scheduled execution present")
        if any(keyword in normalized for keyword in ("for channel", "for user", "mass")):
            risks.append("Potential multi-user or multi-channel impact")
        if script.count("\n") > self.max_lines_before_escalation:
            risks.append("Large script length exceeds auto-approval threshold")

        if not script.strip():
            return ReviewResult(
                approved=False,
                escalate=False,
                summary="Empty script provided; nothing to execute",
                risks=["No-op"],
            )

        escalate = bool(risks)
        summary = self._summarize_script(script)
        approved = not escalate
        return ReviewResult(approved=approved, escalate=escalate, summary=summary, risks=risks)

    def _summarize_script(self, script: str) -> str:
        first_lines = textwrap.dedent(script).strip().splitlines()[:6]
        summary = " | ".join(line.strip() for line in first_lines)
        if not summary:
            summary = "Script with no readable content"
        return summary[:280]
