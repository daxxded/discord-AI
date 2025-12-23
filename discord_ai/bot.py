"""High-level coordinator for the Discord AI assistant."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .audit_log import ActionRecord, AuditLog
from .executor import AIExecutor
from .memory import AdminMemory


@dataclass
class BotContext:
    payload: Dict[str, Any]
    actions: AuditLog
    memory: AdminMemory

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


class DiscordAIBot:
    """Bot orchestrator exposing rich behaviors and auditability."""

    def __init__(self, audit_log: Optional[AuditLog] = None):
        self.audit_log = audit_log or AuditLog()
        self.memory = AdminMemory()
        self.executor = AIExecutor(self.audit_log)

    def handle_request(self, admin_id: int, request: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        self.memory.remember(admin_id, request)
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
