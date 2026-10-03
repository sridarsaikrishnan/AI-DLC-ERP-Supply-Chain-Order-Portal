from __future__ import annotations

import pytest

from src.modules.reference.catalog.application.service import CatalogService
from src.modules.reference.catalog.domain.errors import ItemOwnershipConflict
from src.modules.reference.catalog.domain.events import ITEM_SYNCED
from src.modules.reference.catalog.infrastructure.memory import InMemoryItemRepository
from src.shared.messaging.facts import CollectingFactPublisher
from src.shared.types import ConnectionId


def _service() -> CatalogService:
    return CatalogService(InMemoryItemRepository(), CollectingFactPublisher())


def test_sync_new_item_assigns_owning_connection() -> None:
    svc = _service()
    item = svc.sync_item(sku="ANVIL", name="Anvil", owning_connection_id=ConnectionId("conn_1"))
    assert item.item_id.startswith("item_")
    assert item.owning_connection_id == ConnectionId("conn_1")


def test_resync_from_same_connection_updates_name() -> None:
    svc = _service()
    svc.sync_item(sku="ANVIL", name="Anvil", owning_connection_id=ConnectionId("conn_1"))
    updated = svc.sync_item(
        sku="ANVIL", name="Anvil XL", owning_connection_id=ConnectionId("conn_1")
    )
    assert updated.name == "Anvil XL"


def test_same_sku_from_different_connection_is_a_conflict() -> None:
    svc = _service()
    svc.sync_item(sku="ANVIL", name="Anvil", owning_connection_id=ConnectionId("conn_1"))
    with pytest.raises(ItemOwnershipConflict) as exc:
        svc.sync_item(sku="ANVIL", name="Anvil", owning_connection_id=ConnectionId("conn_2"))
    assert exc.value.existing_owner == ConnectionId("conn_1")
    assert exc.value.incoming_owner == ConnectionId("conn_2")


def test_sync_publishes_a_fact_each_time_including_on_resync() -> None:
    svc = _service()
    facts: CollectingFactPublisher = svc._facts  # type: ignore[attr-defined]
    svc.sync_item(sku="ANVIL", name="Anvil", owning_connection_id=ConnectionId("conn_1"))
    svc.sync_item(sku="ANVIL", name="Anvil XL", owning_connection_id=ConnectionId("conn_1"))

    assert [f.event_type for f in facts.published] == [ITEM_SYNCED, ITEM_SYNCED]
    assert facts.published[-1].payload["name"] == "Anvil XL"
    assert facts.published[-1].payload["sku"] == "ANVIL"
