"""U4 admin endpoints (LC-U4-4). All require ADMIN role."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..foundation.config.models import DataType, Direction
from ..foundation.context.security_context import SecurityContext
from ..foundation.persistence.database import get_session
from ..identity.deps import require_role
from ..integration.bootstrap import build_adapter_registry
from ...shared.errors import ConfigurationError, NotFoundError
from .schemas import (
    ConfigView,
    ConnectivityResult,
    InstanceView,
    MappingReport,
    MappingRequest,
    MappingView,
    RegisterInstanceRequest,
    ReorderRequest,
    RoutingRuleRequest,
    RoutingRuleView,
)
from .service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_guard = require_role("ADMIN")
_adapters = build_adapter_registry()


def _svc(session: Session) -> AdminService:
    return AdminService(session, adapters=_adapters)


@router.post("/instances", response_model=InstanceView)
def register_instance(body: RegisterInstanceRequest, ctx: SecurityContext = Depends(_admin_guard), session: Session = Depends(get_session)):
    try:
        row = _svc(session).register_instance(body.erp_type, body.display_name, body.connection_ref)
        session.commit()
    except ConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return InstanceView(instance_id=row.id, erp_type=row.erp_type, display_name=row.display_name, status=row.status)


@router.get("/instances/{instance_id}/connectivity", response_model=ConnectivityResult)
def connectivity(instance_id: str, ctx: SecurityContext = Depends(_admin_guard), session: Session = Depends(get_session)):
    try:
        reachable = _svc(session).check_connectivity(instance_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="instance not found")
    return ConnectivityResult(instance_id=instance_id, reachable=reachable)


@router.post("/routing-rules", response_model=RoutingRuleView)
def define_rule(body: RoutingRuleRequest, ctx: SecurityContext = Depends(_admin_guard), session: Session = Depends(get_session)):
    try:
        row = _svc(session).define_routing_rule(
            body.order_index,
            [c.model_dump(mode="json") for c in body.conditions],
            body.target_instance_id,
            body.enabled,
        )
        session.commit()
    except ConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RoutingRuleView(rule_id=row.id, order_index=row.order_index, target_instance_id=row.target_instance_id, enabled=row.enabled)


@router.put("/routing-rules/order")
def reorder_rules(body: ReorderRequest, ctx: SecurityContext = Depends(_admin_guard), session: Session = Depends(get_session)):
    try:
        _svc(session).reorder_rules(body.ordered_rule_ids)
        session.commit()
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"reordered": True}


@router.post("/mappings", response_model=MappingReport)
def save_mapping(body: MappingRequest, ctx: SecurityContext = Depends(_admin_guard), session: Session = Depends(get_session)):
    try:
        row, unmapped = _svc(session).save_mapping(
            body.instance_id,
            body.data_type,
            body.direction,
            [e.model_dump(mode="json") for e in body.field_entries],
        )
        session.commit()
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    warnings = [f"required field '{f}' is unmapped" for f in unmapped]
    return MappingReport(mapping_id=row.id, unmapped_required=unmapped, warnings=warnings)


@router.get("/config", response_model=ConfigView)
def get_config(ctx: SecurityContext = Depends(_admin_guard), session: Session = Depends(get_session)):
    cfg = _svc(session).get_config()
    return ConfigView(
        instances=[InstanceView(instance_id=i.id, erp_type=i.erp_type, display_name=i.display_name, status=i.status) for i in cfg["instances"]],
        routing_rules=[RoutingRuleView(rule_id=r.id, order_index=r.order_index, target_instance_id=r.target_instance_id, enabled=r.enabled) for r in cfg["routing_rules"]],
        mappings=[MappingView(mapping_id=m.id, instance_id=m.instance_id, data_type=m.data_type, direction=m.direction) for m in cfg["mappings"]],
    )
