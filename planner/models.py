"""Stable JSON-friendly models used by the RecallNext planner.

The planner intentionally accepts mappings as well as these dataclasses so SQL
and API adapters can supply their own serialization without coupling core logic
to a framework.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

CONFIRMED_INCLUSION = "CONFIRMED_INCLUSION"
POSSIBLE_INCLUSION = "POSSIBLE_INCLUSION"
EXCLUDED_UNDER_ASSUMPTIONS = "EXCLUDED_UNDER_ASSUMPTIONS"
UNRESOLVED = "UNRESOLVED"

FIXED_STATUSES = frozenset(
    {
        CONFIRMED_INCLUSION,
        POSSIBLE_INCLUSION,
        EXCLUDED_UNDER_ASSUMPTIONS,
        UNRESOLVED,
    }
)


@dataclass(frozen=True)
class Allocation:
    """One feasible allocation of recalled and non-recalled cases to shipments."""

    shipment_id: str
    lot_id: str
    quantity_cases: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShipmentDecision:
    shipment_id: str
    min_recalled_cases: int
    max_recalled_cases: int
    held_cases: int
    status: str
    solver_status: str
    assumptions: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
