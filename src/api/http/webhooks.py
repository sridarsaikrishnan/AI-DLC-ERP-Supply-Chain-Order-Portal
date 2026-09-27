"""Inbound ERP webhook HTTP routes — the transport in front of webhooks_inbound.

Two routes, two auth schemes (target-architecture.md 5a, infrastructure-design.md):
- `POST /erp/webhook/{connection_id}` — HMAC signature in the `x-erp-signature` header.
  ERPNext has native webhooks and can compute this.
- `POST /erp/webhook/{connection_id}/{webhook_secret}` — shared-secret-in-path. Odoo
  Automation Rules can only POST to a URL; they can't set custom headers or sign a body.
  The secret itself IS the URL segment, verified with a constant-time comparison against
  the connection's `webhook_secret_ref` (never the ERP login secret — see
  `ErpConnection.webhook_secret_ref`). This trades a weaker channel (the secret ends up
  in the Odoo Automation Rule config and in any access logs) for the only integration
  point Odoo Community actually offers; that's why it's a separate secret from the ERP
  login credential, and why the reconcile sweeper (item C) exists as a safety net
  regardless of whether the webhook fires.

Both routes are thin: parse the ERP-specific body into the transport-agnostic
InboundWebhook, hand it to the ingress service, map the outcome to an HTTP status.
Attribution + dedupe happen in the service; only auth material differs here.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Request, Response

from src.modules.webhooks_inbound.application.ingress import InboundWebhook, IngressOutcome, WebhookAuthMode
from src.shared.types import ConnectionId

router = APIRouter()

_STATUS = {
    IngressOutcome.ACCEPTED: 200,
    IngressOutcome.NO_TRANSITION: 200,
    IngressOutcome.DUPLICATE: 200,
    IngressOutcome.UNATTRIBUTABLE: 202,  # accepted-but-ignored (not an order we track)
    IngressOutcome.UNAUTHORIZED: 401,
}


def _parse_body(raw: bytes) -> dict:
    try:
        return json.loads(raw or b"{}")
    except ValueError:
        return {}


async def _dispatch(request: Request, webhook: InboundWebhook) -> Response:
    container = request.app.state.container
    outcome = container.ingress.handle(webhook)
    container.drain()  # memory profile: drain in-process; postgres: no-op, worker drains
    return Response(status_code=_STATUS.get(outcome, 200), content=outcome.value, media_type="text/plain")


@router.post("/erp/webhook/{connection_id}")
async def erp_webhook_hmac(connection_id: str, request: Request) -> Response:
    """ERPNext (or any ERP that can sign): HMAC over the raw body."""
    raw = await request.body()
    body = _parse_body(raw)
    webhook = InboundWebhook(
        connection_id=ConnectionId(connection_id),
        erp_type=str(body.get("erp_type", "ERP_NEXT")),
        erp_order_id=str(body.get("erp_order_id") or body.get("name") or ""),
        native_status=str(body.get("state") or body.get("status") or ""),
        event_ref=request.headers.get("x-erp-delivery-id", "") or str(body.get("event_id", "")),
        raw_body=raw,
        signature=request.headers.get("x-erp-signature", ""),
        auth_mode=WebhookAuthMode.HMAC,
        invoice_status=body.get("invoice_status"),
    )
    return await _dispatch(request, webhook)


@router.post("/erp/webhook/{connection_id}/{webhook_secret}")
async def erp_webhook_shared_secret(connection_id: str, webhook_secret: str, request: Request) -> Response:
    """Odoo: the secret is the URL segment itself, not a header — see module docstring."""
    raw = await request.body()
    body = _parse_body(raw)
    webhook = InboundWebhook(
        connection_id=ConnectionId(connection_id),
        erp_type=str(body.get("erp_type", "ODOO")),
        erp_order_id=str(body.get("erp_order_id") or body.get("name") or ""),
        native_status=str(body.get("state") or body.get("status") or ""),
        event_ref=str(body.get("event_id", "")),
        raw_body=raw,
        signature=webhook_secret,
        auth_mode=WebhookAuthMode.SHARED_SECRET,
        invoice_status=body.get("invoice_status"),
    )
    return await _dispatch(request, webhook)
