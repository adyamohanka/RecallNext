"""Conservative shipment classification from a finite feasible allocation set."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .models import (
    CONFIRMED_INCLUSION,
    EXCLUDED_UNDER_ASSUMPTIONS,
    POSSIBLE_INCLUSION,
    UNRESOLVED,
)


def _value(item: Any, name: str) -> Any:
    return item.get(name) if isinstance(item, Mapping) else getattr(item, name)


def _shipment_id(item: Any) -> str:
    return str(_value(item, "shipment_id"))


def _quantity(item: Any) -> int:
    quantity = _value(item, "quantity_cases")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
        raise ValueError("quantity_cases must be a non-negative integer")
    return quantity


def _classify(minimum: int, maximum: int) -> str:
    if minimum > 0:
        return CONFIRMED_INCLUSION
    if maximum > 0:
        return POSSIBLE_INCLUSION
    return EXCLUDED_UNDER_ASSUMPTIONS


def classify_shipments(
    lots: Iterable[Any],
    shipments: Iterable[Any],
    candidate_allocations: Iterable[Iterable[Any]],
    recalled_lot_ids: Iterable[str],
    assumptions: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return conservative recalled-case bounds for each shipment.

    ``candidate_allocations`` is a finite collection of *complete feasible*
    allocation scenarios. Each scenario contains rows with ``shipment_id``,
    ``lot_id`` and ``quantity_cases``. An empty scenario is a valid allocation;
    an empty collection of scenarios is a conflict and therefore unresolved.

    Set ``assumptions['candidate_universe_complete']`` to false, or provide a
    non-success ``solver_status``, to deliberately stop scope narrowing.
    """

    del lots  # Kept in the public interface for contract compatibility.
    assumptions_dict = dict(assumptions or {})
    solver_status = str(assumptions_dict.get("solver_status", "SUCCESS"))
    complete = assumptions_dict.get("candidate_universe_complete", True) is True
    shipment_rows = list(shipments)
    scenarios = [list(scenario) for scenario in candidate_allocations]
    recalled = {str(lot_id) for lot_id in recalled_lot_ids}

    if not complete or solver_status != "SUCCESS" or not scenarios:
        return [
            _unresolved(_shipment_id(shipment), _quantity(shipment), solver_status, assumptions_dict)
            for shipment in shipment_rows
        ]

    # Candidate scenarios are expected to be feasible before this planner sees
    # them. Still, reject a malformed or over-capacity scenario defensively:
    # treating it as evidence would make a false exclusion possible.
    capacities = {_shipment_id(shipment): _quantity(shipment) for shipment in shipment_rows}
    if not _scenarios_fit_shipments(scenarios, capacities):
        return [
            _unresolved(
                _shipment_id(shipment),
                _quantity(shipment),
                "INFEASIBLE_CANDIDATE_ALLOCATION",
                assumptions_dict,
            )
            for shipment in shipment_rows
        ]

    results: list[dict[str, Any]] = []
    for shipment in shipment_rows:
        shipment_id = _shipment_id(shipment)
        held_cases = _quantity(shipment)
        recalled_by_scenario: list[int] = []
        for scenario in scenarios:
            total = sum(
                _quantity(row)
                for row in scenario
                if _shipment_id(row) == shipment_id and str(_value(row, "lot_id")) in recalled
            )
            recalled_by_scenario.append(total)
        minimum, maximum = min(recalled_by_scenario), max(recalled_by_scenario)
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


def _unresolved(
    shipment_id: str, held_cases: int, solver_status: str, assumptions: dict[str, Any]
) -> dict[str, Any]:
    return {
        "shipment_id": shipment_id,
        "min_recalled_cases": 0,
        "max_recalled_cases": held_cases,
        "held_cases": held_cases,
        "status": UNRESOLVED,
        "solver_status": solver_status,
        "assumptions": assumptions,
    }


def _scenarios_fit_shipments(scenarios: list[list[Any]], capacities: Mapping[str, int]) -> bool:
    """Ensure every supplied allocation fits known shipment capacity."""

    for scenario in scenarios:
        allocated: dict[str, int] = {}
        for row in scenario:
            shipment_id = _shipment_id(row)
            if shipment_id not in capacities:
                return False
            allocated[shipment_id] = allocated.get(shipment_id, 0) + _quantity(row)
        if any(total > capacities[shipment_id] for shipment_id, total in allocated.items()):
            return False
    return True
