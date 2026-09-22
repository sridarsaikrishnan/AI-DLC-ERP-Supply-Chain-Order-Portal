# Odoo quickstart (scratch, for design exploration)

A throwaway Odoo instance to explore the ERP API and validate our integration assumptions (O-12 transport/version, O-14 status fields). This is **not** the U7 local stack — that full environment (Postgres + Floci + mock ERP + optional Odoo/ERPNext, one-command start) is produced during Code Generation.

## Run
```
docker compose up -d
```
Then open **http://localhost:8069**.

## First-run setup
1. Create a database: set a master password, DB name (e.g. `odoo_dev`), admin email + password.
2. Apps → install **Sales** (so the `sale.order` model exists).
3. Create an API key: avatar → **Preferences → Account Security → New API Key**.

## What maps to our platform's `ErpConnection`
| Odoo value | Our field |
|---|---|
| `http://localhost:8069` | `baseUrl` |
| DB name (e.g. `odoo_dev`) | connection config `database` |
| login + API key | `authConfig` (encrypted) |
| ERP type | `ODOO` |

## Notes
- Odoo's external API is **XML-RPC / JSON-RPC** (not REST) — test with those (see requirements FR-24, O-12).
- Order status spans multiple native fields: `sale.order.state` + `delivery_status` (+ `invoice_status`) — see the status mapping in `aidlc-docs/inception/application-design/canonical-model.md` (O-14).
- **Fictional data only** — never real customer/order data (FR-40).

## Stop / reset
```
docker compose down          # stop
docker compose down -v        # stop and delete data volumes
```
