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
            "You are AI1 in a Discord server. Maintain a natural tone, but also produce "
            "structured actions for administrative tasks."
            f"\nAdmin ID: {author_id}"
            f"\nRecent conversation (last hour):\n{history}"
            f"\nRecent executed actions:\n{actions}"
            f"\nUser message:\n{message}\n"
            "Return JSON with keys 'reply' and 'actions'. 'actions' should be Python async def main() scripts "
            "invoking provided helper functions such as send_message, create_role, assign_role, and fetch_history."
        )
        return prompt

    def respond(self, author_id: int, message: str) -> Dict[str, List[str]]:
        prompt = self.build_prompt(author_id, message)
        raw = self.client.structured_plan(prompt, system=DEFAULT_SYSTEM_MESSAGE)
        log.debug("Raw model output: %s", raw)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"reply": "I couldn't parse that request yet; could you rephrase?", "actions": []}

        if not isinstance(parsed, dict):
            return {"reply": "Unexpected model response format.", "actions": []}
        reply = str(parsed.get("reply", ""))
        actions = parsed.get("actions") or []
        if not isinstance(actions, list):
            actions = []
        return {"reply": reply, "actions": [str(action) for action in actions]}
