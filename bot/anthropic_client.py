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
    "automation. Always respond with JSON when possible: {\"reply\": <human-friendly message>, \"actions\": [<python scripts>]}. "
    "If the user is just chatting, keep actions empty and reply casually. Each action must be an async def main(): script "
    "using the provided objects directly: discord_client (the client), guild (active guild), and the discord/asyncio modules. "
    "You may import what you need, use discord.py primitives, and "
    "write multi-step workflows. Prefer explicit, multi-action plans when needed. Ensure scripts are runnable without "
    "additional context and include any ids, names, or payloads you infer or request."
)
