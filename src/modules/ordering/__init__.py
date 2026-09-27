"""Ordering module — the Order aggregate (event-sourced) and order routing.

This slice contains the pure ownership-routing policy. The event-sourced Order
aggregate + command handlers + projections are added in the next slice (task #4).
"""
