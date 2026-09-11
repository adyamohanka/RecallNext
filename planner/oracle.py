"""Independent tiny-instance exhaustive oracle for allocation bounds tests."""

from __future__ import annotations

from itertools import product
from typing import Any

from .models import CONFIRMED_INCLUSION, EXCLUDED_UNDER_ASSUMPTIONS, POSSIBLE_INCLUSION


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
    """Independently classify an exhaustive tiny candidate universe.

    This intentionally does not invoke production classification: it is the
    oracle used to detect a drift in the production bounds implementation.
    """

    scenarios = enumerate_binary_allocations(
        [shipment["shipment_id"] for shipment in shipments], lot_ids, quantities
    )
    recalled = set(recalled_lot_ids)
    decisions: list[dict[str, Any]] = []
    for shipment in shipments:
        shipment_id = shipment["shipment_id"]
        totals = [
            sum(
                row["quantity_cases"]
                for row in scenario
                if row["shipment_id"] == shipment_id and row["lot_id"] in recalled
            )
            for scenario in scenarios
        ]
        minimum, maximum = min(totals), max(totals)
        status = (
            CONFIRMED_INCLUSION
            if minimum > 0
            else POSSIBLE_INCLUSION
            if maximum > 0
            else EXCLUDED_UNDER_ASSUMPTIONS
        )
        decisions.append(
            {
                "shipment_id": shipment_id,
                "min_recalled_cases": minimum,
                "max_recalled_cases": maximum,
                "held_cases": shipment["quantity_cases"],
                "status": status,
                "solver_status": "SUCCESS",
                "assumptions": {},
            }
        )
    return decisions
