"""The response of an API call, packed for assertions (shared by all API clients)."""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

from playwright.sync_api import APIResponse


@dataclass
class ApiResult:
    status: int
    text: str
    elapsed_ms: int
    request_bytes: int

    @cached_property
    def json(self):
        try:
            return json.loads(self.text)
        except ValueError:
            return None

    @property
    def exposes_stack_trace(self) -> bool:
        return "node_modules" in self.text or "\n    at " in self.text or "Traceback" in self.text


def timed_call(log: logging.Logger, label: str, send: Callable[[], APIResponse], request_bytes: int = 0) -> ApiResult:
    """Send a request, time it, pack the response and log one summary line."""
    started = time.perf_counter()
    response = send()
    result = ApiResult(
        status=response.status,
        text=response.text(),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        request_bytes=request_bytes,
    )
    log.info("%s | request %d bytes | HTTP %d in %d ms | response: %s", label, request_bytes,
             result.status, result.elapsed_ms, result.text[:300].replace("\n", " "))
    return result
