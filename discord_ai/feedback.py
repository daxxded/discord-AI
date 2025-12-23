"""Feedback loop helper to harden AI actions."""
from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Callable, Generic, Optional, Tuple, TypeVar


T = TypeVar("T")


@dataclass
class FeedbackOutcome(Generic[T]):
    result: Optional[T]
    attempts: int
    last_error: Optional[str]


class FeedbackLooper(Generic[T]):
    """Attempt an action up to three times with contextual feedback.

    This creates three feedback loops to improve reliability when executing AI-generated code.
    """

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def run(self, action: Callable[[int, Optional[str]], T]) -> FeedbackOutcome[T]:
        last_error: Optional[str] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = action(attempt, last_error)
                return FeedbackOutcome(result=result, attempts=attempt, last_error=last_error)
            except Exception:  # noqa: BLE001 - we want full capture for feedback
                last_error = traceback.format_exc()
        return FeedbackOutcome(result=None, attempts=self.max_attempts, last_error=last_error)
