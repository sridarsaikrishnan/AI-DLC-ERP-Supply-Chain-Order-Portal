"""Inbound ERP webhooks — the primary way we COLLECT data from ERPs.

A thin, fast ingress: authenticate (HMAC), attribute to a tenant via reverse-routing
keys, dedupe (at-least-once), then drive the order's status. Unattributable or
unauthenticated payloads are dropped, never broadcast. HTTP wiring lives in
api/http/webhooks.py; this module is transport-agnostic.
"""
