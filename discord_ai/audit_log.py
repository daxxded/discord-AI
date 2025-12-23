"""Action logging utilities."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_LOG_PATH = Path("data/actions.log")


@dataclass
class ActionRecord:
    action: str
    status: str
    actor: str
    details: Dict[str, Any]
    error: Optional[str] = None
    timestamp: str = ""

    def with_timestamp(self) -> "ActionRecord":
        self.timestamp = datetime.now(timezone.utc).isoformat()
        return self


class AuditLog:
    """Persist and retrieve action history.

    The log is append-only to preserve a permanent trail of AI behavior.
    """

    def __init__(self, path: Path = DEFAULT_LOG_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: ActionRecord) -> None:
        serializable = asdict(record.with_timestamp())
        with self.path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(serializable, ensure_ascii=False) + "\n")

    def history(self) -> Iterable[ActionRecord]:
        if not self.path.exists():
            return []

        records: List[ActionRecord] = []
        with self.path.open("r", encoding="utf-8") as fp:
            for line in fp:
                try:
                    payload = json.loads(line)
                    records.append(
                        ActionRecord(
                            action=payload.get("action", ""),
                            status=payload.get("status", ""),
                            actor=payload.get("actor", ""),
                            details=payload.get("details", {}),
                            error=payload.get("error"),
                            timestamp=payload.get("timestamp", ""),
                        )
                    )
                except json.JSONDecodeError:
                    continue
        return records

    def tail(self, limit: int = 50) -> List[ActionRecord]:
        return list(self.history())[-limit:]
