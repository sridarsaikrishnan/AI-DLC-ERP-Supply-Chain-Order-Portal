"""ConnectionService — register and read ERP connections (operator-facing)."""

from __future__ import annotations

from src.shared.types import ConnectionId, generate_id

from ..domain.errors import ConnectionNotFound
from ..domain.models import ConnectionStatus, ErpConnection, ErpType
from .ports import ConnectionRepository


class ConnectionService:
    def __init__(self, repository: ConnectionRepository) -> None:
        self._repository = repository

    def register(
        self,
        *,
        erp_type: ErpType,
        instance_label: str,
        base_url: str,
        database: str,
        username: str,
        secret_ref: str,
        webhook_secret_ref: str | None = None,
    ) -> ErpConnection:
        connection = ErpConnection(
            connection_id=ConnectionId(generate_id("conn")),
            erp_type=erp_type,
            instance_label=instance_label,
            base_url=base_url,
            database=database,
            username=username,
            secret_ref=secret_ref,
            status=ConnectionStatus.ACTIVE,
            webhook_secret_ref=webhook_secret_ref,
        )
        self._repository.add(connection)
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
        return connection

    def resume(self, connection_id: ConnectionId) -> ErpConnection:
        connection = self._repository.get(connection_id)
        if connection is None:
            raise ConnectionNotFound(str(connection_id))
        connection.status = ConnectionStatus.ACTIVE
        self._repository.update(connection)
        return connection
