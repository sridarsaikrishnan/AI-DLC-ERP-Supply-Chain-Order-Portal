"""Fulfillment/Invoice/Payment/Return — event-sourced, unlike `catalog`/`connections`/
`tenancy`. Per ADR-0002's own revisit condition ("another aggregate needs the same
guarantees Order needs — full audit history, idempotent transitions"), these are real
operational/financial records worth a replayable log, not reference/config data.
"""

from __future__ import annotations
