# Odoo inbound webhook setup (shared-secret-in-path)

How to make a local (or real) Odoo instance push sale-order status changes to this
platform, so updates show up without waiting for the reconciliation sweeper's next pass.

## Why this looks different from a normal signed webhook

ERPNext has native, signable webhooks, so `POST /erp/webhook/{connection_id}` with an
HMAC signature in the `x-erp-signature` header is enough for it. **Odoo doesn't** —
Community edition's Automation Rules can trigger a "Execute Python Code" server action,
but that action can't set arbitrary request headers or compute an HMAC over a payload in
a way that's simple to set up per-instance. So for Odoo, the platform accepts a second
form of the endpoint where the secret travels **in the URL path** instead of a header:

```
POST /erp/webhook/{connection_id}/{webhook_secret}
```

The tradeoff, explicitly: that secret ends up sitting in plain text inside the Automation
Rule's Python code (visible to any Odoo admin) and in any HTTP access logs along the way
— a materially weaker channel than a signed header. Two things bound that risk:
- **It's a dedicated secret** (`ErpConnection.webhook_secret_ref`), never the same
  credential used to log into Odoo (`secret_ref`). Leaking it lets someone push fake
  status updates for that one connection; it does **not** grant ERP login access.
- **It's not load-bearing.** The reconciliation sweeper (item C, `ReconcileScheduler`)
  polls every connection on a schedule regardless of whether the webhook is configured
  at all. A leaked or broken webhook secret degrades latency (you fall back to polling
  cadence), not correctness.

## 1. Create the webhook secret (Secrets Manager / floci locally)

Pick a random secret per connection — do **not** reuse the connection's ERP login secret.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```bash
aws --endpoint-url=http://localhost:4566 --region us-east-1 secretsmanager create-secret \
  --name "local:odoo-webhook-<connection_id>" \
  --secret-string "<the random value from above>"
```

## 2. Point the connection at it

There's no admin API for this yet (connections are still seeded directly, e.g.
`scripts/seed_demo.py`) — set `webhook_secret_ref` on the `erp_connections` row:

```sql
UPDATE erp_connections
SET webhook_secret_ref = 'local:odoo-webhook-<connection_id>'
WHERE connection_id = '<connection_id>';
```

## 3. Configure the Odoo Automation Rule

1. Enable developer mode: **Settings → General Settings**, scroll down, **Activate the
   developer mode**.
2. **Settings → Technical → Automation → Automation Rules → New**.
3. **Model**: `Sales Order`.
4. **Trigger**: `On Update`. **Trigger Fields**: `state` — so it fires on status changes
   only, not every edit.
5. **Action To Do**: `Execute Python Code`, with:

```python
import requests

payload = {
    "erp_order_id": record.name,
    "state": record.state,
    "invoice_status": record.invoice_status,
    "event_id": f"{record.id}_{record.write_date}",  # dedup key — see note below
}
requests.post(
    "http://localhost:8000/erp/webhook/<connection_id>/<webhook_secret>",
    json=payload,
    timeout=5,
)
```

Replace `<connection_id>` and `<webhook_secret>` with the real values (the webhook
secret from step 1, in plain text — see the tradeoff note above). Once item F adds a
docker-compose `app` service, the URL becomes `http://app:8000/...` (Odoo's container
resolving the API by its compose service name) instead of `localhost`.

`event_id` doubles as the dedup key (`processed_events`/`InMemoryDedupStore`) — it only
needs to be unique per actual status change on that record, which `write_date` gives you
without needing a UUID generator in Odoo's sandboxed code environment.

## What this endpoint expects

Matches `erp_webhook_shared_secret` in `src/api/http/webhooks.py`:

| JSON field | Required | Meaning |
|---|---|---|
| `erp_order_id` (or `name`) | yes | Odoo's `sale.order.name`, e.g. `S00042` — used for reverse-routing attribution |
| `state` (or `status`) | yes | Odoo's native lifecycle state (`draft`, `sale`, `done`, `cancel`, …) |
| `invoice_status` | no | feeds `map_native_status` for finer-grained transitions |
| `event_id` | yes (for dedup) | any string unique per delivery; a redelivery with the same value is silently deduped |

## Verifying it worked

```bash
curl -i -X POST "http://localhost:8000/erp/webhook/<connection_id>/<webhook_secret>" \
  -H "Content-Type: application/json" \
  -d '{"erp_order_id":"S00042","state":"sale","event_id":"manual-test-1"}'
```
`200` = accepted (or accepted-but-no-transition / duplicate — still 200). `401` = wrong
secret. `202` = accepted but unattributable (no order known for that `erp_order_id` yet —
expected if you test before placing a matching order).

## Status: code path verified, Odoo UI click-through not

`tests/integration/test_odoo_webhook_shared_secret.py` proves the receiving side end to
end against real Postgres + floci Secrets Manager: correct secret is accepted and updates
the order, wrong secret is rejected with `401`, using exactly the payload shape above.
What's **not** verified this session is actually clicking through Odoo's Automation Rule
UI on a live instance — the steps above follow Odoo's documented Automation Rules /
Server Action capabilities, but nobody has confirmed the `requests` import is available
in this specific Odoo 17 Community build's sandboxed `safe_eval` environment. If it's
blocked there, the fallback is a small custom Odoo module (an `ir.actions.server` binding
with unrestricted Python) — out of scope here.
