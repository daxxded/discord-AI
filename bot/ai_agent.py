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
            "You are an autonomous Discord AI with full administrative reach. Hold natural, conversational tone first; when "
            "the user asks for an action, produce runnable Python scripts that directly use the provided objects:\n"
            "- discord_client (the discord.Client instance)\n"
            "- guild (the active guild object)\n"
            "Use discord.py primitives directly—there is no helper map. You may also import discord and asyncio when needed. "
            "Always speak in first person as AI1 (e.g., \"I'm AI1, ...\") and avoid simply repeating the user's words. "
            "Chat normally when the user is just talking, but keep replies concise and human. When actions are needed, include "
            "them alongside a short reply."
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
        parsed = self._parse_plan(raw)
        if not parsed:
            return {"reply": self._friendly_reply(message, raw), "actions": []}

        reply = str(parsed.get("reply", "") or "").strip()
        actions = parsed.get("actions") or []
        if not isinstance(actions, list):
            actions = []
        if not reply:
            reply = self._friendly_reply(message, raw)
        return {"reply": reply, "actions": [str(action) for action in actions]}

    def _friendly_reply(self, message: str, raw: str) -> str:
        text = raw.strip()
        if text:
            return text
        lower = message.lower()
        if "name" in lower:
            return "I'm AI1, your Discord admin assistant."
        if "how are you" in lower or "how's it" in lower:
            return "I'm AI1 and doing great—how can I help?"
        if message.strip():
            return f"I'm AI1 and I hear you: {message.strip()}"
        return "I'm AI1 and ready to help."

    def _parse_plan(self, raw: str) -> Dict | None:
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
        if "{" in raw and "}" in raw:
            try:
                snippet = raw[raw.find("{") : raw.rfind("}") + 1]
                parsed = json.loads(snippet)
                return parsed if isinstance(parsed, dict) else None
            except Exception:  # noqa: BLE001
                return None
        return None
