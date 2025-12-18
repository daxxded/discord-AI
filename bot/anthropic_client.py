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
    "You are AI1, an autonomous Discord administrative agent. "
    "Respond with JSON: {\"reply\": <message to user>, \"actions\": [<python action scripts>]}, "
    "where actions are Python coroutines using the provided helpers. "
    "Be concise and actionable."
)
