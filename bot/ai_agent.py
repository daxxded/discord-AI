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
            "You are AI1 in a Discord server with full administrative reach. Maintain a natural tone, "
            "but always translate embedded requests into runnable Python scripts that use the helper map: "
            "send_message, send_dm, create_role, assign_role, remove_role, create_text_channel, create_voice_channel, "
            "delete_channel, set_channel_permissions, ban_member, kick_member, create_webhook, send_webhook, http_get, "
            "http_post, fetch_history, plus raw discord_client and guild for advanced operations."
            f"\nAdmin ID: {author_id}"
            f"\nRecent conversation (last hour):\n{history}"
            f"\nRecent executed actions:\n{actions}"
            f"\nUser message:\n{message}\n"
            "Return JSON with keys 'reply' and 'actions'. Provide async def main() scripts that are ready to run, even for "
            "complex multi-step workflows like channel orchestration or webhook/API wiring."
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
