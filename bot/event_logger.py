from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class JSONEventLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def log(self, event: str, **payload: Any) -> None:
        record: Dict[str, Any] = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        line = json.dumps(record, ensure_ascii=False)
        async with self._lock:
            await asyncio.to_thread(self._write_line, line)

    def _write_line(self, line: str) -> None:
        with self.path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
