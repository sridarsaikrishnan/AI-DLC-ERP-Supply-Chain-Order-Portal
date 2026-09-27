"""Real Odoo adapter (JSON-RPC) implementing the ErpAdapter port.

Stdlib-only client with explicit timeouts and transient/terminal error classification
(RESILIENCY-10). Exercised against a live Odoo (docker/floci stack); not run in the
offline sandbox. Pure payload building is unit-testable without a server.
"""

from __future__ import annotations

import json
import random
import socket
import urllib.error
import urllib.request
from typing import Any

from ..application.ports import ErpTarget, SubmissionResult


class _OdooError(Exception):
    def __init__(self, message: str, *, terminal: bool) -> None:
        super().__init__(message)
        self.terminal = terminal


def build_sale_order_lines(order_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Pure: turn the ERP-neutral payload into the fields we resolve into Odoo order lines."""
    lines: list[dict[str, Any]] = []
    for raw in order_payload.get("lines", []) or []:
        product_key = str(raw.get("product_key") or "UNKNOWN")
        try:
            qty = float(raw.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            qty = 0.0
        lines.append({"product_key": product_key, "quantity": max(qty, 0.0) or 1.0})
    return lines


class OdooAdapter:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = timeout_seconds

    # --- ErpAdapter port ---
    def submit(self, target: ErpTarget, order_payload: dict[str, Any]) -> SubmissionResult:
        try:
            uid = self._authenticate(target)
            partner_id = self._resolve_partner(target, uid, str(order_payload.get("partner_name") or "Portal Customer"))
            order_lines = []
            for line in build_sale_order_lines(order_payload):
                product_id = self._resolve_product(target, uid, line["product_key"])
                order_lines.append((0, 0, {"product_id": product_id, "product_uom_qty": line["quantity"]}))
            vals: dict[str, Any] = {"partner_id": partner_id, "order_line": order_lines}
            if order_payload.get("client_reference"):
                vals["client_order_ref"] = order_payload["client_reference"]
            order_id = self._execute(target, uid, "sale.order", "create", [vals])
            record = self._execute(target, uid, "sale.order", "read", [[order_id], ["name"]])
            name = record[0]["name"] if record else str(order_id)
            return SubmissionResult(success=True, erp_order_id=name)
        except _OdooError as exc:
            return SubmissionResult(success=False, error=str(exc), terminal=exc.terminal)

    def fetch_status(self, target: ErpTarget, erp_order_id: str) -> str | None:
        try:
            uid = self._authenticate(target)
            rows = self._execute(
                target, uid, "sale.order", "search_read",
                [[["name", "=", erp_order_id]]], {"fields": ["state"], "limit": 1},
            )
            return rows[0]["state"] if rows else None
        except _OdooError:
            return None

    def cancel(self, target: ErpTarget, erp_order_id: str) -> SubmissionResult:
        try:
            uid = self._authenticate(target)
            rows = self._execute(
                target, uid, "sale.order", "search_read",
                [[["name", "=", erp_order_id]]], {"fields": ["id"], "limit": 1},
            )
            if not rows:
                return SubmissionResult(success=False, error="order not found", terminal=True)
            self._execute(target, uid, "sale.order", "action_cancel", [[rows[0]["id"]]])
            return SubmissionResult(success=True, erp_order_id=erp_order_id)
        except _OdooError as exc:
            return SubmissionResult(success=False, error=str(exc), terminal=exc.terminal)

    # --- JSON-RPC plumbing ---
    def _authenticate(self, target: ErpTarget) -> int:
        uid = self._jsonrpc(target, "common", "authenticate", [target.database, target.username, target.secret, {}])
        if not uid:
            raise _OdooError("authentication failed", terminal=True)
        return int(uid)

    def _execute(
        self, target: ErpTarget, uid: int, model: str, method: str,
        args: list[Any], kwargs: dict[str, Any] | None = None,
    ) -> Any:
        return self._jsonrpc(
            target, "object", "execute_kw",
            [target.database, uid, target.secret, model, method, args, kwargs or {}],
        )

    def _resolve_partner(self, target: ErpTarget, uid: int, name: str) -> int:
        found = self._execute(target, uid, "res.partner", "search", [[["name", "=", name]]], {"limit": 1})
        if found:
            return int(found[0])
        return int(self._execute(target, uid, "res.partner", "create", [{"name": name}]))

    def _resolve_product(self, target: ErpTarget, uid: int, code: str) -> int:
        found = self._execute(target, uid, "product.product", "search", [[["default_code", "=", code]]], {"limit": 1})
        if found:
            return int(found[0])
        return int(self._execute(target, uid, "product.product", "create", [{"name": code, "default_code": code}]))

    def _jsonrpc(self, target: ErpTarget, service: str, method: str, args: list[Any]) -> Any:
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {"service": service, "method": method, "args": args},
                "id": random.randint(1, 1_000_000_000),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            target.base_url.rstrip("/") + "/jsonrpc",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                parsed = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise _OdooError(f"HTTP {exc.code}", terminal=not (500 <= exc.code < 600)) from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            raise _OdooError(f"cannot reach Odoo: {exc}", terminal=False) from exc

        if parsed.get("error"):
            error = parsed["error"]
            message = (error.get("data") or {}).get("message") or error.get("message") or "Odoo error"
            raise _OdooError(str(message), terminal=True)
        return parsed.get("result")
