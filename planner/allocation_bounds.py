"""Conservative shipment classification from validated feasible allocations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from .models import (
    CONFIRMED_INCLUSION,
    EXCLUDED_UNDER_ASSUMPTIONS,
    POSSIBLE_INCLUSION,
    UNRESOLVED,
)


def _value(item: Any, name: str, default: Any = None) -> Any:
    return (
        item.get(name, default)
        if isinstance(item, Mapping)
        else getattr(item, name, default)
    )


def _identifier(item: Any, name: str) -> str:
    value = str(_value(item, name, "")).strip()
    if not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _quantity(item: Any, name: str = "quantity_cases") -> int:
    quantity = _value(item, name)
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return quantity


def _classify(minimum: int, maximum: int) -> str:
    if minimum > 0:
        return CONFIRMED_INCLUSION
    if maximum > 0:
        return POSSIBLE_INCLUSION
    return EXCLUDED_UNDER_ASSUMPTIONS


def _unresolved_results(
    shipments: list[Any], assumptions: dict[str, Any], solver_status: str
) -> list[dict[str, Any]]:
    safe_assumptions = {**assumptions, "solver_status": solver_status}
    return [
        {
            "shipment_id": _identifier(shipment, "shipment_id"),
            "min_recalled_cases": 0,
            "max_recalled_cases": _quantity(shipment),
            "held_cases": _quantity(shipment),
            "status": UNRESOLVED,
            "solver_status": solver_status,
            "assumptions": safe_assumptions,
        }
        for shipment in shipments
    ]


def _validate_scenarios(
    lots: list[Any],
    shipments: list[Any],
    scenarios: list[list[Any]],
    assumptions: Mapping[str, Any],
) -> None:
    shipment_quantities = {
        _identifier(shipment, "shipment_id"): _quantity(shipment)
        for shipment in shipments
    }
    if len(shipment_quantities) != len(shipments):
        raise ValueError("shipment_id values must be unique")
    lot_quantities = {_identifier(lot, "lot_id"): _quantity(lot) for lot in lots}
    if len(lot_quantities) != len(lots):
        raise ValueError("lot_id values must be unique")
    closed_inventory = assumptions.get("inventory_balance_mode") == "CLOSED"

    for scenario in scenarios:
        by_shipment: dict[str, int] = defaultdict(int)
        by_lot: dict[str, int] = defaultdict(int)
        for row in scenario:
            shipment_id = _identifier(row, "shipment_id")
            lot_id = _identifier(row, "lot_id")
            if shipment_id not in shipment_quantities:
                raise ValueError(
                    f"scenario contains unknown shipment_id {shipment_id!r}"
                )
            if lot_quantities and lot_id not in lot_quantities:
                raise ValueError(f"scenario contains unknown lot_id {lot_id!r}")
            quantity = _quantity(row)
            by_shipment[shipment_id] += quantity
            by_lot[lot_id] += quantity
        if by_shipment != shipment_quantities:
            raise ValueError(
                "every scenario must exactly satisfy every shipment quantity"
            )
        if lot_quantities:
            if any(
                by_lot[lot_id] > quantity for lot_id, quantity in lot_quantities.items()
            ):
                raise ValueError("scenario exceeds available lot quantity")
            if closed_inventory and by_lot != lot_quantities:
                raise ValueError(
                    "closed inventory scenarios must conserve every lot quantity"
                )


def classify_shipments(
    lots: Iterable[Any],
    shipments: Iterable[Any],
    candidate_allocations: Iterable[Iterable[Any]],
    recalled_lot_ids: Iterable[str],
    assumptions: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Calculate bounds only after explicit completeness and scenario validation."""
    assumptions_dict = dict(assumptions or {})
    shipment_rows = list(shipments)
    lot_rows = list(lots)
    scenarios = [list(scenario) for scenario in candidate_allocations]
    solver_status = str(
        assumptions_dict.get("solver_status", "MISSING_VALIDATION_METADATA")
    ).upper()
    complete = assumptions_dict.get("candidate_universe_complete") is True
    if not complete or solver_status != "SUCCESS" or not scenarios:
        return _unresolved_results(shipment_rows, assumptions_dict, solver_status)
    try:
        _validate_scenarios(lot_rows, shipment_rows, scenarios, assumptions_dict)
    except (TypeError, ValueError):
        return _unresolved_results(shipment_rows, assumptions_dict, "INVALID_SCENARIO")

    recalled = {str(lot_id) for lot_id in recalled_lot_ids}
    results: list[dict[str, Any]] = []
    for shipment in shipment_rows:
        shipment_id = _identifier(shipment, "shipment_id")
        held_cases = _quantity(shipment)
        amounts = [
            sum(
                _quantity(row)
                for row in scenario
                if _identifier(row, "shipment_id") == shipment_id
                and _identifier(row, "lot_id") in recalled
            )
            for scenario in scenarios
        ]
        minimum, maximum = min(amounts), max(amounts)
        results.append(
            {
                "shipment_id": shipment_id,
                "min_recalled_cases": minimum,
                "max_recalled_cases": maximum,
                "held_cases": held_cases,
                "status": _classify(minimum, maximum),
                "solver_status": solver_status,
                "assumptions": assumptions_dict,
            }
        )
    return results
