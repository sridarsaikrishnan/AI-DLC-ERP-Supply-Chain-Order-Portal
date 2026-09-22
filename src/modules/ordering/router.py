"""U2 endpoints (LC-U2-4). Guarded by U1 auth dependencies."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..foundation.context.security_context import SecurityContext
from ..foundation.persistence.database import get_session
from ..identity.deps import current_context, require_role
from ...shared.errors import NotFoundError, PortalError, ValidationError
from .catalog_service import CatalogService
from .schemas import (
    ActionAck,
    AmendRequest,
    InventoryView,
    OrderAck,
    OrderView,
    PlaceOrderRequest,
    ProductView,
    StatusEntry,
    StatusHistoryView,
)
from .service import OrderService

router = APIRouter(tags=["ordering"])
catalog = CatalogService()


def _order_view(row) -> OrderView:
    return OrderView(
        order_id=row.id,
        client_reference=row.client_reference,
        lifecycle_state=row.lifecycle_state,
        erp_reference=row.erp_reference,
        created_at=row.created_at,
    )


@router.post("/orders", response_model=OrderAck)
def place_order(body: PlaceOrderRequest, ctx: SecurityContext = Depends(require_role("CLIENT_USER")), session: Session = Depends(get_session)):
    try:
        row = OrderService(session, ctx).place_order(body.model_dump(mode="json"))
        session.commit()
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors)
    return OrderAck(order_id=row.id, lifecycle_state=row.lifecycle_state)


@router.get("/orders", response_model=list[OrderView])
def list_orders(ctx: SecurityContext = Depends(current_context), session: Session = Depends(get_session)):
    return [_order_view(r) for r in OrderService(session, ctx).list_orders()]


@router.get("/orders/{order_id}", response_model=OrderView)
def get_order(order_id: str, ctx: SecurityContext = Depends(current_context), session: Session = Depends(get_session)):
    try:
        return _order_view(OrderService(session, ctx).get_order(order_id))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="order not found")


@router.get("/orders/{order_id}/history", response_model=StatusHistoryView)
def order_history(order_id: str, ctx: SecurityContext = Depends(current_context), session: Session = Depends(get_session)):
    try:
        rows = OrderService(session, ctx).get_history(order_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="order not found")
    return StatusHistoryView(
        order_id=order_id,
        history=[StatusEntry(state=r.state, reason=r.reason, occurred_at=r.occurred_at) for r in rows],
    )


def _corrective(order_id: str, action: str, session: Session, ctx: SecurityContext, amended: dict | None = None) -> ActionAck:
    try:
        OrderService(session, ctx).initiate_corrective(order_id, action, amended)
        session.commit()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="order not found")
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors)
    except PortalError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ActionAck(order_id=order_id)


@router.post("/orders/{order_id}/cancel", response_model=ActionAck)
def cancel_order(order_id: str, ctx: SecurityContext = Depends(require_role("CLIENT_USER")), session: Session = Depends(get_session)):
    return _corrective(order_id, "CANCEL", session, ctx)


@router.post("/orders/{order_id}/resubmit", response_model=ActionAck)
def resubmit_order(order_id: str, ctx: SecurityContext = Depends(require_role("CLIENT_USER")), session: Session = Depends(get_session)):
    return _corrective(order_id, "RESUBMIT", session, ctx)


@router.post("/orders/{order_id}/amend", response_model=ActionAck)
def amend_order(order_id: str, body: AmendRequest, ctx: SecurityContext = Depends(require_role("CLIENT_USER")), session: Session = Depends(get_session)):
    return _corrective(order_id, "AMEND", session, ctx, amended=body.model_dump(mode="json"))


@router.get("/catalog", response_model=list[ProductView])
def browse_catalog(q: str | None = None, ctx: SecurityContext = Depends(current_context)):
    return [ProductView(**p) for p in catalog.browse(q)]


@router.get("/inventory/{product_key}", response_model=InventoryView)
def check_inventory(product_key: str, ctx: SecurityContext = Depends(current_context)):
    inv = catalog.availability(product_key)
    if inv is None:
        raise HTTPException(status_code=404, detail="availability unavailable")
    return InventoryView(**inv)
