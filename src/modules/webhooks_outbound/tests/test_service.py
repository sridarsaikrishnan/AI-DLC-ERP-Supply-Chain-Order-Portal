from src.modules.webhooks_outbound.application.service import WebhookEndpointService
from src.modules.webhooks_outbound.infrastructure.memory import InMemoryWebhookEndpointRepository
from src.shared.secrets import EnvSecretStore
from src.shared.types import TenantId, WebhookEndpointId


def _service() -> WebhookEndpointService:
    return WebhookEndpointService(InMemoryWebhookEndpointRepository(), EnvSecretStore())


def test_register_returns_endpoint_and_raw_secret_once() -> None:
    service = _service()
    endpoint, raw_secret = service.register(
        tenant_id=TenantId("tnt_demo"), name="Procurement system", url="https://example.com/hooks", event_types=None
    )
    assert endpoint.tenant_id == TenantId("tnt_demo")
    assert endpoint.is_active is True
    assert raw_secret.startswith("whsec_")


def test_pause_and_resume_round_trip() -> None:
    service = _service()
    endpoint, _ = service.register(
        tenant_id=TenantId("tnt_demo"), name="Warehouse feed", url="https://example.com/wh", event_types=None
    )
    paused = service.pause(endpoint.endpoint_id, tenant_id=TenantId("tnt_demo"))
    assert paused.is_active is False
    resumed = service.resume(endpoint.endpoint_id, tenant_id=TenantId("tnt_demo"))
    assert resumed.is_active is True


def test_pause_unknown_endpoint_raises() -> None:
    service = _service()
    try:
        service.pause(WebhookEndpointId("whep_nope"), tenant_id=TenantId("tnt_demo"))
        assert False, "expected WebhookEndpointNotFound"
    except Exception as exc:
        assert "whep_nope" in str(exc)


def test_pause_wrong_tenant_raises_not_found() -> None:
    """A different tenant's endpoint ID must read as not-found, not as a permission
    error that would confirm the ID exists — fail-closed against IDOR."""
    service = _service()
    endpoint, _ = service.register(
        tenant_id=TenantId("tnt_demo"), name="Warehouse feed", url="https://example.com/wh", event_types=None
    )
    try:
        service.pause(endpoint.endpoint_id, tenant_id=TenantId("tnt_other"))
        assert False, "expected WebhookEndpointNotFound"
    except Exception as exc:
        assert str(endpoint.endpoint_id) in str(exc)
