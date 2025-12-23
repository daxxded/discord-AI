## Overview

An autonomous Discord administrative bot that pairs two cooperating agents (AI1 + AI2) with explicit human-in-the-loop guardrails. The bot is designed to be expressive and free while still protecting the server through validation, auditing, and defensive execution.

## Capabilities

- **Admin-level operations**: Create roles, send messages, and fulfill multi-step asks (e.g., *“summarize the last 20 messages and create a role”*).
- **Conversational + action aware**: Can hold a conversation while picking out embedded requests.
- **One-hour per-admin memory**: Contextual chat and request history is kept for each admin.
- **Full action trail**: Every action is timestamped and written to `data/actions.log`.
- **Three feedback loops**: Every execution is retried up to three times with error-aware adjustments for robustness.
- **AI1 freedom, AI2 review**: AI1 generates executable Python; AI2 blocks dangerous patterns and can escalate for human approval.

## Files

- `config.example.json`: Template for required credentials (Discord, Anthropic, Telegram), admin IDs, and non-admin chat-only IDs.
- `discord_ai/`:
  - `config.py`: Loads the JSON config defensively.
  - `audit_log.py`: Append-only timestamped action log.
  - `memory.py`: One-hour, per-admin conversational memory.
  - `feedback.py`: Three-attempt feedback loop for any action.
  - `executor.py`: AI1 script generation + AI2 safety review + sandboxed execution.
  - `bot.py`: High-level orchestrator with helpers for complex requests.
- `main.py`: Lightweight entrypoint to bootstrap a `DiscordAIBot` using `config.json`.

## Human-in-the-loop flow

1. **AI1** generates a Python snippet tailored to the request.
2. **AI2** runs static safety checks; unsafe scripts are rejected and logged.
3. **Execution** happens inside a restricted sandbox with three feedback attempts.
4. **Audit trail** records every step; human operators can inspect `data/actions.log` at any time.

## Running locally

1. Copy `config.example.json` to `config.json` and fill in your tokens and admin IDs.
2. Initialize the bot in your application code:

```python
from discord_ai.bot import DiscordAIBot
from discord_ai.config import load_config

bot = DiscordAIBot(config=load_config())
result = bot.handle_request(
    admin_id=123,
    request="summarize the last 20 messages and create a role",
    payload={
        "messages": [{"content": "hello"}, {"content": "world"}],
        "channels": [111, 222, 333, 444],
        "random_text": "Say hi in random channels",
        "dm_user_id": 555,
        "dm_text": "Here's your summary",
        "scheduled_messages": [
            {"channel_id": 111, "content": "Welcome!", "delay_seconds": 3, "repeat": True, "interval_seconds": 3},
        ],
    },
)
print(result)
```

3. Inspect the latest actions with `tail -n 50 data/actions.log`.

## Notes

- The sandbox in `executor.py` blocks common destructive patterns and keeps builtins empty to reduce blast radius while preserving AI freedom.
- Swap the static AI2 checks with your preferred model reviewer or Telegram approval layer for production use.
- Extend `BotContext` with your Discord client hooks (send message, create role, fetch history) to connect the orchestrator to the live server.
- Channel `1444077226365816864` is hard-protected from deletion within the orchestration layer.
