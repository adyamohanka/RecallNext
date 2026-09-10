"""Independent tiny-instance exhaustive oracle for allocation bounds tests."""

from __future__ import annotations

from itertools import product
from typing import Any

from .allocation_bounds import classify_shipments


def enumerate_binary_allocations(
    shipment_ids: list[str], lot_ids: list[str], quantities: dict[str, int]
) -> list[list[dict[str, Any]]]:
    """Enumerate allocations for tiny one-case lots.

    This intentionally simple oracle is for tests only. Each lot is assigned to
    one shipment; the total per lot comes from ``quantities``.
    """

    if not shipment_ids:
        return []
    scenarios: list[list[dict[str, Any]]] = []
    for assigned_shipments in product(shipment_ids, repeat=len(lot_ids)):
        scenarios.append(
            [
                {
                    "shipment_id": shipment_id,
                    "lot_id": lot_id,
                    "quantity_cases": quantities[lot_id],
                }
                for lot_id, shipment_id in zip(lot_ids, assigned_shipments)
            ]
        )
    return scenarios


def oracle_classify(
    shipments: list[dict[str, Any]], lot_ids: list[str], quantities: dict[str, int], recalled_lot_ids: list[str]
) -> list[dict[str, Any]]:
    """Classify an exhaustive tiny candidate universe using the public planner."""

    scenarios = enumerate_binary_allocations(
        [shipment["shipment_id"] for shipment in shipments], lot_ids, quantities
    )
    return classify_shipments([], shipments, scenarios, recalled_lot_ids)
