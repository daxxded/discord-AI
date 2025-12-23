from __future__ import annotations

import asyncio
import json
import logging
import uuid

import discord

from bot.ai2_reviewer import AI2Reviewer
from bot.ai_agent import AIConversationAgent
from bot.anthropic_client import AnthropicClient
from bot.config import BotConfig, find_config_path
from bot.executor import ScriptExecutor
from bot.helpers import DiscordHelpers
from bot.memory import RollingMemory
from bot.telegram_bridge import TelegramBridge

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class AutonomousDiscordBot(discord.Client):
    def __init__(self, config: BotConfig, telegram: TelegramBridge) -> None:
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

    async def on_ready(self) -> None:
        log.info("Logged in as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild and message.guild.id != self.config.guild_id:
            return
        if message.author.id not in self.config.admins:
            return

        content = message.content.strip()
        self.memory.add_message(message.author.id, content)

        plan = self.agent.respond(message.author.id, content)
        reply = plan.get("reply", "")
        actions = plan.get("actions", [])

        if reply:
            await message.channel.send(reply)

        for script in actions:
            await self._handle_script(script, channel=message.channel, author=message.author)

    async def _handle_script(self, script: str, channel: discord.abc.Messageable, author: discord.User) -> None:
        review = self.ai2.review(script)
        request_id = uuid.uuid4().hex[:8]
        if review.escalate:
            allowed = await self.telegram.send_escalation(request_id, review.summary, review.risks, script)
            if not allowed:
                await channel.send("Action was escalated and not approved.")
                return
        elif not review.approved:
            await channel.send("Action rejected by AI2 reviewer.")
            return

        await channel.send(f"Executing action ({request_id})…")
        try:
            await self.executor.execute(script)
            self.memory.add_action(f"{author.display_name}: {review.summary}")
            await channel.send(f"Completed action ({request_id}).")
        except Exception as exc:  # noqa: BLE001
            log.exception("Execution failed")
            await channel.send(f"Failed to execute script ({request_id}): {exc}")


async def main() -> None:
    config_path = find_config_path()
    config = BotConfig.load(config_path)
    telegram = TelegramBridge(token=config.telegram_token)

    bot = AutonomousDiscordBot(config, telegram)
    await telegram.start()

    try:
        await bot.start(config.discord_token)
    finally:
        await telegram.stop()


if __name__ == "__main__":
    asyncio.run(main())
