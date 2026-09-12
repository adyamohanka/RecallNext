import json

from planner.integration import plan_incident
from planner.sequential_benchmark import (
    STRATEGIES,
    _apply_observation,
    _observation,
    default_manifest,
    run_sequential_benchmark,
)


def test_planner_result_is_json_safe_and_timed():
    manifest = default_manifest(); result = plan_incident({**manifest, "assumptions": {"candidate_universe_complete": True, "solver_status": "SUCCESS"}})
    assert result["planner_seconds"] >= 0; json.dumps(result)

def test_sequential_benchmark_is_fair_and_reproducible():
    first = run_sequential_benchmark(); second = run_sequential_benchmark()
    assert {run["strategy"] for run in first["runs"]} == set(STRATEGIES)
    assert len(first["runs"]) == 2 * 2 * 5 * 5
    assert all(run["simulated_minutes"] <= run["budget_minutes"] for run in first["runs"])
    assert all(len(run["selected_action_ids"]) == len(set(run["selected_action_ids"])) for run in first["runs"])
    assert [(r["strategy"], r["seed"], r["selected_action_ids"]) for r in first["runs"]] == [(r["strategy"], r["seed"], r["selected_action_ids"]) for r in second["runs"]]
    assert first == second
    assert "planner_seconds" not in first["runs"][0]


def test_an_action_filters_only_its_own_observation_not_full_truth():
    action = {"action_id": "CHECK-S1", "target_id": "S-1"}
    scenarios = [
        [{"shipment_id": "S-1", "lot_id": "REC", "quantity_cases": 5}, {"shipment_id": "S-2", "lot_id": "A", "quantity_cases": 5}, {"shipment_id": "S-3", "lot_id": "B", "quantity_cases": 5}],
        [{"shipment_id": "S-1", "lot_id": "REC", "quantity_cases": 5}, {"shipment_id": "S-2", "lot_id": "B", "quantity_cases": 5}, {"shipment_id": "S-3", "lot_id": "A", "quantity_cases": 5}],
        [{"shipment_id": "S-1", "lot_id": "A", "quantity_cases": 5}, {"shipment_id": "S-2", "lot_id": "REC", "quantity_cases": 5}, {"shipment_id": "S-3", "lot_id": "B", "quantity_cases": 5}],
    ]
    observed = _observation(action, scenarios[0])
    assert _apply_observation(action, observed, scenarios) == scenarios[:2]


def test_affordable_action_is_not_abandoned_after_over_budget_preference():
    manifest = default_manifest()
    manifest["budgets"] = [4]
    manifest["seeds"] = [11]
    manifest["actions"] = [
        {"action_id": "EXPENSIVE", "target_id": "S-2", "estimated_minutes": 7, "directly_involved_cases": 99},
        {"action_id": "AFFORDABLE", "target_id": "S-1", "estimated_minutes": 4, "directly_involved_cases": 1},
    ]
    runs = run_sequential_benchmark(manifest)["runs"]
    highest_first = [run for run in runs if run["strategy"] == "highest_directly_involved_quantity_first"]
    assert all(run["selected_action_ids"] == ["AFFORDABLE"] for run in highest_first)
