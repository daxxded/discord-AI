from __future__ import annotations

import asyncio
import logging
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Dict

log = logging.getLogger(__name__)

SAFE_BUILTINS = MappingProxyType({
    "len": len,
    "range": range,
    "min": min,
    "max": max,
    "sorted": sorted,
    "sum": sum,
    "enumerate": enumerate,
    "zip": zip,
    "any": any,
    "all": all,
    "abs": abs,
    "int": int,
    "str": str,
    "float": float,
    "bool": bool,
})


class ScriptExecutor:
    def __init__(self, helpers: Dict[str, Any]) -> None:
        self.helpers = helpers

    async def execute(self, script: str) -> Any:
        namespace: Dict[str, Any] = {**self.helpers}
        namespace["__builtins__"] = SAFE_BUILTINS

        compiled = compile(script, filename="<ai-script>", mode="exec")
        exec(compiled, namespace)

        coroutine = namespace.get("main")
        if coroutine is None:
            log.info("No main() coroutine exported; nothing to run")
            return None
        if not asyncio.iscoroutinefunction(coroutine):
            raise ValueError("main must be an async function")
        return await coroutine()
