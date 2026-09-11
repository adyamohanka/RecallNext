from planner.benchmarks import baseline_action_orders
from planner.models import EXCLUDED_UNDER_ASSUMPTIONS, POSSIBLE_INCLUSION


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
