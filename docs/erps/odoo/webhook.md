# Odoo inbound webhook (shared secret in the path)

How a local Odoo pushes a sales-order status change so we do not wait for the next poll.
The click-by-click proof of quotation → delivery → invoice is [supply-chain-check.md](./supply-chain-check.md).

## Why this looks different from a signed webhook

An ERP that can sign a body uses `POST /erp/webhook/{connection_id}` with `x-erp-signature`.
Odoo Community Automation Rules can run Python, and they cannot set that header or compute an HMAC.
Odoo therefore uses a second route, where the secret is a path segment:

```
POST /erp/webhook/{connection_id}/{webhook_secret}
```

That secret sits in the Automation Rule, visible to any Odoo admin, and in access logs.
Two bounds:

- It is `webhook_secret_ref`, never the login secret in `secret_ref`. Leaking it lets someone post a fake status for this connection. It does not log them into Odoo.
- The poll runs anyway. A broken webhook makes status late, not wrong. Deliveries and invoice lines are read by the poll even when the webhook works.

## Local values

`scripts/seed_demo.py` already stores these. You do not create a new secret for the demo connection.

| | |
|---|---|
| Connection | `conn_odoo_local` |
| Secret ref | `local:odoo-webhook-demo-secret` |
| Secret value | `odoo-webhook-demo` |
| URL the Odoo container must call | `http://host.docker.internal:8000/erp/webhook/conn_odoo_local/odoo-webhook-demo` |

`localhost` inside the Odoo container is Odoo, not the API. `host.docker.internal` is the machine running the API. A curl from that machine uses `http://127.0.0.1:8000/...` instead.

## Automation Rule

1. **Settings → Activate the developer mode.**
2. **Settings → Technical → Automation → Automation Rules → New.**
3. **Model:** Sales Order (`sale.order`).
4. **Trigger:** On Update. **Trigger Fields:** `state`.
5. **Action:** Execute Python Code:

```python
import requests

payload = {
    "erp_order_id": record.name,
    "state": record.state,
    "invoice_status": record.invoice_status,
    "event_id": f"{record.id}_{record.write_date}",
}
requests.post(
    "http://host.docker.internal:8000/erp/webhook/conn_odoo_local/odoo-webhook-demo",
    json=payload,
    timeout=5,
)
```

`event_id` is the dedup key. The same value posted again does not move the order a second time. The raw body is still appended to `erp_event_inbox` each time the secret checks out.

Odoo 17 often blocks `import requests` in this sandbox. If the rule errors, status still arrives on the poll, and the inbox stays empty until a POST succeeds. The curl in [supply-chain-check.md](./supply-chain-check.md) is how you put a raw body in the inbox without the rule.

## Fields the status mapper reads

The inbox stores the body before these names matter. Mapping uses them afterward.

| JSON field | Required to move the order | Meaning |
|---|---|---|
| `erp_order_id` or `name` | yes | `sale.order.name`, such as `S00042` |
| `state` | yes | `draft`, `sent`, `sale`, `done`, `cancel`, … |
| `invoice_status` | no | `invoiced` closes the order |
| `event_id` | for dedup | unique per change; a repeat is not applied again |

`cancel` → `CANCELLED`. `invoice_status=invoiced` → `CLOSED`. `sale` or `done` → `CONFIRMED`. Anything else, including `draft`, is kept in the inbox and does not change status.

## Prove a row landed

```bash
curl -i -X POST "http://127.0.0.1:8000/erp/webhook/conn_odoo_local/odoo-webhook-demo" \
  -H "Content-Type: application/json" \
  -d '{"erp_order_id":"S00042","state":"sale","invoice_status":"no","event_id":"manual-1"}'
```

`200` — secret accepted (applied, no transition, or duplicate are all `200`).
`401` — wrong secret, nothing stored.
`202` — secret accepted, no adopted order with that number yet. The raw body is still stored.

```sql
SELECT received_at, convert_from(body, 'UTF8')
FROM erp_event_inbox
WHERE connection_id = 'conn_odoo_local'
ORDER BY received_at DESC
LIMIT 5;
```
