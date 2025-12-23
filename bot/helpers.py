from __future__ import annotations

import logging
from typing import Dict, Optional

import discord
import aiohttp

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

    async def send_dm(self, user_id: int, content: str) -> None:
        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        if not user:
            raise ValueError("User not found")
        await user.send(content)

    async def create_role(
        self,
        name: str,
        color: Optional[str | int | discord.Color] = None,
        permissions: Optional[discord.Permissions] = None,
    ) -> discord.Role:
        guild = self._guild
        colour = self._resolve_color(color)
        perms = permissions or discord.Permissions.all()
        return await guild.create_role(name=name, colour=colour, permissions=perms)

    async def assign_role(self, user_id: int, role_id: int) -> None:
        guild = self._guild
        member = guild.get_member(user_id)
        role = guild.get_role(role_id)
        if not member or not role:
            raise ValueError("Member or role not found")
        await member.add_roles(role, reason="AI1 action")

    async def remove_role(self, user_id: int, role_id: int) -> None:
        guild = self._guild
        member = guild.get_member(user_id)
        role = guild.get_role(role_id)
        if not member or not role:
            raise ValueError("Member or role not found")
        await member.remove_roles(role, reason="AI1 action")

    async def create_text_channel(self, name: str, category_id: Optional[int] = None) -> discord.TextChannel:
        guild = self._guild
        category = guild.get_channel(category_id) if category_id else None
        return await guild.create_text_channel(name=name, category=category)

    async def create_voice_channel(self, name: str, category_id: Optional[int] = None) -> discord.VoiceChannel:
        guild = self._guild
        category = guild.get_channel(category_id) if category_id else None
        return await guild.create_voice_channel(name=name, category=category)

    async def delete_channel(self, channel_id: int) -> None:
        channel = self.bot.get_channel(channel_id)
        if not channel:
            raise ValueError("Channel not found")
        await channel.delete(reason="AI1 action")

    async def set_channel_permissions(
        self,
        channel_id: int,
        target_id: int,
        overwrite: Dict[str, bool],
        is_role: bool = True,
    ) -> None:
        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel)):
            raise ValueError("Channel not found")
        guild = self._guild
        target = guild.get_role(target_id) if is_role else guild.get_member(target_id)
        if not target:
            raise ValueError("Permission target not found")
        perms = discord.PermissionOverwrite(**overwrite)
        await channel.set_permissions(target, overwrite=perms, reason="AI1 action")

    async def ban_member(self, user_id: int, reason: str | None = None, delete_message_days: int = 0) -> None:
        guild = self._guild
        member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        await guild.ban(member, reason=reason, delete_message_days=delete_message_days)

    async def kick_member(self, user_id: int, reason: str | None = None) -> None:
        guild = self._guild
        member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        await guild.kick(member, reason=reason)

    async def create_webhook(self, channel_id: int, name: str) -> str:
        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            raise ValueError("Channel not found or not text-based")
        webhook = await channel.create_webhook(name=name)
        return webhook.url

    async def send_webhook(
        self,
        webhook_url: str,
        content: str,
        username: str | None = None,
        avatar_url: str | None = None,
    ) -> None:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            await webhook.send(content, username=username, avatar_url=avatar_url)

    async def http_get(self, url: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                try:
                    return await resp.json()
                except Exception:  # noqa: BLE001
                    return {"status": resp.status, "text": await resp.text()}

    async def http_post(self, url: str, json_payload: Optional[dict] = None) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json_payload) as resp:
                resp.raise_for_status()
                try:
                    return await resp.json()
                except Exception:  # noqa: BLE001
                    return {"status": resp.status, "text": await resp.text()}

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
            "send_dm": self.send_dm,
            "create_role": self.create_role,
            "assign_role": self.assign_role,
            "remove_role": self.remove_role,
            "create_text_channel": self.create_text_channel,
            "create_voice_channel": self.create_voice_channel,
            "delete_channel": self.delete_channel,
            "set_channel_permissions": self.set_channel_permissions,
            "ban_member": self.ban_member,
            "kick_member": self.kick_member,
            "create_webhook": self.create_webhook,
            "send_webhook": self.send_webhook,
            "http_get": self.http_get,
            "http_post": self.http_post,
            "fetch_history": self.fetch_history,
            "discord_client": self.bot,
            "guild": self._guild,
        }

    def _resolve_color(self, color: Optional[str | int | discord.Color]) -> discord.Color:
        if color is None:
            return discord.Color.random()
        if isinstance(color, discord.Color):
            return color
        try:
            if isinstance(color, str):
                return discord.Color.from_str(color)
            return discord.Color(color)
        except Exception:  # noqa: BLE001
            log.warning("Falling back to random color; invalid input: %s", color)
            return discord.Color.random()
