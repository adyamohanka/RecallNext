"""Deterministic sequential benchmark. Hidden truth is benchmark-only."""
from __future__ import annotations

import random
from collections.abc import Mapping
from typing import Any

from .evidence_planner import RESOLVED_STATUSES, rank_actions
from .integration import plan_incident
from .models import EXCLUDED_UNDER_ASSUMPTIONS

STRATEGIES = (
    "hold_all_plausible_inventory", "random_action_order", "cheapest_first",
    "highest_directly_involved_quantity_first", "recallnext_ranking",
)


def default_manifest() -> dict[str, Any]:
    """Committed synthetic manifest; every scenario is evaluated as hidden truth."""
    scenarios = [
        [{"shipment_id": "S-1", "lot_id": "FARM-A:REC", "quantity_cases": 5}, {"shipment_id": "S-2", "lot_id": "FARM-A:GOOD", "quantity_cases": 5}],
        [{"shipment_id": "S-1", "lot_id": "FARM-A:GOOD", "quantity_cases": 5}, {"shipment_id": "S-2", "lot_id": "FARM-A:REC", "quantity_cases": 5}],
    ]
    return {
        "fixture_version": "sequential-v1", "lots": [{"lot_id": "FARM-A:REC", "quantity_cases": 5}, {"lot_id": "FARM-A:GOOD", "quantity_cases": 5}],
        "shipments": [{"shipment_id": "S-1", "quantity_cases": 5}, {"shipment_id": "S-2", "quantity_cases": 5}],
        "candidate_allocations": scenarios, "recalled_lot_ids": ["FARM-A:REC"],
        "actions": [
            {"action_id": "ACT-LABEL-S1", "target_id": "S-1", "estimated_minutes": 4, "directly_involved_cases": 5},
            {"action_id": "ACT-MANIFEST-S2", "target_id": "S-2", "estimated_minutes": 7, "directly_involved_cases": 5},
        ], "budgets": [4, 11], "seeds": [11, 17, 23, 29, 31],
    }


def _payload(manifest: Mapping[str, Any], scenarios: list[list[dict[str, Any]]]) -> dict[str, Any]:
    return {"lots": manifest["lots"], "shipments": manifest["shipments"], "candidate_allocations": scenarios,
            "recalled_lot_ids": manifest["recalled_lot_ids"], "assumptions": {"candidate_universe_complete": True, "solver_status": "SUCCESS", "inventory_balance_mode": "CLOSED"}}


def _truth_cases(scenario: list[dict[str, Any]], recalled: set[str]) -> dict[str, int]:
    return {shipment: sum(row["quantity_cases"] for row in scenario if row["shipment_id"] == shipment and row["lot_id"] in recalled) for shipment in {row["shipment_id"] for row in scenario}}


def _observation(action: Mapping[str, Any], scenario: list[dict[str, Any]]) -> tuple[tuple[str, str, int], ...]:
    """Return only the rows observable through this action's declared target."""
    target = str(action["target_id"])
    return tuple(sorted(
        (str(row["shipment_id"]), str(row["lot_id"]), int(row["quantity_cases"]))
        for row in scenario
        if str(row["shipment_id"]) == target
    ))


def _apply_observation(
    action: Mapping[str, Any],
    observed: tuple[tuple[str, str, int], ...],
    scenarios: list[list[dict[str, Any]]],
) -> list[list[dict[str, Any]]]:
    """Keep candidates consistent with one action-specific observation only."""
    return [scenario for scenario in scenarios if _observation(action, scenario) == observed]


def _outcomes(manifest: Mapping[str, Any], scenarios: list[list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    outcomes: dict[str, list[dict[str, Any]]] = {}
    for action in manifest["actions"]:
        action_id = action["action_id"]
        possibilities = []
        seen: set[tuple[tuple[str, str, int], ...]] = set()
        for scenario in scenarios:
            observed = _observation(action, scenario)
            if observed in seen:
                continue
            seen.add(observed)
            filtered = _apply_observation(action, observed, scenarios)
            decisions = plan_incident(_payload(manifest, filtered))["decisions"]
            possibilities.append({"outcome": "VALID", "decisions": decisions})
        possibilities.append({"outcome": "UNAVAILABLE", "decisions": []})
        outcomes[action_id] = possibilities
    return outcomes


def _select(strategy: str, remaining: list[dict[str, Any]], decisions: list[dict[str, Any]], manifest: Mapping[str, Any], scenarios: list[list[dict[str, Any]]], seed: int) -> dict[str, Any] | None:
    if not remaining or strategy == "hold_all_plausible_inventory":
        return None
    if strategy == "random_action_order":
        return random.Random(seed).choice(sorted(remaining, key=lambda item: item["action_id"]))
    if strategy == "cheapest_first":
        return min(remaining, key=lambda item: (item["estimated_minutes"], item["action_id"]))
    if strategy == "highest_directly_involved_quantity_first":
        return min(remaining, key=lambda item: (-item["directly_involved_cases"], item["action_id"]))
    ranked = rank_actions(decisions, remaining, _outcomes(manifest, scenarios))
    return ranked[0] if ranked else None


def run_sequential_benchmark(manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run every strategy against every hidden scenario, seed, and budget."""
    manifest = dict(manifest or default_manifest())
    cases = list(enumerate(manifest["candidate_allocations"]))
    runs: list[dict[str, Any]] = []
    for truth_index, truth in cases:
        truth_cases = _truth_cases(truth, set(manifest["recalled_lot_ids"]))
        for budget in manifest["budgets"]:
            for seed in manifest["seeds"]:
                for strategy in STRATEGIES:
                    scenarios = list(manifest["candidate_allocations"]); remaining = list(manifest["actions"]); selected = []; outcomes = []; minutes = 0.0; trace = []
                    while True:
                        decisions = plan_incident(_payload(manifest, scenarios))["decisions"]; trace.append(decisions)
                        if all(item["status"] in RESOLVED_STATUSES for item in decisions): stop = "ALL_RESOLVED"; break
                        affordable = [item for item in remaining if minutes + item["estimated_minutes"] <= budget]
                        if remaining and not affordable:
                            stop = "BUDGET_EXHAUSTED"
                            break
                        choice = _select(strategy, affordable, decisions, manifest, scenarios, seed + len(selected))
                        if choice is None: stop = "NO_ACTION"; break
                        selected.append(choice["action_id"]); minutes += choice["estimated_minutes"]; remaining = [item for item in remaining if item["action_id"] != choice["action_id"]]
                        # The oracle supplies only this action's observed rows, never a full scenario.
                        observed = _observation(choice, truth)
                        scenarios = _apply_observation(choice, observed, scenarios)
                        outcomes.append("VALID")
                    final = trace[-1]; false_excluded = sum(truth_cases.get(item["shipment_id"], 0) for item in final if item["status"] == EXCLUDED_UNDER_ASSUMPTIONS)
                    total_truth = sum(truth_cases.values()); resolved = sum(item["held_cases"] for item in final if item["status"] in RESOLVED_STATUSES)
                    runs.append({"fixture_version": manifest["fixture_version"], "truth_scenario_id": f"SCN-{truth_index:03d}", "strategy": strategy, "seed": seed, "budget_minutes": budget, "selected_action_ids": selected, "outcomes": outcomes, "stop_reason": stop, "false_excluded_cases": false_excluded, "affected_case_coverage": 1.0 if total_truth == 0 else (total_truth - false_excluded) / total_truth, "resolved_cases": resolved, "unnecessary_held_cases": sum(item["held_cases"] for item in final if truth_cases.get(item["shipment_id"], 0) == 0 and item["status"] not in RESOLVED_STATUSES), "action_count": len(selected), "simulated_minutes": minutes, "error": None})
    # Intentionally excludes machine-dependent wall-clock values so artifacts are reproducible.
    return {"fixture_version": manifest["fixture_version"], "strategies": list(STRATEGIES), "budgets": manifest["budgets"], "seeds": manifest["seeds"], "truth_case_count": len(cases), "runs": runs}
