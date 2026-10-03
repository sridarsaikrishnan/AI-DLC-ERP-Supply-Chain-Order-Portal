"""Shipment aggregate — a minimal, record-only event-sourced aggregate (one command, one
event). Reuses the generic `EventSourcedRepository` kernel.

A shipment records a *dispatch* — carrier/tracking/proof-of-delivery — which is a distinct
fact from "delivered" (a downstream status). Split out of the former `fulfillment` module.
"""

from __future__ import annotations

from typing import Any

from src.shared.eventsourcing import Aggregate

from .events import ShipmentRecorded


class Shipment(Aggregate):
    aggregate_type = "Shipment"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.order_id: str = ""
        self.lines: list[dict[str, Any]] = []
        self.carrier: str | None = None
        self.tracking_number: str | None = None
        self.proof_of_delivery: str | None = None

    @classmethod
    def record(
        cls,
        *,
        shipment_id: str,
        order_id: str,
        lines: list[dict[str, Any]],
        carrier: str | None = None,
        tracking_number: str | None = None,
        proof_of_delivery: str | None = None,
    ) -> Shipment:
        if not lines:
            raise ValueError("a shipment must have at least one line")
        s = cls(shipment_id)
        s.emit(
            ShipmentRecorded(
                shipment_id=shipment_id,
                order_id=order_id,
                lines=lines,
                carrier=carrier,
                tracking_number=tracking_number,
                proof_of_delivery=proof_of_delivery,
            )
        )
        return s

    def _apply_ShipmentRecorded(self, e: ShipmentRecorded) -> None:
        self.order_id = e.order_id
        self.lines = list(e.lines)
        self.carrier = e.carrier
        self.tracking_number = e.tracking_number
        self.proof_of_delivery = e.proof_of_delivery

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "lines": self.lines,
            "carrier": self.carrier,
            "tracking_number": self.tracking_number,
            "proof_of_delivery": self.proof_of_delivery,
        }

    def restore(self, state: dict[str, Any]) -> None:
        self.order_id = state["order_id"]
        self.lines = state["lines"]
        self.carrier = state["carrier"]
        self.tracking_number = state["tracking_number"]
        self.proof_of_delivery = state.get("proof_of_delivery")
