"""Deterministic baseline ordering for RecallNext planner evaluations.

These helpers do not claim a simulated operational improvement. They generate
the exact action orders that an evaluator can execute against a fixture and
measure with their own evidence-outcome simulator.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Mapping
from typing import Any

from .evidence_planner import rank_actions


def _value(item: Any, name: str, default: Any = None) -> Any:
    return item.get(name, default) if isinstance(item, Mapping) else getattr(item, name, default)


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
        "cheapest_first": sorted(ids, key=lambda action_id: (_value(by_id[action_id], "estimated_minutes"), action_id)),
        "highest_directly_involved_quantity_first": sorted(
            ids, key=lambda action_id: (-int(involved.get(action_id, 0)), action_id)
        ),
        "recallnext_ranking": [item["action_id"] for item in ranked],
    }
