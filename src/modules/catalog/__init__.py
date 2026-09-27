"""Catalog module — items owned by exactly one ERP connection.

An item is owned by the connection it was synced from (`owning_connection_id`) and is
visible to a reseller only via a verified binding. The same SKU arriving from two
connections is an ownership conflict for the operator to resolve. CRUD aggregate.
"""
