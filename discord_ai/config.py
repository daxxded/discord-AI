"""Configuration helpers for the Discord AI bot."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import json


CONFIG_FILE = Path("config.json")


@dataclass
class BotConfig:
    discord_token: str
    anthropic_key: str
    telegram_token: str
    guild_id: int
    admins: List[int]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BotConfig":
        return cls(
            discord_token=data.get("discord_token", ""),
            anthropic_key=data.get("anthropic_key", ""),
            telegram_token=data.get("telegram_token", ""),
            guild_id=int(data.get("guild_id", 0)),
            admins=[int(admin) for admin in data.get("admins", [])],
        )


def load_config(path: Path = CONFIG_FILE) -> BotConfig:
    """Load configuration from a JSON file.

    The function is defensive to avoid crashes when the config is missing or malformed.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found at {path.resolve()}. Please provide config.json based on config.example.json"
        )

    with path.open("r", encoding="utf-8") as fp:
        try:
            data = json.load(fp)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    return BotConfig.from_dict(data)
