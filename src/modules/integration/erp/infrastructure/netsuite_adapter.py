"""Real NetSuite adapter (SuiteTalk REST Web Services) implementing the ErpAdapter port.

Field names used below (both in the request bodies this builds and in the response
fields `fetch_status` reads) come straight from the human-reviewed canonical<->NetSuite
field mapping in `docs/erps/netsuite.md` — that mapping is authoritative here, not
re-derived. See that doc for the full outbound/inbound tables and confidence scores.

Stdlib-only HTTP client (`urllib`), explicit timeouts, and transient/terminal error
classification (RESILIENCY-10), following `odoo_adapter.py`'s shape. The one exception
to "stdlib-only" is JWT signing for authentication: `PyJWT` + `cryptography` are already
project dependencies (`pyproject.toml` — used today for Cognito's RS256 tokens in
`shared/identity/cognito.py`), so reusing them here for NetSuite's own RS256 JWT bearer
assertion isn't a new dependency, just a second consumer of an existing one.

Exercised against a live NetSuite account only via the (separately required) steps in
`docs/erps/netsuite.md`; not run in the offline sandbox. Pure payload building and the
HTTP/SuiteQL seams are unit-testable without one — see `test_netsuite_adapter.py`.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import jwt

from ..application.ports import ErpTarget, SubmissionResult

_RECORD_TYPE = "salesOrder"


class _NetSuiteError(Exception):
    def __init__(self, message: str, *, terminal: bool) -> None:
        super().__init__(message)
        self.terminal = terminal


def build_sales_order_lines(order_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Pure: canonical order payload -> the fields this adapter resolves into NetSuite
    sales order line items. Mirrors `odoo_adapter.build_sale_order_lines`'s shape — same
    canonical keys in (`product_key`/`quantity`/`unit_of_measure`/`unit_price`), with the
    NetSuite-specific resolution (item internal id lookup) happening in `submit`, not
    here, so this stays testable without a live account.

    No `line_discount`/`tax_rates` handling — unlike Odoo's version, those aren't in the
    approved field mapping for this ERP, so this doesn't invent handling for them.
    """
    lines: list[dict[str, Any]] = []
    for raw in order_payload.get("lines", []) or []:
        product_key = str(raw.get("product_key") or "UNKNOWN")
        try:
            qty = float(raw.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            qty = 0.0
        unit_price = raw.get("unit_price")
        rate = float(unit_price["amount"]) if unit_price is not None else None
        lines.append(
            {
                "product_key": product_key,
                "quantity": max(qty, 0.0) or 1.0,
                "unit_of_measure": str(raw.get("unit_of_measure") or ""),
                "rate": rate,
            }
        )
    return lines


class NetSuiteAdapter:
    # Declared per ADR-0015 — what this adapter actually uses from the canonical
    # payload. "tax"/"multi_currency" are deliberately absent: no tax field is in the
    # approved mapping and there's no multi-currency handling. "uom" is also absent,
    # deliberately — see `_resolve_unit`'s docstring for why guessing one would be worse
    # than omitting it. "partial_fulfillment" IS declared: unlike Odoo, `fetch_status`
    # here does surface shipped-quantity data (`shipqty` -> `shipped_qty_by_line`, per
    # the approved mapping).
    capabilities = frozenset({"idempotency", "fail_closed_product", "partial_fulfillment"})

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = timeout_seconds

    # --- ErpAdapter port ---
    def submit(self, target: ErpTarget, order_payload: dict[str, Any]) -> SubmissionResult:
        try:
            token = self._get_access_token(target)
            # Idempotency: NetSuite's own `externalId` addressing (`eid:...`) is the
            # publicly documented REST convention for "has an external system already
            # created this record" — not reusing `otherrefnum` (that's approved to mean
            # the reseller's client_reference, a different field, FR-A2 vs FR-elsewhere).
            order_id = order_payload.get("order_id")
            if order_id:
                existing = self._get_record_by_external_id(target, token, str(order_id))
                if existing is not None:
                    return SubmissionResult(
                        success=True, erp_order_id=str(existing.get("tranid") or "")
                    )
            # The customer is the reseller's ERP customer id from the binding (FR-A1) —
            # sent directly as `entityid` (approved mapping), never a name-based lookup.
            entity_id = self._entity_id(order_payload)
            lines: list[dict[str, Any]] = []
            for line in build_sales_order_lines(order_payload):
                item_id = self._resolve_item(target, token, line["product_key"])
                line_vals: dict[str, Any] = {"item": {"id": item_id}, "quantity": line["quantity"]}
                if line["rate"] is not None:
                    line_vals["rate"] = line["rate"]
                unit_id = self._resolve_unit(target, token, line["unit_of_measure"])
                if unit_id is not None:
                    line_vals["units"] = {"id": unit_id}
                lines.append(line_vals)
            body: dict[str, Any] = {"entityid": entity_id, "item": {"items": lines}}
            client_reference = order_payload.get("client_reference")
            if client_reference:
                body["otherrefnum"] = str(client_reference)
            if order_id:
                body["externalId"] = str(order_id)
            internal_id = self._create_record(target, token, body)
            record = self._get_record(target, token, internal_id)
            tranid = str((record or {}).get("tranid") or internal_id)
            return SubmissionResult(success=True, erp_order_id=tranid)
        except _NetSuiteError as exc:
            return SubmissionResult(success=False, error=str(exc), terminal=exc.terminal)

    def fetch_status(self, target: ErpTarget, erp_order_id: str) -> dict[str, str] | None:
        try:
            token = self._get_access_token(target)
            internal_id = self._find_internal_id_by_tranid(target, token, erp_order_id)
            if internal_id is None:
                return None
            record = self._get_record(target, token, internal_id)
            if record is None:
                return None
            # Field names straight from the approved mapping (docs/erps/netsuite.md):
            # fulfillmentstatus -> fulfillment_status, carrier -> carrier,
            # shipqty -> shipped_qty_by_line. `_map_netsuite` (status_mapping.py) only
            # reads `fulfillmentstatus`; `carrier`/`shipqty` are returned here too so
            # they're available to whatever reads this field bag next (fulfillment
            # tracking is a separate concern from lifecycle status — see FR-A6).
            return {
                "fulfillmentstatus": str(record.get("fulfillmentstatus") or ""),
                "carrier": str(record.get("carrier") or ""),
                "shipqty": str(record.get("shipqty") or ""),
            }
        except _NetSuiteError:
            return None

    def cancel(self, target: ErpTarget, erp_order_id: str) -> SubmissionResult:
        try:
            token = self._get_access_token(target)
            internal_id = self._find_internal_id_by_tranid(target, token, erp_order_id)
            if internal_id is None:
                return SubmissionResult(success=False, error="order not found", terminal=True)
            # TODO(account-specific): this account's native field/value for marking a
            # NetSuite sales order cancelled isn't in the approved field mapping and
            # isn't knowable without the live account (e.g. a billing/approval-workflow
            # status, or which `orderstatus` value this account actually uses for
            # "Cancelled"). Confirm it against the real account, then PATCH that field
            # here — never guess a status value for a write path like this one.
            raise _NetSuiteError(
                "cancel() is not wired up for this account yet — see the TODO in "
                "NetSuiteAdapter.cancel for exactly what's missing",
                terminal=True,
            )
        except _NetSuiteError as exc:
            return SubmissionResult(success=False, error=str(exc), terminal=exc.terminal)

    # --- field resolution ---
    @staticmethod
    def _entity_id(order_payload: dict[str, Any]) -> str:
        """The order is placed AS the reseller's ERP customer (FR-A1): `entityid` is
        used directly (approved mapping: entityid -> erp_customer_id) — no name-based
        lookup/auto-create, same reasoning as Odoo's `_partner_id`."""
        raw = order_payload.get("erp_customer_id")
        if raw in (None, ""):
            raise _NetSuiteError(
                "no erp_customer_id on the order — the reseller is not linked to an ERP customer",
                terminal=True,
            )
        return str(raw)

    def _resolve_item(self, target: ErpTarget, token: str, code: str) -> str:
        """Fail closed, not silent auto-create: by the time this runs, `routing.py` has
        already confirmed `code` is a real SKU in *our* catalog. If NetSuite has no
        matching item, that's catalog drift worth a human looking at — not something to
        paper over by inventing a new NetSuite item. `itemid` is NetSuite's own built-in
        display-name field on an item record (publicly documented, not account-specific)."""
        rows = self._suiteql(
            target, token, f"SELECT id FROM item WHERE itemid = '{self._escape(code)}'"
        )
        if rows:
            return str(rows[0]["id"])
        raise _NetSuiteError(
            f"no NetSuite item with itemid '{code}' — sync it in NetSuite before retrying",
            terminal=True,
        )

    def _resolve_unit(self, target: ErpTarget, token: str, name: str) -> str | None:
        """Deliberately NOT a lookup, unlike Odoo's `_resolve_uom`: a NetSuite unit
        internal id is only valid *within the Units Type assigned to this specific
        item* — a generic "search all units by name" could return an id that's a
        syntactically fine match but wrong (or outright invalid) for this item, which is
        worse than omitting it. Which unit list this account's items actually use is
        account-specific and not knowable without the live account, so this always
        omits the field (NetSuite then uses the item's default unit) rather than
        guessing — see docs/erps/netsuite.md's "Known gaps"."""
        del target, token, name  # not used — see docstring
        return None

    # --- idempotency / lookups ---
    def _get_record_by_external_id(
        self, target: ErpTarget, token: str, external_id: str
    ) -> dict[str, Any] | None:
        status, body, _ = self._http(
            target,
            token,
            "GET",
            f"/record/v1/{_RECORD_TYPE}/eid:{urllib.parse.quote(external_id)}",
        )
        if status == 404:
            return None
        return body

    def _find_internal_id_by_tranid(
        self, target: ErpTarget, token: str, tranid: str
    ) -> str | None:
        rows = self._suiteql(
            target,
            token,
            "SELECT id FROM transaction WHERE tranid = "
            f"'{self._escape(tranid)}' AND type = 'SalesOrd'",
        )
        return str(rows[0]["id"]) if rows else None

    def _create_record(self, target: ErpTarget, token: str, body: dict[str, Any]) -> str:
        status, _, headers = self._http(
            target, token, "POST", f"/record/v1/{_RECORD_TYPE}", body=body
        )
        location = headers.get("Location") or headers.get("location") or ""
        internal_id = location.rstrip("/").rsplit("/", 1)[-1] if location else ""
        if not internal_id:
            raise _NetSuiteError(
                f"NetSuite did not return a record location (HTTP {status})", terminal=True
            )
        return internal_id

    def _get_record(
        self, target: ErpTarget, token: str, internal_id: str
    ) -> dict[str, Any] | None:
        status, body, _ = self._http(
            target, token, "GET", f"/record/v1/{_RECORD_TYPE}/{internal_id}"
        )
        if status == 404:
            return None
        return body

    def _suiteql(self, target: ErpTarget, token: str, query: str) -> list[dict[str, Any]]:
        # `Prefer: transient` is required by NetSuite's SuiteQL endpoint (publicly
        # documented) — without it NetSuite persists the query as a saved search.
        _, body, _ = self._http(
            target,
            token,
            "POST",
            "/query/v1/suiteql",
            body={"q": query},
            extra_headers={"Prefer": "transient"},
        )
        return list((body or {}).get("items") or [])

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("'", "''")

    # --- OAuth 2.0 Client Credentials (M2M) authentication ---
    def _get_access_token(self, target: ErpTarget) -> str:
        """ASSUMPTION (NetSuite public API documentation, to be verified against the
        real account): authenticates via OAuth 2.0 Client Credentials Grant using a
        JWT bearer client assertion (RS256) — NetSuite's own currently-recommended
        mechanism for new system-to-system integrations with no end user involved
        (its alternative, Token-based Authentication/OAuth 1.0a HMAC signing, is older
        and NetSuite's docs steer new integrations away from it). `target.secret` is
        the RSA private key (PEM) for the certificate registered on this account's
        Integration record — resolved via Secrets Manager, same role Odoo's password
        plays in `OdooAdapter._authenticate`. `credentials["account_id"]`/`["client_id"]`
        /`["certificate_id"]` are the non-secret identifiers NetSuite's own OAuth2 M2M
        setup requires (per `ErpConnection.credentials`'s docstring: "a token-auth ERP
        [...] might need an account id").

        Re-authenticates on every call (no token caching) — same tradeoff Odoo's adapter
        makes ("every call re-authenticates"); fine for this adapter's call volume, a
        real gap if NetSuite's token endpoint turns out to be rate-limited in practice.
        """
        client_id = target.credentials.get("client_id", "")
        certificate_id = target.credentials.get("certificate_id", "")
        token_url = target.base_url.rstrip("/") + "/services/rest/auth/oauth2/v1/token"
        now = int(time.time())
        assertion = jwt.encode(
            {
                "iss": client_id,
                "scope": "rest_webservices",
                "aud": token_url,
                "iat": now,
                "exp": now + 3600,  # NetSuite's maximum assertion lifetime
            },
            target.secret,
            algorithm="RS256",
            headers={"kid": certificate_id} if certificate_id else None,
        )
        data = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": assertion,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                parsed = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            terminal = not (500 <= exc.code < 600)
            raise _NetSuiteError(
                f"token request failed: HTTP {exc.code}", terminal=terminal
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise _NetSuiteError(f"cannot reach NetSuite: {exc}", terminal=False) from exc
        token = parsed.get("access_token")
        if not token:
            raise _NetSuiteError("token response had no access_token", terminal=True)
        return str(token)

    # --- REST plumbing ---
    def _http(
        self,
        target: ErpTarget,
        token: str,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any] | None, dict[str, str]]:
        base = target.base_url.rstrip("/")
        # NetSuite's REST Web Services base path convention (publicly documented):
        # <base_url>/services/rest/record/v1/... and .../query/v1/suiteql. `base_url` is
        # already resolved per-connection (same pattern as Odoo) so no account id needs
        # to be spliced in here.
        url = base + "/services/rest" + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        headers.update(extra_headers or {})
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
                parsed = json.loads(raw) if raw else None
                return response.status, parsed, dict(response.headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return 404, None, {}
            terminal = not (500 <= exc.code < 600)
            raise _NetSuiteError(f"HTTP {exc.code}", terminal=terminal) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise _NetSuiteError(f"cannot reach NetSuite: {exc}", terminal=False) from exc
