from planner.benchmarks import baseline_action_orders, evaluate_decision_trace
from planner.models import EXCLUDED_UNDER_ASSUMPTIONS, POSSIBLE_INCLUSION, UNRESOLVED


def test_baselines_are_stable_and_include_the_required_comparators():
    current = [{"shipment_id": "S-1", "held_cases": 8, "status": POSSIBLE_INCLUSION}]
    actions = [
        {"action_id": "A", "estimated_minutes": 5},
        {"action_id": "B", "estimated_minutes": 2},
    ]
    outcomes = {
        action["action_id"]: [
            {
                "outcome": "VALID",
                "decisions": [
                    {
                        "shipment_id": "S-1",
                        "held_cases": 8,
                        "status": EXCLUDED_UNDER_ASSUMPTIONS,
                    }
                ],
            }
        ]
        for action in actions
    }

    orders = baseline_action_orders(
        current, actions, outcomes, {"A": 1, "B": 9}, seed=7
    )

    assert orders["hold_all_plausible_inventory"] == []
    assert orders["cheapest_first"] == ["B", "A"]
    assert orders["highest_directly_involved_quantity_first"] == ["B", "A"]
    assert (
        orders["random_action_order"]
        == baseline_action_orders(current, actions, outcomes, {"A": 1, "B": 9}, seed=7)[
            "random_action_order"
        ]
    )
    assert orders["recallnext_ranking"] == ["B"]


def test_evaluation_reports_real_synthetic_trace_metrics_without_touching_production_planner():
    initial = [
        {"shipment_id": "S-1", "held_cases": 10, "status": POSSIBLE_INCLUSION},
        {"shipment_id": "S-2", "held_cases": 6, "status": UNRESOLVED},
    ]
    final = [
        {"shipment_id": "S-1", "held_cases": 10, "status": EXCLUDED_UNDER_ASSUMPTIONS},
        {"shipment_id": "S-2", "held_cases": 6, "status": UNRESOLVED},
    ]

    report = evaluate_decision_trace([initial, final], ["ACT-1"], {"ACT-1": 3}, {"S-1": 0, "S-2": 2})

    assert report["false_excluded_cases"] == 0
    assert report["resolved_cases"] == 10
    assert report["unnecessary_held_cases"] == 0
    assert report["actions"] == 1
    assert report["simulated_minutes"] == 3


def test_evaluation_rejects_incomplete_or_duplicate_decision_snapshots():
    import pytest

    snapshot = [{"shipment_id": "S-1", "held_cases": 1, "status": POSSIBLE_INCLUSION}]

    with pytest.raises(ValueError, match="ground truth"):
        evaluate_decision_trace([snapshot], [], {}, {})
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_decision_trace([snapshot + snapshot], [], {}, {"S-1": 0})
    with pytest.raises(ValueError, match="cover exactly"):
        evaluate_decision_trace([snapshot, []], [], {}, {"S-1": 0})
