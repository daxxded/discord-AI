"""Entrypoint wiring the Discord AI bot components together."""
from __future__ import annotations

from pathlib import Path

from discord_ai.bot import DiscordAIBot
from discord_ai.config import BotConfig, load_config


def build_bot(config_path: Path = Path("config.json")) -> DiscordAIBot:
    config = load_config(config_path)
    return DiscordAIBot(config=config)


if __name__ == "__main__":
    bot = build_bot()
    sample_messages = [{"content": "hello"}, {"content": "world"}]
    payload = {
        "messages": sample_messages,
        "channels": [111, 222, 333, 444],
        "random_text": "Random hello from AI",
        "dm_user_id": 999,
        "dm_text": "This is a DM preview",
        "scheduled_messages": [
            {"channel_id": 111, "content": "Welcome!", "delay_seconds": 3, "repeat": True, "interval_seconds": 3},
        ],
    }
    result = bot.handle_request(admin_id=bot.config.admins[0], request="demo freedom actions", payload=payload)
    print(result)
