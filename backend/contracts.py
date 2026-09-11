"""Boundary checks between flat Exasol rows and Bhavyasha's planner."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any

PLANNER_SUCCESS = "SUCCESS"


class ContractError(ValueError):
    """Raised when database output could be misinterpreted by the planner."""


def source_qualified_lot_id(lot_source_id: object, lot_code: object) -> str:
    """Build the delimiter format already used by the planner branch."""

    if lot_source_id is None or lot_code is None:
        raise ContractError("lot_source_id and lot_code must both be non-empty")
    source = str(lot_source_id).strip()
    code = str(lot_code).strip()
    if not source or not code:
        raise ContractError("lot_source_id and lot_code must both be non-empty")
    if ":" in source or ":" in code:
        raise ContractError(
            "lot_source_id and lot_code cannot contain ':' in contract version 1"
        )
    return f"{source}:{code}"


def _quantity(value: object) -> int:
    if isinstance(value, bool):
        raise ContractError("quantity_cases must be a non-negative integer")
    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise ContractError("quantity_cases must be an integer")
        value = int(value)
    if not isinstance(value, int) or value < 0:
        raise ContractError("quantity_cases must be a non-negative integer")
    return value


def _boolean(value: object, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in {0, 1}:
        return bool(value)
    raise ContractError(f"{name} must be a boolean")


def _required_text(row: Mapping[str, Any], name: str) -> str:
    value = row.get(name)
    if value is None or not str(value).strip():
        raise ContractError(f"{name} must be a non-empty string")
    return str(value).strip()


def build_planner_payload(
    flat_scenario_rows: Iterable[Mapping[str, Any]],
    *,
    candidate_universe_complete: object,
    solver_status: object,
) -> dict[str, Any]:
    """Group flat Exasol scenario rows into the current planner input shape.

    A raw candidate edge is not a scenario. Callers must pass only complete,
    solver-verified scenarios. Duplicate shipment/lot rows are rejected instead
    of silently double-counting recalled quantity.
    """

    complete = _boolean(candidate_universe_complete, "candidate_universe_complete")
    normalized_solver_status = str(solver_status).strip().upper()
    if not normalized_solver_status:
        raise ContractError("solver_status must be a non-empty string")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()

    for row in flat_scenario_rows:
        scenario_id = _required_text(row, "scenario_id")
        shipment_id = _required_text(row, "shipment_id")
        expected_lot_id = source_qualified_lot_id(
            row.get("lot_source_id"), row.get("lot_code")
        )
        supplied_lot_id = row.get("lot_id")
        if supplied_lot_id is not None and str(supplied_lot_id) != expected_lot_id:
            raise ContractError(
                f"lot_id {supplied_lot_id!r} does not match {expected_lot_id!r}"
            )
        key = (scenario_id, shipment_id, expected_lot_id)
        if key in seen:
            raise ContractError(
                "duplicate allocation row for scenario, shipment, and lot"
            )
        seen.add(key)
        grouped[scenario_id].append(
            {
                "shipment_id": shipment_id,
                "lot_id": expected_lot_id,
                "quantity_cases": _quantity(row.get("quantity_cases")),
            }
        )

    scenarios: list[list[dict[str, Any]]] = []
    for scenario_id in sorted(grouped):
        allocations = sorted(
            grouped[scenario_id], key=lambda item: (item["shipment_id"], item["lot_id"])
        )
        scenarios.append(allocations)

    return {
        "candidate_allocations": scenarios,
        "assumptions": {
            "candidate_universe_complete": complete,
            "solver_status": normalized_solver_status,
        },
    }
