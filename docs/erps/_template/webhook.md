# <ERP name> inbound webhook

How this ERP pushes a status change to us. The poll still runs if this is not set up.
The walk that proves the whole flow is [supply-chain-check.md](./supply-chain-check.md).

## Why it looks like this

HMAC (`POST /erp/webhook/{connection_id}`, header `x-erp-signature`) when the ERP can sign the body.
Shared secret in the path (`POST /erp/webhook/{connection_id}/{webhook_secret}`) when it can only call a URL.
Say which one this ERP uses, and why.

## Secret

`webhook_secret_ref` on the connection. Never the login secret in `secret_ref`.

## What the ERP sends

The body is stored raw in `erp_event_inbox` before we read any field. Still list the fields the status mapper needs, because a body we cannot map does not move the order.

| Field | Required for a status change | Meaning |
|---|---|---|
| | | |

## Prove a row landed

From the machine running the API (not from inside the ERP's container):

```bash
curl -i -X POST "http://127.0.0.1:8000/erp/webhook/<connection_id>/<webhook_secret>" \
  -H "Content-Type: application/json" \
  -d '<a body this ERP would really send>'
```

`200` means the secret was accepted. `401` means it was not, and nothing was stored.
Then:

```sql
SELECT received_at, convert_from(body, 'UTF8')
FROM erp_event_inbox
WHERE connection_id = '<connection_id>'
ORDER BY received_at DESC
LIMIT 5;
```

The text in `body` must be the bytes you posted, not a rewritten payload.
