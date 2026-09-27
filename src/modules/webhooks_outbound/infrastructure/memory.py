"""In-memory outbound-webhook repositories (tests + memory profile)."""

from __future__ import annotations

from src.shared.types import TenantId, WebhookEndpointId

from ..domain.models import WebhookDelivery, WebhookEndpoint


class InMemoryWebhookEndpointRepository:
    def __init__(self) -> None:
        self._by_id: dict[WebhookEndpointId, WebhookEndpoint] = {}

    def add(self, endpoint: WebhookEndpoint) -> None:
        self._by_id[endpoint.endpoint_id] = endpoint

    def get(self, endpoint_id: WebhookEndpointId) -> WebhookEndpoint | None:
        return self._by_id.get(endpoint_id)

    def update(self, endpoint: WebhookEndpoint) -> None:
        self._by_id[endpoint.endpoint_id] = endpoint

    def list_by_tenant(self, tenant_id: TenantId) -> list[WebhookEndpoint]:
        return [e for e in self._by_id.values() if e.tenant_id == tenant_id]


class InMemoryWebhookDeliveryRepository:
    def __init__(self) -> None:
        self._by_key: dict[tuple[WebhookEndpointId, str], WebhookDelivery] = {}

    def find(self, endpoint_id: WebhookEndpointId, event_id: str) -> WebhookDelivery | None:
        return self._by_key.get((endpoint_id, event_id))

    def upsert(self, delivery: WebhookDelivery) -> None:
        self._by_key[(delivery.endpoint_id, delivery.event_id)] = delivery

    def list_by_tenant(self, tenant_id: TenantId) -> list[WebhookDelivery]:
        return [d for d in self._by_key.values() if d.tenant_id == tenant_id]

    def list_all(self) -> list[WebhookDelivery]:
        return list(self._by_key.values())
