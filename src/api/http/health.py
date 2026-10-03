"""Liveness / readiness / metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response

router = APIRouter()


@router.get("/livez")
def livez() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    # A deep check (DB connectivity) is wired in the Postgres deployment.
    return {"status": "ready"}


@router.get("/metrics")
def metrics() -> Response:
    return Response(
        content="# metrics exposed via OpenTelemetry/CloudWatch in deployment\n",
        media_type="text/plain",
    )
