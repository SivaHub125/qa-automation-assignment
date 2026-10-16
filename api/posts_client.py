"""Thin client for the JSONPlaceholder /posts resource, built on Playwright's APIRequestContext."""

import json
import logging

from playwright.sync_api import APIRequestContext

from api.api_result import ApiResult, timed_call

log = logging.getLogger("api.posts")


class PostsClient:
    path = "/posts"

    def __init__(self, request: APIRequestContext, timeout_ms: int = 60_000):
        self.request = request
        self.timeout_ms = timeout_ms

    def create(self, payload) -> ApiResult:
        """POST a JSON-serialisable payload (dict, list, ...)."""
        return self.create_raw(json.dumps(payload, ensure_ascii=False))

    def create_raw(self, body: str) -> ApiResult:
        """POST a raw string body exactly as given (used for malformed JSON)."""
        data = body.encode("utf-8")
        return timed_call(
            log, f"POST {self.path}",
            lambda: self.request.post(self.path, data=data, timeout=self.timeout_ms,
                                      headers={"Content-Type": "application/json; charset=UTF-8"}),
            request_bytes=len(data),
        )
