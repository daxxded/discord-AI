from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List, Tuple

ONE_HOUR_SECONDS = 60 * 60


@dataclass
class MemoryEvent:
    timestamp: float
    content: str


class RollingMemory:
    def __init__(self, horizon_seconds: int = ONE_HOUR_SECONDS) -> None:
        self.horizon_seconds = horizon_seconds
        self._per_admin: Dict[int, Deque[MemoryEvent]] = defaultdict(deque)
        self._actions: Deque[MemoryEvent] = deque(maxlen=500)

    def add_message(self, admin_id: int, content: str) -> None:
        now = time.time()
        self._per_admin[admin_id].append(MemoryEvent(now, content))
        self._prune(admin_id, now)

    def add_action(self, description: str) -> None:
        self._actions.append(MemoryEvent(time.time(), description))

    def get_admin_context(self, admin_id: int) -> List[str]:
        now = time.time()
        self._prune(admin_id, now)
        return [event.content for event in self._per_admin.get(admin_id, [])]

    def get_recent_actions(self) -> List[str]:
        return [event.content for event in self._actions]

    def _prune(self, admin_id: int, now: float) -> None:
        horizon = now - self.horizon_seconds
        admin_memory = self._per_admin.get(admin_id)
        if not admin_memory:
            return
        while admin_memory and admin_memory[0].timestamp < horizon:
            admin_memory.popleft()

    def snapshot(self) -> Dict[str, Iterable[Tuple[float, str]]]:
        return {
            "admins": {
                admin: [(event.timestamp, event.content) for event in events]
                for admin, events in self._per_admin.items()
            },
            "actions": [(event.timestamp, event.content) for event in self._actions],
        }
