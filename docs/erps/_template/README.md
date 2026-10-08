# <ERP name>

Status: **not registered** / **live**. Adapter file: `src/modules/integration/erp/infrastructure/<erp>_adapter.py`.
If this page disagrees with that file or `status_mapping.py`, the code is right.

Copy this file when adding an ERP. Keep the headings. Fill the tables from the adapter, not from memory.

## What it is, as far as this platform is concerned

Which document in that ERP is "the sales order", and which API we call.

## How a connection is configured

| `ErpConnection` field | What it is for this ERP |
|---|---|
| `base_url` | |
| `credentials` | Non-secret bag. Name every key this adapter reads. |
| `secret_ref` | What the secret string actually is (password, token, …). |
| `webhook_secret_ref` | See [webhook.md](./webhook.md). |

## Authentication

How a call logs in. What a bad credential does (retry, or stop).

## How an order arrives

This product does not create the sales order. Say which record `fetch_partner_orders` reads, which id is the binding's `erp_customer_id`, and which product code becomes `product_key`. A line with no code is skipped.

## Status mapping

| Native fields | Canonical status |
|---|---|
| | `CANCELLED` / `CLOSED` / `CONFIRMED` / no transition |

## Shipments and invoices

Which documents `fetch_shipments` and `fetch_invoices` read, and which id is stable across polls.

## Known gaps

Quirks found against a real instance. If you learned it the hard way, it goes here.
