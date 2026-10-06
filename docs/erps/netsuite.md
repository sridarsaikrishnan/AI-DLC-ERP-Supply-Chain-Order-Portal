# NetSuite

Status: **live, real adapter**
(`src/modules/integration/erp/infrastructure/netsuite_adapter.py`). This page is sourced
from the adapter code and from a human-reviewed canonical<->NetSuite field mapping — if
it ever disagrees with the adapter or `src/modules/integration/erp/domain/status_mapping.py`,
the code is right and this is stale.

## What it is, as far as this platform is concerned

NetSuite's **Sales Order** record (`salesOrder`), driven over **SuiteTalk REST Web
Services** (`<base_url>/services/rest/...`) — not SOAP, not RESTlets. Lookups that
aren't a direct record GET go through **SuiteQL** (`/services/rest/query/v1/suiteql`),
NetSuite's SQL-like query endpoint.

## How a connection is configured

One `ErpConnection` row = one NetSuite account. The fields that matter for NetSuite:

| `ErpConnection` field | What it is for NetSuite |
|---|---|
| `base_url` | e.g. `https://<account_id>.suitetalk.api.netsuite.com` — the adapter appends `/services/rest/...` itself. |
| `credentials["account_id"]` | NetSuite account id. Not currently spliced into any URL by the adapter (`base_url` is already account-specific), kept available for anything that needs it explicitly. |
| `credentials["client_id"]` | The Integration record's Client ID (Consumer Key) — the JWT assertion's `iss`. |
| `credentials["certificate_id"]` | The id of the certificate uploaded to the Integration record — the JWT header's `kid`. |
| `secret_ref` | Resolves to the **RSA private key (PEM)** matching that certificate — used to sign the JWT assertion, never sent anywhere itself. |
| `webhook_secret_ref` | Not used — NetSuite isn't wired for inbound webhooks today (see below). |

## Authentication

**ASSUMPTION (NetSuite's public API documentation, to be verified against the real
account):** OAuth 2.0 **Client Credentials Grant** (machine-to-machine), authenticated
with an RS256-signed JWT bearer client assertion — this is NetSuite's own
currently-recommended mechanism for a system-to-system integration with no end user
involved. Its older alternative, Token-based Authentication (OAuth 1.0a / HMAC-SHA256),
remains supported but is the legacy path NetSuite's docs steer new integrations away
from.

Flow (`NetSuiteAdapter._get_access_token`): build a JWT (`iss=client_id`,
`scope=rest_webservices`, `aud=<token endpoint>`, `iat`/`exp`), sign it RS256 with the
account's private key, `kid`=`certificate_id`, then `POST` it as `client_assertion` to
`<base_url>/services/rest/auth/oauth2/v1/token` with
`grant_type=client_credentials`. The returned bearer token is sent as
`Authorization: Bearer <token>` on every subsequent REST/SuiteQL call. No caching —
every adapter call re-authenticates (same tradeoff as Odoo's adapter).

RS256 signing uses `PyJWT`/`cryptography` — both already project dependencies (Cognito
token verification uses the same library), so this isn't a new dependency.

## Outbound: canonical order -> NetSuite `salesOrder`

Field-by-field, from the human-reviewed canonical<->NetSuite mapping (confidence scores
as reviewed):

| Canonical | NetSuite field | Confidence | Notes |
|---|---|---|---|
| binding `erp_customer_id` (FR-A1) | `entityid` | 97% | Used **directly**, no name-based lookup/auto-create — same reasoning as Odoo's `partner_id`. A missing/invalid value is a terminal error. |
| `client_reference` | `otherrefnum` | 96% | The reseller's own reference — **not** the platform's own order id (that's a different mechanism, see Idempotency below). |
| `line.product_key` | `item` (lookup only, by `itemid`) | 97% | **Fails closed**: no match -> terminal error naming the SKU, never an auto-created phantom item. |
| `line.quantity` | `quantity` | 99% | |
| `line.unit_of_measure` | `units` | 98% | **Always omitted today** — see "Known gaps". |
| `line.unit_price` | `rate` | 97% | No discount/tax handling — neither is in the approved mapping. |
| *(platform's own `order_id`)* | NetSuite's built-in `externalId` | — (not part of the approved mapping; a platform-level de-dup mechanism, not a business field) | See Idempotency below. |
| *(returned)* `erp_order_id` | `tranid` | 98% | Read back after create (NetSuite assigns it), same role as Odoo's `sale.order.name`. |

### Idempotency

Before creating anything, `submit` checks NetSuite's own `externalId` addressing
(`GET .../salesOrder/eid:<platform order_id>`) — NetSuite's publicly documented REST
convention for "has an external system already created this record", analogous to
Odoo's `client_order_ref` search. This deliberately does **not** reuse `otherrefnum`:
that field is approved to carry the reseller's `client_reference`, a different concept
(FR-A2's platform-level idempotency key vs. the reseller's own PO/reference number).

## Inbound: NetSuite `salesOrder` -> canonical status/fulfillment fields

| NetSuite field | Canonical | Confidence | Notes |
|---|---|---|---|
| `fulfillmentstatus` | `fulfillment_status` | 99% | The only field `_map_netsuite` (status_mapping.py) reads. Its standard values (`pending fulfillment`, `partially fulfilled`, `fulfilled`) all map to `CONFIRMED` — a fully delivered order is a shipped fact (Fulfillment records), not its own lifecycle status (FR-A6), same reasoning as Odoo's `"sale"`/`"done"`. |
| `carrier` | `carrier` | 99% | Returned by `fetch_status` for downstream fulfillment tracking; not read by the status mapper itself. |
| `shipqty` | `shipped_qty_by_line` | 98% | Same as `carrier` — surfaced, not consumed by the status mapper. |

### `fetch_status` — step by step

1. Authenticate.
2. SuiteQL: find the record's internal id by `tranid` (`SELECT id FROM transaction WHERE
   tranid = ? AND type = 'SalesOrd'`). No match -> `None`.
3. `GET` the full record by internal id, pluck out `fulfillmentstatus`/`carrier`/`shipqty`.

## Known gaps

Real limitations, flagged rather than hidden:

- **`unit_of_measure` is never sent.** Unlike Odoo's UoM lookup (a safe global-by-name
  search), NetSuite's unit internal ids are only valid *within the Units Type assigned
  to a specific item* — a generic "search units by name" could return an id that's
  wrong (or outright invalid) for that item. Which unit list this account's items
  actually use is account-specific and not knowable without the live account, so
  `_resolve_unit` always omits the field (NetSuite falls back to the item's default
  unit) instead of guessing.
- **`cancel()` is not wired up.** The approved field mapping has no field for
  "cancelled" — NetSuite's lifecycle tracks that via a separate status/billing concept
  beyond `fulfillmentstatus` (e.g. a billing status, or a custom
  approval-workflow/order-status value), and which exact field+value this account uses
  isn't knowable without it. `cancel()` always returns a terminal failure naming this
  gap rather than guessing a status value to PATCH.
- **No CLOSED/CANCELLED native status mapping yet.** `_map_netsuite` only ever returns
  `CONFIRMED` or `None` — same root cause as the `cancel()` gap above (no approved field
  for either canonical state). Add the mapper branches once the real field/values are
  confirmed against the account.
- **No inbound webhook.** Not wired for the thin-webhook pattern described in
  `docs/erp-integration-patterns.md` — reconciliation polling only, same as every newly
  registered ERP until that's separately built.
- **Account id/client id/certificate id plumbing is a best-effort shape, not yet
  verified against a real Integration record.** The exact `credentials` keys above are
  this adapter's working assumption of what NetSuite's OAuth2 M2M setup needs; confirm
  against the real account before going live.
