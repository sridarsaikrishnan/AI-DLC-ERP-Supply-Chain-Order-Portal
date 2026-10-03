"""ConnectionService — register and read ERP connections (operator-facing)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.shared.messaging.facts import FactPublisher, make_fact
from src.shared.types import ConnectionId, generate_id

from ..domain.errors import ConnectionNotFound
from ..domain.events import CONNECTION_PAUSED, CONNECTION_REGISTERED, CONNECTION_RESUMED
from ..domain.models import ConnectionStatus, ErpConnection, ErpType

if TYPE_CHECKING:
    from .ports import ConnectionRepository


class ConnectionService:
    def __init__(self, repository: ConnectionRepository, facts: FactPublisher) -> None:
        self._repository = repository
        self._facts = facts

    def register(
        self,
        *,
        erp_type: ErpType,
        instance_label: str,
        base_url: str,
        credentials: dict[str, str],
        secret_ref: str,
        webhook_secret_ref: str | None = None,
    ) -> ErpConnection:
        connection = ErpConnection(
            connection_id=ConnectionId(generate_id("conn")),
            erp_type=erp_type,
            instance_label=instance_label,
            base_url=base_url,
            credentials=credentials,
            secret_ref=secret_ref,
            status=ConnectionStatus.ACTIVE,
            webhook_secret_ref=webhook_secret_ref,
        )
        self._repository.add(connection)
        self._publish(connection, CONNECTION_REGISTERED)
        return connection

    def get(self, connection_id: ConnectionId) -> ErpConnection | None:
        return self._repository.get(connection_id)

    def pause(self, connection_id: ConnectionId) -> ErpConnection:
        """Stops new deliveries being routed here (`ConnectionsResolver.resolve` only
        returns active connections) without deleting anything it's referenced by."""
        connection = self._repository.get(connection_id)
        if connection is None:
            raise ConnectionNotFound(str(connection_id))
        connection.status = ConnectionStatus.PAUSED
        self._repository.update(connection)
        self._publish(connection, CONNECTION_PAUSED)
        return connection

    def resume(self, connection_id: ConnectionId) -> ErpConnection:
        connection = self._repository.get(connection_id)
        if connection is None:
            raise ConnectionNotFound(str(connection_id))
        connection.status = ConnectionStatus.ACTIVE
        self._repository.update(connection)
        self._publish(connection, CONNECTION_RESUMED)
        return connection

    def _publish(self, connection: ErpConnection, event_type: str) -> None:
        # Never the secret refs — a fact is a notification other domains may log/inspect,
        # not a place to leak credential pointers.
        self._facts.publish(
            make_fact(
                stream_id=str(connection.connection_id),
                aggregate_type="Connection",
                event_type=event_type,
                payload={
                    "connection_id": str(connection.connection_id),
                    "erp_type": connection.erp_type.value,
                    "instance_label": connection.instance_label,
                    "status": connection.status.value,
                },
            )
        )
