from __future__ import annotations

import asyncio
import logging
from typing import Iterable, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

log = logging.getLogger(__name__)


class TelegramBridge:
    def __init__(self, token: str, owner_chat_id: Optional[int] = None) -> None:
        self.token = token
        self.owner_chat_id = owner_chat_id
        self._application: Optional[Application] = None
        self._pending: dict[str, asyncio.Future[bool]] = {}
        self._scripts: dict[str, str] = {}

    async def start(self) -> None:
        self._application = Application.builder().token(self.token).build()
        self._application.add_handler(CallbackQueryHandler(self._on_decision))
        self._application.add_handler(CommandHandler("start", self._on_start))
        await self._application.initialize()
        await self._application.start()
        log.info("Telegram bridge started")

    async def stop(self) -> None:
        if not self._application:
            return
        await self._application.stop()
        await self._application.shutdown()

    async def send_escalation(self, request_id: str, summary: str, risks: Iterable[str], code: str) -> bool:
        if not self._application:
            raise RuntimeError("Telegram bridge is not started")

        chat_id = self.owner_chat_id or (await self._guess_owner())
        if chat_id is None:
            log.warning("No Telegram chat id available; rejecting by default")
            return False

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Approve (Once)", callback_data=f"approve:{request_id}"),
                    InlineKeyboardButton("⛔ Reject", callback_data=f"reject:{request_id}"),
                ],
                [InlineKeyboardButton("📄 View Full Code", callback_data=f"view:{request_id}")],
            ]
        )

        risks_list = "\n".join(f"• {risk}" for risk in risks) or "(none)"
        message = (
            "<b>AI2 Escalation</b>\n"
            f"<b>Summary:</b> {summary}\n\n"
            f"<b>Risks:</b>\n{risks_list}\n\n"
            "Pending approval before execution."
        )

        future: asyncio.Future[bool] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        self._scripts[request_id] = code

        await self._application.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )

        try:
            decision = await asyncio.wait_for(future, timeout=120)
            return decision
        except asyncio.TimeoutError:
            log.warning("Telegram approval timed out for %s", request_id)
            return False
        finally:
            self._pending.pop(request_id, None)
            self._scripts.pop(request_id, None)

    async def _on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat:
            await update.message.reply_text("Escalation bot ready.")

    async def _on_decision(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        data = query.data or ""
        action, _, request_id = data.partition(":")
        future = self._pending.get(request_id)
        if not future:
            await query.edit_message_text("No pending request.")
            return

        if action == "approve":
            future.set_result(True)
            await query.edit_message_text("Approved — executing once.")
        elif action == "reject":
            future.set_result(False)
            await query.edit_message_text("Rejected.")
        elif action == "view":
            code = self._scripts.get(request_id, "<no code available>")
            await query.edit_message_text(
                text=f"<b>Full Code</b>\n<pre>{self._escape(code)}</pre>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.edit_message_text("Unrecognized action.")

    async def _guess_owner(self) -> Optional[int]:
        if not self._application:
            return None
        updates = await self._application.bot.get_updates(limit=1)
        if updates and updates[0].message:
            return updates[0].message.chat_id
        return None

    def _escape(self, content: str) -> str:
        return content.replace("<", "&lt;").replace(">", "&gt;")
