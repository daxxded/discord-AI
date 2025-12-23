"""Per-admin memory with 1 hour TTL."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, List

TTL = timedelta(hours=1)


@dataclass
class MemoryEntry:
    content: str
    timestamp: datetime


class AdminMemory:
    def __init__(self):
        self._store: Dict[int, Deque[MemoryEntry]] = defaultdict(deque)

    def remember(self, admin_id: int, content: str) -> None:
        self._store[admin_id].append(MemoryEntry(content=content, timestamp=datetime.now(timezone.utc)))
        self._expire(admin_id)

    def recall(self, admin_id: int) -> List[str]:
        self._expire(admin_id)
        return [entry.content for entry in self._store.get(admin_id, [])]

    def _expire(self, admin_id: int) -> None:
        cutoff = datetime.now(timezone.utc) - TTL
        queue = self._store.get(admin_id)
        if not queue:
            return
        while queue and queue[0].timestamp < cutoff:
            queue.popleft()
