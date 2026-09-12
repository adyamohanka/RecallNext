"""Independent exhaustive utilities for tiny allocation fixtures."""

from __future__ import annotations

from collections import defaultdict
from itertools import product
from typing import Any

from .models import CONFIRMED_INCLUSION, EXCLUDED_UNDER_ASSUMPTIONS, POSSIBLE_INCLUSION


def enumerate_binary_allocations(
    shipment_ids: list[str], lot_ids: list[str], quantities: dict[str, int]
) -> list[list[dict[str, Any]]]:
    if not shipment_ids:
        return []
    return [
        [
            {
                "shipment_id": shipment_id,
                "lot_id": lot_id,
                "quantity_cases": quantities[lot_id],
            }
            for lot_id, shipment_id in zip(lot_ids, assigned_shipments)
        ]
        for assigned_shipments in product(shipment_ids, repeat=len(lot_ids))
    ]


def oracle_classify_scenarios(
    shipments: list[dict[str, Any]],
    scenarios: list[list[dict[str, Any]]],
    recalled_lot_ids: list[str],
) -> list[dict[str, Any]]:
    """Compute bounds without importing or calling production classification."""
    recalled = set(recalled_lot_ids)
    results = []
    for shipment in shipments:
        shipment_id = shipment["shipment_id"]
        quantities = []
        for scenario in scenarios:
            by_shipment: dict[str, int] = defaultdict(int)
            for row in scenario:
                if row["lot_id"] in recalled:
                    by_shipment[row["shipment_id"]] += row["quantity_cases"]
            quantities.append(by_shipment[shipment_id])
        minimum, maximum = min(quantities), max(quantities)
        status = (
            CONFIRMED_INCLUSION
            if minimum > 0
            else POSSIBLE_INCLUSION
            if maximum > 0
            else EXCLUDED_UNDER_ASSUMPTIONS
        )
        results.append(
            {
                "shipment_id": shipment_id,
                "min_recalled_cases": minimum,
                "max_recalled_cases": maximum,
                "status": status,
            }
        )
    return results


def oracle_classify(
    shipments: list[dict[str, Any]],
    lot_ids: list[str],
    quantities: dict[str, int],
    recalled_lot_ids: list[str],
) -> list[dict[str, Any]]:
    scenarios = enumerate_binary_allocations(
        [s["shipment_id"] for s in shipments], lot_ids, quantities
    )
    return oracle_classify_scenarios(shipments, scenarios, recalled_lot_ids)
