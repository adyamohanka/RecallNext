"""Deterministic baseline ordering for RecallNext planner evaluations.

These helpers do not claim a simulated operational improvement. They generate
the exact action orders that an evaluator can execute against a fixture and
measure with their own evidence-outcome simulator.
"""

from __future__ import annotations

import random
import time
from collections.abc import Iterable, Mapping
from typing import Any

from .evidence_planner import RESOLVED_STATUSES, rank_actions
from .models import EXCLUDED_UNDER_ASSUMPTIONS


def _value(item: Any, name: str, default: Any = None) -> Any:
    return (
        item.get(name, default)
        if isinstance(item, Mapping)
        else getattr(item, name, default)
    )


def baseline_action_orders(
    current_decisions: Iterable[Any],
    actions: Iterable[Any],
    outcome_scenarios: Mapping[str, Iterable[Mapping[str, Any]]],
    directly_involved_cases: Mapping[str, int] | None = None,
    seed: int = 17,
) -> dict[str, list[str]]:
    """Return reproducible action orders for required baseline comparisons."""

    action_list = list(actions)
    by_id = {str(_value(action, "action_id")): action for action in action_list}
    ids = sorted(by_id)
    random_ids = ids[:]
    random.Random(seed).shuffle(random_ids)
    involved = dict(directly_involved_cases or {})
    ranked = rank_actions(current_decisions, action_list, outcome_scenarios)

    return {
        "hold_all_plausible_inventory": [],
        "random_action_order": random_ids,
        "cheapest_first": sorted(
            ids,
            key=lambda action_id: (
                _value(by_id[action_id], "estimated_minutes"),
                action_id,
            ),
        ),
        "highest_directly_involved_quantity_first": sorted(
            ids, key=lambda action_id: (-int(involved.get(action_id, 0)), action_id)
        ),
        "recallnext_ranking": [item["action_id"] for item in ranked],
    }


def evaluate_decision_trace(
    decision_trace: Iterable[Iterable[Any]],
    action_ids: Iterable[str],
    action_minutes: Mapping[str, float],
    ground_truth_recalled_cases: Mapping[str, int],
) -> dict[str, Any]:
    """Measure a simulated policy trace for tests and evaluation reports only.

    ``ground_truth_recalled_cases`` is deliberately explicit and must never be
    passed to production classification or action ranking. It lets a synthetic
    benchmark count dangerous false exclusions and unnecessary holds.
    """

    started = time.perf_counter()
    snapshots = [list(snapshot) for snapshot in decision_trace]
    if not snapshots:
        raise ValueError("decision_trace must contain at least the initial snapshot")
    expected_ids = [str(_value(decision, "shipment_id")) for decision in snapshots[0]]
    if len(set(expected_ids)) != len(expected_ids):
        raise ValueError("initial decision snapshot contains duplicate shipment IDs")
    if set(ground_truth_recalled_cases) != set(expected_ids):
        raise ValueError("ground truth must cover exactly the initial shipment IDs")
    for snapshot in snapshots:
        shipment_ids = [str(_value(decision, "shipment_id")) for decision in snapshot]
        if len(set(shipment_ids)) != len(shipment_ids):
            raise ValueError("decision snapshot contains duplicate shipment IDs")
        if set(shipment_ids) != set(expected_ids):
            raise ValueError("every decision snapshot must cover exactly the initial shipment IDs")
    selected_actions = list(action_ids)
    missing_effort = [action_id for action_id in selected_actions if action_id not in action_minutes]
    if missing_effort:
        raise ValueError(f"missing estimated minutes for actions: {', '.join(missing_effort)}")

    final = {str(_value(decision, "shipment_id")): decision for decision in snapshots[-1]}
    false_exclusions = 0
    unnecessary_holds = 0
    covered_cases = 0
    for shipment_id, decision in final.items():
        truth = int(ground_truth_recalled_cases.get(shipment_id, 0))
        status = _value(decision, "status")
        held = int(_value(decision, "held_cases", 0))
        if status == EXCLUDED_UNDER_ASSUMPTIONS and truth > 0:
            false_exclusions += truth
        if truth == 0 and status not in RESOLVED_STATUSES:
            unnecessary_holds += held
        if status in RESOLVED_STATUSES:
            covered_cases += held

    return {
        "actions": len(selected_actions),
        "simulated_minutes": sum(float(action_minutes[action_id]) for action_id in selected_actions),
        "false_excluded_cases": false_exclusions,
        "resolved_cases": covered_cases,
        "unnecessary_held_cases": unnecessary_holds,
        "snapshot_count": len(snapshots),
        "evaluation_seconds": time.perf_counter() - started,
    }
