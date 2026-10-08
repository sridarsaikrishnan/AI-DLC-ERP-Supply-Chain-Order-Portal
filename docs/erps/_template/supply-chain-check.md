# Supply-chain check — <ERP name>

What a developer does in this ERP, once, to prove one sales order is followed all the way through.
Same headings for every ERP. Odoo is the filled-in copy: [../odoo/supply-chain-check.md](../odoo/supply-chain-check.md).

## Before you start

- The stack is up.
- Which connection row, which binding, and which customer id in this ERP that binding uses.
- Where to sign in: ERP UI, operator portal, reseller portal.

## One-time setup in the ERP

- The product code the adapter will treat as `product_key`.
- The webhook, if this ERP pushes status. Link [webhook.md](./webhook.md).
- Anything that must be installed before a delivery or an invoice can exist.

## Walk the order

Number the clicks. Each step names the customer, the document, and the button.
The customer on the document must be the binding's customer. A document for anyone else is invisible here.

1. Create the sales order (or this ERP's equivalent) and save it.
2. Confirm it.
3. Complete the delivery.
4. Post the customer invoice.

## What arrives as a webhook, and what is polled

| Step | Webhook | Poll |
|---|---|---|
| Document saved | | `fetch_partner_orders` |
| Confirmed | | `fetch_status` |
| Delivered | | `fetch_shipments` |
| Invoiced | | `fetch_invoices` |

A webhook is not how a new order is adopted. The poll does that.

## Where to look

- `erp_event_inbox.body` — raw request bytes, after the secret checks out.
- Operator order page — status, delivered quantity, invoiced quantity.
- Reseller notifications — only after a later event was actually delivered to an endpoint. Saving the order is not a notification.

## Done when

- The inbox has the raw POST for this document.
- The operator order shows confirmed, then delivered, then invoiced.
- A second poll does not increase the quantities.
