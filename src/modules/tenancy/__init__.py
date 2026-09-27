"""Tenancy module — resellers and their bindings to ERP connections.

A `TenantConnectionBinding` links a reseller (tenant) to an ERP connection plus that
reseller's customer id in that ERP, and must be verified before any inbound data is
attributed to the tenant. Uniqueness guarantees isolation:
  UNIQUE(tenant_id, connection_id)  and  UNIQUE(connection_id, erp_customer_id)
CRUD aggregate (not event-sourced).
"""
