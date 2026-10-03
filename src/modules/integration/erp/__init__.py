"""Integration module — talking to ERP systems.

Owns the `ErpAdapter` port, the concrete adapters (Odoo/ERPNext/stub), native↔canonical
status mapping, and the outbound delivery handler. Domain (aggregates) never imports
this; delivery drives orders through a narrow command port.
"""
