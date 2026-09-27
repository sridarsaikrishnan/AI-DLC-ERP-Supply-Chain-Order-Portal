"""FastAPI composition root: mounts GraphQL (reseller + operator) + HTTP (webhooks, health).

Security headers (SECURITY-04) are applied to all responses. Tenant/roles are taken from
the validated Cognito JWT; a header-based stub is used until Cognito is wired (Phase 3).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter

from src.api.graphql.context import GraphQLContext
from src.api.graphql.operator.schema import build_operator_schema
from src.api.graphql.reseller.schema import build_reseller_schema
from src.api.http import health, webhooks
from src.composition import build_container

_SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def _identity(request: Request) -> tuple[str, tuple[str, ...]]:
    """Resolve (tenant_id, roles). TODO(Phase 3): validate Cognito JWT (issuer/aud/exp/sig).

    Until then, trust a gateway-provided header in local dev only.
    """
    tenant = request.headers.get("x-tenant-id", "tnt_demo")
    roles = tuple(r for r in request.headers.get("x-roles", "").split(",") if r)
    return tenant, roles


def create_app() -> FastAPI:
    app = FastAPI(title="ERP & Supply Chain Order Portal", version="0.2.0")
    app.state.container = build_container()

    async def reseller_context(request: Request) -> GraphQLContext:
        tenant, roles = _identity(request)
        return GraphQLContext(container=app.state.container, tenant_id=tenant, roles=roles)

    async def operator_context(request: Request) -> GraphQLContext:
        tenant, roles = _identity(request)
        return GraphQLContext(container=app.state.container, tenant_id=tenant, roles=roles)

    app.include_router(
        GraphQLRouter(build_reseller_schema(), context_getter=reseller_context), prefix="/graphql/reseller"
    )
    app.include_router(
        GraphQLRouter(build_operator_schema(), context_getter=operator_context), prefix="/graphql/operator"
    )
    app.include_router(webhooks.router)
    app.include_router(health.router)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    return app


app = create_app()
