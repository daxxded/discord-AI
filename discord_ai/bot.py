"""High-level coordinator for the Discord AI assistant."""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .audit_log import ActionRecord, AuditLog
from .config import BotConfig
from .executor import AIExecutor
from .memory import AdminMemory


@dataclass
class BotContext:
    payload: Dict[str, Any]
    actions: AuditLog
    memory: AdminMemory
    protected_channel_id: int = 1444077226365816864

    def fetch_and_summarize(self, limit: int = 20) -> str:
        messages = self.payload.get("messages", [])[-limit:]
        summary = "; ".join(msg.get("content", "") for msg in messages)
        return f"Summary of last {len(messages)} messages: {summary}" if summary else "No messages to summarize."

    def create_role(self, name: str) -> Dict[str, Any]:
        role = {"name": name, "id": random.randint(10_000, 99_999)}
        self.actions.write(
            ActionRecord(
                action="create_role",
                status="success",
                actor="AI1",
                details={"role": role},
            )
        )
        return role

    def send_message(self, content: str) -> None:
        self.actions.write(
            ActionRecord(
                action="send_message",
                status="success",
                actor="AI1",
                details={"content": content},
            )
        )

    def send_random_text_to_channels(self, count: int, text: str) -> None:
        channels: List[int] = self.payload.get("channels", [])
        random.shuffle(channels)
        selected = channels[:count]
        for channel_id in selected:
            self.actions.write(
                ActionRecord(
                    action="send_message",
                    status="success",
                    actor="AI1",
                    details={"channel_id": channel_id, "content": text},
                )
            )

    def dm_user(self, user_id: int, text: str) -> None:
        self.actions.write(
            ActionRecord(
                action="dm_user",
                status="success",
                actor="AI1",
                details={"user_id": user_id, "content": text},
            )
        )

    def schedule_message(
        self,
        channel_id: int,
        content: str,
        delay_seconds: float = 3.0,
        repeat: bool = False,
        interval_seconds: float = 3.0,
    ) -> None:
        def _send():
            self.actions.write(
                ActionRecord(
                    action="scheduled_send_message",
                    status="success",
                    actor="AI1",
                    details={"channel_id": channel_id, "content": content, "delay_seconds": delay_seconds},
                )
            )
            if repeat:
                timer = threading.Timer(interval_seconds, _send)
                timer.daemon = True
                timer.start()

        timer = threading.Timer(delay_seconds, _send)
        timer.daemon = True
        timer.start()

    def delete_channel(self, channel_id: int) -> None:
        if str(channel_id) == str(self.protected_channel_id):
            raise ValueError("Deletion of protected channel 1444077226365816864 is forbidden.")
        self.actions.write(
            ActionRecord(
                action="delete_channel",
                status="success",
                actor="AI1",
                details={"channel_id": channel_id},
            )
        )


class DiscordAIBot:
    """Bot orchestrator exposing rich behaviors and auditability."""

    def __init__(self, config: BotConfig, audit_log: Optional[AuditLog] = None):
        self.config = config
        self.audit_log = audit_log or AuditLog()
        self.memory = AdminMemory()
        self.executor = AIExecutor(self.audit_log)

    def handle_request(self, admin_id: int, request: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        self.memory.remember(admin_id, request)

        if admin_id in self.config.non_admins:
            self.audit_log.write(
                ActionRecord(
                    action="handle_request_denied",
                    status="rejected",
                    actor="AI1",
                    details={"admin_id": admin_id, "request": request, "reason": "non-admin user"},
                )
            )
            return {
                "result": None,
                "plan": None,
                "memory": self.memory.recall(admin_id),
                "recent_actions": [record.__dict__ for record in self.audit_log.tail(5)],
                "message": "You can chat but cannot execute administrative actions.",
            }

        if admin_id not in self.config.admins:
            self.audit_log.write(
                ActionRecord(
                    action="handle_request_denied",
                    status="rejected",
                    actor="AI1",
                    details={"admin_id": admin_id, "request": request, "reason": "unknown user"},
                )
            )
            raise PermissionError("User is not authorized to run AI actions.")

        plan = self.executor.build_plan(request)
        context = BotContext(payload=payload, actions=self.audit_log, memory=self.memory)
        sandbox = {"context": context}
        result = self.executor.execute(plan, sandbox)
        self.audit_log.write(
            ActionRecord(
                action="handle_request",
                status="success",
                actor="AI1",
                details={"admin_id": admin_id, "request": request},
            )
        )
        return {
            "result": result,
            "plan": plan.description,
            "memory": self.memory.recall(admin_id),
            "recent_actions": [record.__dict__ for record in self.audit_log.tail(5)],
        }

    def summarize_and_create_role(self, channel_id: int, role_name: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Explicit helper for the 'grab last 20 messages, summarize, and create a role' flow."""
        context = BotContext(payload={"messages": messages, "role_name": role_name}, actions=self.audit_log, memory=self.memory)
        sandbox = {"context": context}
        plan = self.executor.build_plan("Summarize recent messages and create a role")
        result = self.executor.execute(plan, sandbox)
        return result
