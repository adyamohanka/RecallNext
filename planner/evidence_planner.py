"""One-step conservative ranking of obtainable evidence actions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .models import (
    CONFIRMED_INCLUSION,
    EXCLUDED_UNDER_ASSUMPTIONS,
    UNRESOLVED,
)


RESOLVED_STATUSES = frozenset({CONFIRMED_INCLUSION, EXCLUDED_UNDER_ASSUMPTIONS})
NON_NARROWING_OUTCOMES = frozenset({"UNAVAILABLE", "ILLEGIBLE", "CONFLICTING", "REJECTED"})


def _value(item: Any, name: str, default: Any = None) -> Any:
    return item.get(name, default) if isinstance(item, Mapping) else getattr(item, name, default)


def _decisions_by_shipment(decisions: Iterable[Any]) -> dict[str, Any]:
    return {str(_value(decision, "shipment_id")): decision for decision in decisions}


def _resolved_cases(current: Any, future: Any) -> int:
    """Count held cases that become a completed conservative decision."""

    if _value(current, "status") in RESOLVED_STATUSES:
        return 0
    if _value(future, "status") not in RESOLVED_STATUSES:
        return 0
    return int(_value(current, "held_cases", _value(current, "max_recalled_cases", 0)))


def _outcome_metrics(current: list[Any], outcome: Mapping[str, Any]) -> dict[str, int]:
    current_by_shipment = _decisions_by_shipment(current)
    future_by_shipment = _decisions_by_shipment(outcome.get("decisions", []))
    if str(outcome.get("outcome", "VALID")).upper() in NON_NARROWING_OUTCOMES:
        return {
            "resolved_cases": 0,
            "newly_excluded_cases": 0,
            "newly_confirmed_cases": 0,
            "remaining_unresolved_cases": sum(
                int(_value(decision, "held_cases", 0))
                for decision in current
                if _value(decision, "status") not in RESOLVED_STATUSES
            ),
        }

    resolved = excluded = confirmed = 0
    for shipment_id, before in current_by_shipment.items():
        after = future_by_shipment.get(shipment_id)
        if after is None:
            continue
        changed_cases = _resolved_cases(before, after)
        resolved += changed_cases
        if _value(after, "status") == EXCLUDED_UNDER_ASSUMPTIONS:
            excluded += changed_cases
        if _value(after, "status") == CONFIRMED_INCLUSION:
            confirmed += changed_cases

    # Outcome payloads may report only changed shipments. Omitted shipments
    # retain their previous state; dropping them would undercount uncertainty.
    remaining = sum(
        int(_value(future_by_shipment.get(shipment_id, before), "held_cases", 0))
        for shipment_id, before in current_by_shipment.items()
        if _value(future_by_shipment.get(shipment_id, before), "status") not in RESOLVED_STATUSES
    )
    return {
        "resolved_cases": resolved,
        "newly_excluded_cases": excluded,
        "newly_confirmed_cases": confirmed,
        "remaining_unresolved_cases": remaining,
    }


def _is_dominated(candidate: dict[str, Any], competitors: list[dict[str, Any]]) -> bool:
    for other in competitors:
        if other is candidate:
            continue
        no_worse = (
            other["worst_case_resolved_cases"] >= candidate["worst_case_resolved_cases"]
            and other["conditional_best_case_resolved_cases"] >= candidate["conditional_best_case_resolved_cases"]
            and other["estimated_minutes"] <= candidate["estimated_minutes"]
        )
        strictly_better = (
            other["worst_case_resolved_cases"] > candidate["worst_case_resolved_cases"]
            or other["conditional_best_case_resolved_cases"] > candidate["conditional_best_case_resolved_cases"]
            or other["estimated_minutes"] < candidate["estimated_minutes"]
        )
        if no_worse and strictly_better:
            return True
    return False


def rank_actions(
    current_decisions: Iterable[Any], actions: Iterable[Any], outcome_scenarios: Mapping[str, Iterable[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Rank actions by conservative value, then conditional value and effort.

    ``outcome_scenarios`` maps an action id to all credible outcomes, including
    unavailable, illegible, and conflicting outcomes. Missing outcome coverage
    intentionally produces a zero worst-case score rather than an optimistic
    recommendation.
    """

    current = list(current_decisions)
    ranked: list[dict[str, Any]] = []
    for action in actions:
        action_id = str(_value(action, "action_id"))
        effort = _value(action, "estimated_minutes")
        if not isinstance(effort, (int, float)) or isinstance(effort, bool) or effort <= 0:
            raise ValueError("estimated_minutes must be a positive number")
        scenarios = list(outcome_scenarios.get(action_id, []))
        metrics = [_outcome_metrics(current, scenario) for scenario in scenarios]
        worst = min((metric["resolved_cases"] for metric in metrics), default=0)
        conditional = max((metric["resolved_cases"] for metric in metrics), default=0)
        ranked.append(
            {
                "action_id": action_id,
                "action_type": _value(action, "action_type"),
                "target_id": _value(action, "target_id"),
                "question": _value(action, "question"),
                "estimated_minutes": effort,
                "availability": _value(action, "availability", "UNKNOWN"),
                "worst_case_resolved_cases": worst,
                "conditional_best_case_resolved_cases": conditional,
                "worst_case_resolved_cases_per_minute": worst / effort,
                "outcomes": [
                    {"outcome": str(scenario.get("outcome", "VALID")).upper(), **metric}
                    for scenario, metric in zip(scenarios, metrics)
                ],
            }
        )

    survivors = [item for item in ranked if not _is_dominated(item, ranked)]
    survivors.sort(
        key=lambda item: (
            -item["worst_case_resolved_cases_per_minute"],
            -item["conditional_best_case_resolved_cases"],
            item["estimated_minutes"],
            item["action_id"],
        )
    )
    for item in survivors:
        item["ranking_reason"] = (
            "Ranked by worst-case resolved cases per minute; conditional benefit, "
            "effort, and action ID are deterministic tie-breakers."
        )
    return survivors
