"""Composition root — FastAPI app for the ERP & Supply Chain Order Portal (U0 foundation).

Wires shared cross-cutting concerns: correlation middleware, health endpoints,
and the metrics endpoint. Feature module routers (U1-U4) will be included here as
they are built.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..shared.correlation import CORRELATION_HEADER, get_correlation_id, set_correlation_id
from ..shared.logging import configure_logging, get_logger
from ..shared import metrics
from ..modules.foundation.queue.worker import HandlerRegistry, WorkerHost
from ..modules.foundation.queue.poller import Poller
from ..modules.foundation.persistence.database import SessionLocal
from ..modules.identity.router import router as identity_router
from ..modules.integration.bootstrap import register_integration
from ..modules.ordering.router import router as ordering_router
from ..modules.admin.router import router as admin_router

configure_logging(os.environ.get("LOG_LEVEL", "INFO"))
logger = get_logger("app.main")

app = FastAPI(title="ERP & Supply Chain Order Portal", version="0.1.0")

# Shared queue infrastructure (handlers registered by U3 later).
handler_registry = HandlerRegistry()
worker_host = WorkerHost(SessionLocal, handler_registry)
poller = Poller(worker_host)

# Feature module routers
app.include_router(identity_router)
app.include_router(ordering_router)
app.include_router(admin_router)

# Register U3 integration adapters + job handlers into the shared worker registry
register_integration(handler_registry)

# --- Web UI (static frontend served by the same app) ---
_WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@app.get("/", include_in_schema=False)
def _index():
    index = _WEB_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return Response(content='{"detail":"UI not built"}', media_type="application/json", status_code=404)


if _WEB_DIR.exists():
    # Static assets (css/js) under /static; API routes above take precedence.
    app.mount("/static", StaticFiles(directory=str(_WEB_DIR)), name="static")


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    incoming = request.headers.get(CORRELATION_HEADER)
    cid = set_correlation_id(incoming)
    metrics.increment("http_requests_total")
    response: Response = await call_next(request)
    response.headers[CORRELATION_HEADER] = cid or ""
    return response


@app.get("/livez")
def livez():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    """Readiness checks DB connectivity."""
    try:
        session = SessionLocal()
        session.execute(__import__("sqlalchemy").text("SELECT 1"))
        session.close()
        return {"status": "ready"}
    except Exception:  # noqa: BLE001
        return Response(content='{"status":"not-ready"}', media_type="application/json", status_code=503)


@app.get("/metrics")
def metrics_endpoint():
    return Response(content=metrics.render_text(), media_type="text/plain")


@app.on_event("startup")
def _startup():
    # Local PoC convenience: on SQLite, create tables + seed demo data.
    try:
        from .seed import is_sqlite, seed_local
        if is_sqlite():
            seed_local()
            logger.info("sqlite schema created and seeded")
    except Exception:  # noqa: BLE001
        logger.exception("local seed failed")

    role = os.environ.get("APP_ROLE", "both")
    if role in ("worker", "both"):
        poller.start()
    logger.info("app started", extra={"extra_fields": {"role": role}})


@app.on_event("shutdown")
def _shutdown():
    poller.stop()
