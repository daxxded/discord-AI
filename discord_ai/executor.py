"""Generate, validate, and execute AI-authored scripts."""
from __future__ import annotations

import textwrap
import traceback
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Optional

from .audit_log import ActionRecord, AuditLog
from .feedback import FeedbackLooper


SAFE_GUARDS = (
    "import os",
    "os.remove",
    "os.rmdir",
    "shutil.rmtree",
    "subprocess",
    "open(\"/",
    "socket",
    "delete_channel",
    "1444077226365816864",  # block high-priority channel id from appearing in generated code
)


@dataclass
class ScriptPlan:
    description: str
    code: str
    safe: bool
    flagged_reason: Optional[str] = None


class AIExecutor:
    """Coordinates AI1 (creator) and AI2 (reviewer) with manual overrides."""

    def __init__(self, audit_log: AuditLog):
        self.audit_log = audit_log
        self.feedback = FeedbackLooper()

    def build_plan(self, request: str) -> ScriptPlan:
        """AI1 step: craft a Python snippet to satisfy the request."""
        code = textwrap.dedent(
            f"""
            # Auto-generated script for: {request}
            def run(context):
                # The context contains safe helpers like send_message, create_role, fetch_messages
                summary = context.fetch_and_summarize(limit=context.payload.get('summary_limit', 20))
                role = context.create_role(name=context.payload.get('role_name', 'auto-role'))
                context.send_message(summary)

                # Optional freedom actions
                context.send_random_text_to_channels(
                    count=3,
                    text=context.payload.get('random_text', 'Automated hello from AI'),
                )
                if context.payload.get('dm_user_id'):
                    context.dm_user(user_id=context.payload['dm_user_id'], text=context.payload.get('dm_text', summary))
                if context.payload.get('scheduled_messages'):
                    for entry in context.payload['scheduled_messages']:
                        context.schedule_message(
                            channel_id=entry.get('channel_id'),
                            content=entry.get('content', 'Scheduled hello'),
                            delay_seconds=entry.get('delay_seconds', 3),
                            repeat=entry.get('repeat', False),
                            interval_seconds=entry.get('interval_seconds', 3),
                        )
                return {{"summary": summary, "role": role}}
            """
        ).strip()

        safe, flagged_reason = self._ai2_review(code)
        return ScriptPlan(description=request, code=code, safe=safe, flagged_reason=flagged_reason)

    def execute(self, plan: ScriptPlan, sandbox: Dict[str, Any]) -> Dict[str, Any]:
        """Run the script with three feedback loops and full auditing."""
        if not plan.safe:
            self.audit_log.write(
                ActionRecord(
                    action="ai_script_rejected",
                    status="rejected",
                    actor="AI2",
                    details={"reason": plan.flagged_reason, "description": plan.description},
                )
            )
            raise PermissionError(plan.flagged_reason or "Script rejected by AI2")

        def _attempt(attempt: int, last_error: Optional[str]):
            local_env: Dict[str, Any] = {}
            global_env: Dict[str, Any] = {"__builtins__": MappingProxyType({}), **sandbox}
            exec(plan.code, global_env, local_env)  # noqa: S102 - intentional sandboxed exec
            if "run" not in local_env:
                raise RuntimeError("Generated script did not define run(context)")
            return local_env["run"](sandbox.get("context"))

        outcome = self.feedback.run(_attempt)
        record = ActionRecord(
            action="ai_script_execute",
            status="success" if outcome.result is not None else "failed",
            actor="AI1",
            details={"description": plan.description, "attempts": outcome.attempts},
            error=outcome.last_error,
        )
        self.audit_log.write(record)
        if outcome.result is None:
            raise RuntimeError(outcome.last_error or "Unknown execution failure")
        return outcome.result

    def _ai2_review(self, code: str) -> tuple[bool, Optional[str]]:
        """Simple static checks to flag dangerous patterns.

        Real deployment should swap this with a proper LLM-based reviewer.
        """
        lowered = code.lower()
        for guard in SAFE_GUARDS:
            if guard in lowered:
                return False, f"Script contains blocked pattern: {guard}"
        if len(code) > 5_000:
            return False, "Script too large and ambiguous"
        return True, None
