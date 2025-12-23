from __future__ import annotations

import json
import logging
from typing import Dict, List

from .anthropic_client import AnthropicClient, DEFAULT_SYSTEM_MESSAGE
from .memory import RollingMemory

log = logging.getLogger(__name__)


class AIConversationAgent:
    def __init__(self, client: AnthropicClient, memory: RollingMemory) -> None:
        self.client = client
        self.memory = memory

    def build_prompt(self, author_id: int, message: str) -> str:
        history = "\n".join(self.memory.get_admin_context(author_id))
        actions = "\n".join(self.memory.get_recent_actions())
        prompt = (
            "You are an autonomous Discord AI with full administrative reach. Hold natural conversations first, but when "
            "the user asks for an action, produce runnable Python scripts that directly use the provided objects:\n"
            "- discord_client (the discord.Client instance)\n"
            "- guild (the active guild object)\n"
            "Use discord.py primitives directly—there is no helper map. You may also import discord and asyncio when needed."
            f"\nAdmin/User ID: {author_id}"
            f"\nRecent conversation (last hour):\n{history}"
            f"\nRecent executed actions:\n{actions}"
            f"\nUser message:\n{message}\n"
            "Return JSON with keys 'reply' and 'actions'. Each action must define async def main(): that can run as-is."
        )
        return prompt

    def respond(self, author_id: int, message: str) -> Dict[str, List[str]]:
        prompt = self.build_prompt(author_id, message)
        raw = self.client.structured_plan(prompt, system=DEFAULT_SYSTEM_MESSAGE)
        log.debug("Raw model output: %s", raw)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            fallback = raw.strip() or "I'm here and ready to help."
            return {"reply": fallback, "actions": []}

        if not isinstance(parsed, dict):
            fallback = raw.strip() if isinstance(raw, str) else "I'm here and ready to help."
            return {"reply": fallback, "actions": []}
        reply = str(parsed.get("reply", ""))
        actions = parsed.get("actions") or []
        if not isinstance(actions, list):
            actions = []
        return {"reply": reply, "actions": [str(action) for action in actions]}
