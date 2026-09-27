"""Shared library: reusable, domain-agnostic building blocks.

Nothing here contains business rules. Domain modules depend on this package; this
package depends on nothing in `modules`, `api`, or `worker` (enforced by import-linter).
"""
