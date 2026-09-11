"""Bounded exhaustive scenario generation for small incident components."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from itertools import product
from typing import Any


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _compositions(
    lot_bounds: list[tuple[str, int, int]], target: int
) -> list[list[tuple[str, int]]]:
    results: list[list[tuple[str, int]]] = []

    def visit(index: int, remaining: int, chosen: list[tuple[str, int]]) -> None:
        if index == len(lot_bounds):
            if remaining == 0:
                results.append(
                    [(lot_id, quantity) for lot_id, quantity in chosen if quantity]
                )
            return
        lot_id, minimum, maximum = lot_bounds[index]
        lower = max(
            minimum, remaining - sum(item[2] for item in lot_bounds[index + 1 :])
        )
        upper = min(
            maximum, remaining - sum(item[1] for item in lot_bounds[index + 1 :])
        )
        for quantity in range(lower, upper + 1):
            visit(index + 1, remaining - quantity, [*chosen, (lot_id, quantity)])

    visit(0, target, [])
    return results


def generate_feasible_scenarios(
    candidate_edges: Iterable[Mapping[str, Any]],
    shipments: Iterable[Mapping[str, Any]],
    lots: Iterable[Mapping[str, Any]],
    *,
    candidate_universe_complete: bool,
    closed_inventory: bool = True,
    max_combinations: int = 250_000,
    max_scenarios: int = 10_000,
) -> dict[str, Any]:
    """Enumerate allocations for a small component or fail without partial output."""
    if not candidate_universe_complete:
        return {
            "candidate_allocations": [],
            "solver_status": "INCOMPLETE_CANDIDATE_UNIVERSE",
            "candidate_universe_complete": False,
        }

    shipment_rows = list(shipments)
    lot_rows = list(lots)
    shipment_quantities = {
        str(item["shipment_id"]): _integer(item["quantity_cases"], "shipment quantity")
        for item in shipment_rows
    }
    if len(shipment_quantities) != len(shipment_rows):
        return {
            "candidate_allocations": [],
            "solver_status": "DUPLICATE_SHIPMENT_ID",
            "candidate_universe_complete": False,
        }
    lot_quantities = {
        str(item["lot_id"]): _integer(item["quantity_cases"], "lot quantity")
        for item in lot_rows
    }
    if len(lot_quantities) != len(lot_rows):
        return {
            "candidate_allocations": [],
            "solver_status": "DUPLICATE_LOT_ID",
            "candidate_universe_complete": False,
        }
    groups: dict[tuple[str, str], list[tuple[str, int, int]]] = defaultdict(list)
    group_targets: dict[tuple[str, str], int] = {}
    group_lots: set[tuple[str, str, str]] = set()
    for edge in candidate_edges:
        shipment_id = str(edge["shipment_id"])
        container_id = str(edge.get("container_id", "UNSPECIFIED"))
        lot_id = str(edge["lot_id"])
        if shipment_id not in shipment_quantities or lot_id not in lot_quantities:
            return {
                "candidate_allocations": [],
                "solver_status": "INVALID_CANDIDATE_EDGE",
                "candidate_universe_complete": False,
            }
        edge_identity = (shipment_id, container_id, lot_id)
        if edge_identity in group_lots or "group_quantity_cases" not in edge:
            return {
                "candidate_allocations": [],
                "solver_status": "INVALID_CANDIDATE_EDGE",
                "candidate_universe_complete": False,
            }
        group_lots.add(edge_identity)
        target = _integer(edge["group_quantity_cases"], "group quantity")
        key = (shipment_id, container_id)
        if key in group_targets and group_targets[key] != target:
            return {
                "candidate_allocations": [],
                "solver_status": "INVALID_CANDIDATE_EDGE",
                "candidate_universe_complete": False,
            }
        group_targets[key] = target
        groups[(shipment_id, container_id)].append(
            (
                lot_id,
                _integer(edge.get("min_quantity_cases", 0), "minimum quantity"),
                _integer(edge["max_quantity_cases"], "maximum quantity"),
            )
        )

    if set(shipment_quantities) != {key[0] for key in groups}:
        return {
            "candidate_allocations": [],
            "solver_status": "MISSING_SHIPMENT_CANDIDATES",
            "candidate_universe_complete": False,
        }

    choices: list[tuple[tuple[str, str], list[list[tuple[str, int]]]]] = []
    group_totals: dict[str, int] = defaultdict(int)
    for key in sorted(groups):
        bounds = sorted(groups[key])
        target = group_targets[key]
        group_totals[key[0]] += target
        allocations = _compositions(bounds, target)
        if not allocations:
            return {
                "candidate_allocations": [],
                "solver_status": "INFEASIBLE",
                "candidate_universe_complete": True,
            }
        choices.append((key, allocations))
    if dict(group_totals) != shipment_quantities:
        return {
            "candidate_allocations": [],
            "solver_status": "INVALID_GROUP_TOTAL",
            "candidate_universe_complete": False,
        }

    total_combinations = 1
    for _, allocations in choices:
        total_combinations *= len(allocations)
        if total_combinations > max_combinations:
            return {
                "candidate_allocations": [],
                "solver_status": "LIMIT_REACHED",
                "candidate_universe_complete": False,
            }

    scenarios: list[list[dict[str, Any]]] = []
    for selection in product(*(allocations for _, allocations in choices)):
        used: dict[str, int] = defaultdict(int)
        scenario: list[dict[str, Any]] = []
        for ((shipment_id, container_id), _), allocation in zip(choices, selection):
            for lot_id, quantity in allocation:
                used[lot_id] += quantity
                scenario.append(
                    {
                        "shipment_id": shipment_id,
                        "container_id": container_id,
                        "lot_id": lot_id,
                        "quantity_cases": quantity,
                    }
                )
        if any(used[lot_id] > quantity for lot_id, quantity in lot_quantities.items()):
            continue
        if closed_inventory and dict(used) != lot_quantities:
            continue
        scenarios.append(
            sorted(
                scenario,
                key=lambda row: (
                    row["shipment_id"],
                    row["container_id"],
                    row["lot_id"],
                ),
            )
        )
        if len(scenarios) > max_scenarios:
            return {
                "candidate_allocations": [],
                "solver_status": "LIMIT_REACHED",
                "candidate_universe_complete": False,
            }

    return {
        "candidate_allocations": scenarios,
        "solver_status": "SUCCESS" if scenarios else "INFEASIBLE",
        "candidate_universe_complete": True,
        "diagnostics": {
            "examined_combinations": total_combinations,
            "feasible_scenarios": len(scenarios),
        },
    }
