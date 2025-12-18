from __future__ import annotations

import logging
from typing import Awaitable, Callable, Coroutine

import discord

log = logging.getLogger(__name__)


class DiscordHelpers:
    def __init__(self, bot: discord.Client, guild_id: int) -> None:
        self.bot = bot
        self.guild_id = guild_id

    async def send_message(self, channel_id: int, content: str) -> None:
        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            raise ValueError("Channel not found or not text-based")
        await channel.send(content)

    async def create_role(self, name: str, color: discord.Color | None = None) -> discord.Role:
        guild = self._guild
        return await guild.create_role(name=name, colour=color or discord.Color.random())

    async def assign_role(self, user_id: int, role_id: int) -> None:
        guild = self._guild
        member = guild.get_member(user_id)
        role = guild.get_role(role_id)
        if not member or not role:
            raise ValueError("Member or role not found")
        await member.add_roles(role, reason="AI1 action")

    async def fetch_history(self, channel_id: int, limit: int = 100):
        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            raise ValueError("Channel not found or not text-based")
        messages = []
        async for message in channel.history(limit=limit):
            messages.append({"author": message.author.id, "content": message.content})
        return messages

    @property
    def _guild(self) -> discord.Guild:
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            raise ValueError("Guild not available")
        return guild

    def to_mapping(self):
        return {
            "send_message": self.send_message,
            "create_role": self.create_role,
            "assign_role": self.assign_role,
            "fetch_history": self.fetch_history,
        }
