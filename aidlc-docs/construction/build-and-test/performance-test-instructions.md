# Performance Test Instructions

## Applicability
MVP has no hard performance targets (best-effort, Q4=C at moderate volume: hundreds–low thousands of orders/day). This is a lightweight, optional check — not a gate for the PoC.

## Optional Smoke Load
Using a simple tool (e.g., hey/k6/locust) against the proxy:
```bash
# example with hey: 200 requests, 10 concurrent, against livez
hey -n 200 -c 10 http://localhost:8080/livez
```
For order submission load, first obtain a bearer token, then drive `POST /orders` with a valid body.

## What to Observe
- Submission API stays responsive because it only validates + persists + enqueues (fulfillment is async).
- Worker throughput: jobs drain from the `jobs` table; `SELECT ... FOR UPDATE SKIP LOCKED` lets the 2 replicas share the load without double-processing.
- Metrics endpoint `/metrics` exposes request and job counters.

## If Slow
- Increase app replicas; the DB-backed queue is the first swap-out point for a real broker if volume grows past the moderate target.
