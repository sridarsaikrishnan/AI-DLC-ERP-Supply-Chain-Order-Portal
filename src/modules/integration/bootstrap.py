"""Bootstrap (LC-U3-6): register stub adapters and job handlers into U0.

Called from the app startup so the U0 WorkerHost can dispatch jobs to U3 handlers.
"""

from __future__ import annotations

from ..foundation.config.models import ErpType
from ..foundation.queue.models import JobType
from ..foundation.queue.worker import HandlerRegistry
from .adapter import AdapterRegistry
from .adapters.erpnext_stub import ErpNextStubAdapter
from .adapters.odoo_stub import OdooStubAdapter
from .handlers import make_handlers


def build_adapter_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(ErpType.ERP_NEXT, ErpNextStubAdapter())
    registry.register(ErpType.ODOO, OdooStubAdapter())
    return registry


def register_integration(handler_registry: HandlerRegistry) -> AdapterRegistry:
    adapters = build_adapter_registry()
    handlers = make_handlers(adapters)
    handler_registry.register(JobType.SUBMISSION, handlers["process_submission"])
    handler_registry.register(JobType.STATUS_SYNC, handlers["process_status_sync"])
    handler_registry.register(JobType.CORRECTIVE_ACTION, handlers["process_corrective_action"])
    return adapters
