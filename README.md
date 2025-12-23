# Autonomous Discord AI Bot

An administrative Discord bot powered by Anthropic Claude models with a dual-agent safety layer. AI1 plans and converses naturally while holding full administrative powers; AI2 reviews planned scripts and escalates risky actions for manual Telegram approval.

## Features
- Conversational AI (Claude haiku models) that can understand mixed chit-chat plus embedded administrative requests.
- Structured AI1 outputs: human reply plus runnable Python action scripts across messaging, channels, roles, webhooks, bans, and external API calls.
- AI2 reviewer to auto-approve safe scripts or escalate higher-impact actions (webhooks, bans, deletes, external calls) to a Telegram bot with human-in-the-loop controls.
- Restricted Python executor without filesystem access, using only approved Discord helper functions and explicit built-ins; raw Discord client/guild handles are still exposed to AI1 for advanced flows.
- Rolling one-hour per-admin memory for dialogue plus a recent action log to support reversibility and context-aware replies.

## Configuration
Create a `config.json` file alongside `main.py` using the template below. Secrets are never committed and must be provided at runtime.

```json
{
  "discord_token": "your-discord-token",
  "anthropic_key": "your-anthropic-key",
  "telegram_token": "your-telegram-token",
  "guild_id": 1443908368539451415,
  "admins": [
    783029509061476403,
    1039618113852952577,
    1361732484093575328,
    1447673330269163752
  ]
}
```

You can copy `config.example.json` and fill in your real values.

## Running the bot
Install dependencies and start the bot (Python 3.11+ recommended):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The bot will connect to Discord and start the Telegram escalation bridge. When AI2 flags a script as risky or unclear, the Telegram bot sends a summary, risks, and full code snapshot with approval buttons. No flagged script will run without explicit approval.

## How AI1 → AI2 → Human flow works
1. **AI1 conversation**: AI1 receives the admin message plus one-hour conversational memory and recent actions. It returns JSON with a human-facing reply and optional Python scripts implementing the requested actions—even complex sequences like channel orchestration or webhook/API wiring.
2. **AI2 review**: AI2 heuristically inspects each script for risky patterns (external calls, timed execution, multi-user impact, bans/kicks/deletes/webhooks, or large size). Safe scripts run immediately; risky ones are escalated.
3. **Telegram approval**: Escalated scripts are sent to the configured Telegram chat with summary, risks, and a “View Full Code” button. Execution remains frozen until approved.
4. **Execution sandbox**: Approved scripts run in a constrained executor exposing rich Discord helpers (`send_message`, `send_dm`, `create_role`, `assign_role`, `remove_role`, `create_text_channel`, `create_voice_channel`, `delete_channel`, `set_channel_permissions`, `ban_member`, `kick_member`, `create_webhook`, `send_webhook`, `http_get`, `http_post`, `fetch_history`) plus raw client/guild handles—still with no filesystem access or secret exposure.

## Development notes
- Imports are kept simple—no try/except guards around them.
- Extend the helper map in `bot/helpers.py` to expose more controlled capabilities to AI1.
- The rolling memory in `bot/memory.py` can be tuned to adjust horizon or action history size.
