"""Persistence infrastructure: engine/session, tables, Postgres event store, outbox relay.

Implements the kernel's `EventStore` port on PostgreSQL. Authored for the real stack;
exercised against the Postgres from docker-compose (not run in the offline sandbox).
"""
