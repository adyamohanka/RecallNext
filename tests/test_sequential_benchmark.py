import json

from planner.integration import plan_incident
from planner.sequential_benchmark import (
    STRATEGIES,
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
