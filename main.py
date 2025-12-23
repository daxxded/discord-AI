from __future__ import annotations

import asyncio
import logging
import uuid

import discord

from bot.ai2_reviewer import AI2Reviewer
from bot.ai_agent import AIConversationAgent
from bot.anthropic_client import AnthropicClient
from bot.config import BotConfig, find_config_path
from bot.event_logger import JSONEventLogger
from bot.executor import ScriptExecutor
from bot.helpers import DiscordHelpers
from bot.memory import RollingMemory
from bot.telegram_bridge import TelegramBridge

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class AutonomousDiscordBot(discord.Client):
    def __init__(self, config: BotConfig, telegram: TelegramBridge, events: JSONEventLogger) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)

        self.config = config
        self.memory = RollingMemory()
        self.ai_client = AnthropicClient(api_key=config.anthropic_key)
        self.agent = AIConversationAgent(self.ai_client, self.memory)
        self.ai2 = AI2Reviewer()
        self.telegram = telegram
        self.helpers = DiscordHelpers(self, config.guild_id)
        self.executor = ScriptExecutor(self.helpers.to_mapping())
        self.events = events

    async def on_ready(self) -> None:
        await self.events.log("discord_ready", user_id=getattr(self.user, "id", None), username=str(self.user))
        log.info("Logged in as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            await self.events.log(
                "message_ignored",
                reason="author_is_bot",
                author_id=message.author.id,
                channel_id=getattr(message.channel, "id", None),
            )
            return
        if message.guild and message.guild.id != self.config.guild_id:
            await self.events.log(
                "message_ignored",
                reason="different_guild",
                author_id=message.author.id,
                guild_id=message.guild.id,
            )
            return
        if message.author.id not in self.config.admins:
            await self.events.log(
                "message_ignored",
                reason="not_admin",
                author_id=message.author.id,
                channel_id=getattr(message.channel, "id", None),
            )
            return
        if message.guild and self.user not in message.mentions:
            await self.events.log(
                "message_ignored",
                reason="bot_not_mentioned",
                author_id=message.author.id,
                channel_id=message.channel.id,
            )
            return

        content = message.content.strip()
        self.memory.add_message(message.author.id, content)
        await self.events.log(
            "message_received",
            author_id=message.author.id,
            channel_id=getattr(message.channel, "id", None),
            guild_id=getattr(message.guild, "id", None),
            content=content,
        )

        plan = self.agent.respond(message.author.id, content)
        reply = plan.get("reply", "")
        actions = plan.get("actions", [])
        await self.events.log(
            "plan_generated",
            author_id=message.author.id,
            channel_id=getattr(message.channel, "id", None),
            reply=reply,
            actions=actions,
        )

        if reply:
            await message.channel.send(reply)
            await self.events.log(
                "reply_sent",
                channel_id=message.channel.id,
                reply=reply,
                author_id=message.author.id,
            )

        for script in actions:
            await self._handle_script(script, channel=message.channel, author=message.author)

    async def _handle_script(self, script: str, channel: discord.abc.Messageable, author: discord.User) -> None:
        review = self.ai2.review(script)
        request_id = uuid.uuid4().hex[:8]
        await self.events.log(
            "action_reviewed",
            request_id=request_id,
            summary=review.summary,
            risks=review.risks,
            escalate=review.escalate,
            approved=review.approved,
            author_id=author.id,
        )

        if review.escalate:
            allowed = await self.telegram.send_escalation(request_id, review.summary, review.risks, script)
            await self.events.log("action_escalated", request_id=request_id, allowed=allowed, author_id=author.id)
            if not allowed:
                await channel.send("Action was escalated and not approved.")
                return
        elif not review.approved:
            await channel.send("Action rejected by AI2 reviewer.")
            await self.events.log("action_rejected", request_id=request_id, author_id=author.id)
            return

        await channel.send(f"Executing action ({request_id})…")
        await self.events.log("action_started", request_id=request_id, author_id=author.id)
        try:
            await self.executor.execute(script)
            self.memory.add_action(f"{author.display_name}: {review.summary}")
            await channel.send(f"Completed action ({request_id}).")
            await self.events.log("action_completed", request_id=request_id, author_id=author.id)
        except Exception as exc:  # noqa: BLE001
            log.exception("Execution failed")
            await channel.send(f"Failed to execute script ({request_id}): {exc}")
            await self.events.log("action_failed", request_id=request_id, author_id=author.id, error=str(exc))


async def main() -> None:
    config_path = find_config_path().resolve()
    config = BotConfig.load(config_path)
    log_path = config_path.parent / "logs" / "bot_events.jsonl"
    event_logger = JSONEventLogger(log_path)
    await event_logger.log("startup", config_path=str(config_path))

    telegram = TelegramBridge(token=config.telegram_token)
    bot = AutonomousDiscordBot(config, telegram, event_logger)
    await telegram.start()
    await event_logger.log("telegram_started")

    try:
        await bot.start(config.discord_token)
    finally:
        await telegram.stop()
        await event_logger.log("shutdown")


if __name__ == "__main__":
    asyncio.run(main())
