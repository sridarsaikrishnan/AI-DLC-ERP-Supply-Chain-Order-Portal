"""Ports for outbound webhook registration + dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.shared.types import TenantId, WebhookEndpointId

    from ..domain.models import WebhookDelivery, WebhookEndpoint


class WebhookEndpointRepository(Protocol):
    def add(self, endpoint: WebhookEndpoint) -> None: ...
    def get(self, endpoint_id: WebhookEndpointId) -> WebhookEndpoint | None: ...
    def update(self, endpoint: WebhookEndpoint) -> None: ...
    def list_by_tenant(self, tenant_id: TenantId) -> list[WebhookEndpoint]: ...


class WebhookDeliveryRepository(Protocol):
    def find(self, endpoint_id: WebhookEndpointId, event_id: str) -> WebhookDelivery | None: ...
    def upsert(self, delivery: WebhookDelivery) -> None: ...
    def list_by_tenant(self, tenant_id: TenantId) -> list[WebhookDelivery]: ...
    def list_all(self) -> list[WebhookDelivery]: ...


@dataclass
class WebhookSendResult:
    success: bool
    status_code: int | None
    error: str | None


class WebhookSender(Protocol):
    def send(self, url: str, headers: dict[str, str], body: bytes) -> WebhookSendResult: ...
