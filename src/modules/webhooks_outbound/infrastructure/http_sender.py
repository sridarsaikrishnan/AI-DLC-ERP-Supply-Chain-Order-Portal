"""Real `WebhookSender` — POSTs to the reseller's endpoint over HTTP."""

from __future__ import annotations

import httpx

from ..application.ports import WebhookSendResult


class HttpWebhookSender:
    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._timeout = timeout_seconds

    def send(self, url: str, headers: dict[str, str], body: bytes) -> WebhookSendResult:
        try:
            response = httpx.post(url, headers=headers, content=body, timeout=self._timeout)
        except httpx.HTTPError as exc:
            return WebhookSendResult(success=False, status_code=None, error=str(exc))
        if 200 <= response.status_code < 300:
            return WebhookSendResult(success=True, status_code=response.status_code, error=None)
        return WebhookSendResult(success=False, status_code=response.status_code, error=response.text[:200])
