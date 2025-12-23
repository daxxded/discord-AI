from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class BotConfig:
    discord_token: str
    anthropic_key: str
    telegram_token: str
    guild_id: int
    admins: List[int]

    @classmethod
    def load(cls, path: str | Path) -> "BotConfig":
        data = json.loads(Path(path).read_text())
        return cls(
            discord_token=data["discord_token"],
            anthropic_key=data["anthropic_key"],
            telegram_token=data["telegram_token"],
            guild_id=int(data["guild_id"]),
            admins=[int(admin) for admin in data.get("admins", [])],
        )


def find_config_path() -> Path:
    candidate = Path(__file__).resolve().parent.parent / "config.json"
    if not candidate.exists():
        example = Path(__file__).resolve().parent.parent / "config.example.json"
        if not example.exists():
            raise FileNotFoundError("No config.json or config.example.json file found")
        return example
    return candidate
