"""Client for the EMI Insights app's own JSON API (/api/emi, /api/schedule)."""

import logging

from playwright.sync_api import APIRequestContext

from api.api_result import ApiResult, timed_call

log = logging.getLogger("api.emi_app")


class EmiAppClient:
    def __init__(self, request: APIRequestContext):
        self.request = request

    def get(self, path: str, **params) -> ApiResult:
        query = {k: str(v) for k, v in params.items()}
        return timed_call(log, f"GET {path} {query}", lambda: self.request.get(path, params=query))

    def emi(self, **params) -> ApiResult:
        return self.get("/api/emi", **params)

    def schedule(self, **params) -> ApiResult:
        return self.get("/api/schedule", **params)
