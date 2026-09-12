"""Fail-closed adapter from Exasol candidate rows to planner input.

The adapter accepts mapping-like rows so the backend can pass PyExasol results
without coupling the pure planner to a database client.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

SUCCESS = "SUCCESS"
MALFORMED_CANDIDATE_ROWS = "MALFORMED_CANDIDATE_ROWS"


def _field(row: Mapping[str, Any], name: str) -> Any:
    """Read lower- or upper-case SQL aliases without accepting missing data."""

    if name in row:
        return row[name]
    uppercase = name.upper()
    if uppercase in row:
        return row[uppercase]
    raise KeyError(name)


def _required_text(row: Mapping[str, Any], name: str) -> str:
    """Return a non-blank SQL identity without fabricating one from NULL."""

    value = _field(row, name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-blank string")
    return value.strip()


def planner_input_from_candidate_rows(
    shipments: Iterable[Mapping[str, Any]],
    candidate_rows: Iterable[Mapping[str, Any]],
    recalled_lot_ids: Iterable[str],
    *,
    solver_status: str = SUCCESS,
    candidate_universe_complete: bool = True,
) -> dict[str, Any]:
    """Return the exact input shape accepted by ``classify_shipments``.

    Required candidate columns are ``scenario_id``, ``shipment_id``,
    ``lot_source_id``, ``lot_code``, and ``quantity_cases``. A ``scenario_id``
    identifies one complete feasible allocation. If the query supplies rows
    without this grouping or contains malformed/duplicate rows, the adapter
    marks the universe incomplete instead of inventing allocations.
    """

    shipment_list = [dict(shipment) for shipment in shipments]
    assumptions = {
        "candidate_universe_complete": candidate_universe_complete is True,
        "solver_status": str(solver_status),
    }
    if (
        assumptions["solver_status"] != SUCCESS
        or not assumptions["candidate_universe_complete"]
    ):
        return {
            "shipments": shipment_list,
            "candidate_allocations": [],
            "recalled_lot_ids": list(recalled_lot_ids),
            "assumptions": assumptions,
        }

    scenarios: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str, str, int]] = set()
    try:
        for row in candidate_rows:
            scenario_id = _required_text(row, "scenario_id")
            shipment_id = _required_text(row, "shipment_id")
            lot_source_id = _required_text(row, "lot_source_id")
            lot_code = _required_text(row, "lot_code")
            quantity_cases = _field(row, "quantity_cases")
            if (
                not isinstance(quantity_cases, int)
                or isinstance(quantity_cases, bool)
                or quantity_cases < 0
            ):
                raise ValueError("quantity_cases must be a non-negative integer")
            dedupe_key = (
                scenario_id,
                shipment_id,
                f"{lot_source_id}:{lot_code}",
                quantity_cases,
            )
            if dedupe_key in seen:
                raise ValueError("duplicate candidate allocation row")
            seen.add(dedupe_key)
            scenarios.setdefault(scenario_id, []).append(
                {
                    "shipment_id": shipment_id,
                    "lot_id": f"{lot_source_id}:{lot_code}",
                    "quantity_cases": quantity_cases,
                }
            )
    except (AttributeError, KeyError, TypeError, ValueError):
        assumptions["candidate_universe_complete"] = False
        assumptions["solver_status"] = MALFORMED_CANDIDATE_ROWS
        scenarios = {}

    return {
        "shipments": shipment_list,
        "candidate_allocations": [scenarios[key] for key in sorted(scenarios)],
        "recalled_lot_ids": list(recalled_lot_ids),
        "assumptions": assumptions,
    }
