"""Connections module — the registry of ERP instances the platform talks to.

An `ErpConnection` is operator-only identity (name, endpoint, credentials reference).
It is NEVER exposed on reseller-facing surfaces (FR-19). CRUD aggregate (not event-sourced).
"""
