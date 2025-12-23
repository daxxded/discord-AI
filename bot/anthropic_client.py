from __future__ import annotations

import logging
from typing import List, Sequence

from anthropic import Anthropic

log = logging.getLogger(__name__)


class AnthropicClient:
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022") -> None:
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def complete(self, prompt: str, system: str, temperature: float = 0) -> str:
        log.debug("Sending prompt to AnthropIc model %s", self.model)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        content: Sequence[dict] = response.content
        if not content:
            return ""
        return "".join(chunk.get("text", "") for chunk in content if isinstance(chunk, dict))

    def structured_plan(self, prompt: str, system: str) -> str:
        return self.complete(prompt=prompt, system=system, temperature=0)


DEFAULT_SYSTEM_MESSAGE = (
    "You are AI1, an autonomous Discord administrative agent with full Discord control, "
    "monitored by AI2 and a human approval layer. Hold normal conversations while also "
    "executing any administrative request, from simple role tweaks to complex multi-step "
    "automation. Always respond with JSON: {\"reply\": <human-friendly message>, \"actions\": [<python scripts>]}. "
    "Each action must be an async def main(): script using the provided helpers mapping, which includes: \n"
    "- send_message(channel_id, content) and send_dm(user_id, content)\n"
    "- create_role(name, color|None, permissions|None) returning a role object\n"
    "- assign_role(user_id, role_id) and remove_role(user_id, role_id)\n"
    "- create_text_channel(name, category_id|None), create_voice_channel(name, category_id|None), delete_channel(channel_id)\n"
    "- set_channel_permissions(channel_id, target_id, overwrite_dict) for members or roles\n"
    "- create_webhook(channel_id, name) returning the webhook URL, send_webhook(webhook_url, content, username|None, avatar_url|None)\n"
    "- http_get(url) / http_post(url, json|None) for calling external APIs to wire up webhooks or automations\n"
    "- fetch_history(channel_id, limit) plus access to the raw discord_client and guild objects for advanced flows.\n"
    "Prefer explicit, multi-action plans when needed. Ensure scripts are runnable without additional context and include any ids, names, or payloads you infer or request."
)
