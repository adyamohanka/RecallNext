"""Stable pure planner entry point for the Exasol integration adapter."""
from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Any

from .allocation_bounds import classify_shipments


def plan_incident(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Classify a validated snapshot and return JSON-safe timing metadata."""
    started = perf_counter()
    decisions = classify_shipments(
        payload.get("lots", []), payload["shipments"], payload["candidate_allocations"],
        payload["recalled_lot_ids"], payload.get("assumptions", {}),
    )
    return {
        "decisions": decisions,
        "planner_seconds": perf_counter() - started,
        "scenario_count": len(payload["candidate_allocations"]),
        "model_version": str(payload.get("model_version", "bounded-enumerator-v1")),
    }
