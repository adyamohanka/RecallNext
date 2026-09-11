from planner.evidence_planner import rank_actions
from planner.models import EXCLUDED_UNDER_ASSUMPTIONS, POSSIBLE_INCLUSION, UNRESOLVED

CURRENT = [
    {
        "shipment_id": "S-1",
        "held_cases": 10,
        "status": POSSIBLE_INCLUSION,
    }
]


def test_unavailable_outcome_makes_worst_case_value_zero():
    actions = [{"action_id": "A-1", "estimated_minutes": 5}]
    outcomes = {
        "A-1": [
            {
                "outcome": "VALID",
                "decisions": [
                    {
                        "shipment_id": "S-1",
                        "held_cases": 10,
                        "status": EXCLUDED_UNDER_ASSUMPTIONS,
                    }
                ],
            },
            {
                "outcome": "UNAVAILABLE",
                "decisions": [
                    {"shipment_id": "S-1", "held_cases": 10, "status": UNRESOLVED}
                ],
            },
        ]
    }

    ranked = rank_actions(CURRENT, actions, outcomes)

    assert ranked[0]["worst_case_resolved_cases"] == 0
    assert ranked[0]["conditional_best_case_resolved_cases"] == 10


def test_dominated_action_is_removed_and_order_is_deterministic():
    actions = [
        {"action_id": "SLOW", "estimated_minutes": 10},
        {"action_id": "FAST", "estimated_minutes": 5},
    ]
    resolved = [
        {
            "outcome": "VALID",
            "decisions": [
                {
                    "shipment_id": "S-1",
                    "held_cases": 10,
                    "status": EXCLUDED_UNDER_ASSUMPTIONS,
                }
            ],
        }
    ]

    ranked = rank_actions(CURRENT, actions, {"SLOW": resolved, "FAST": resolved})

    assert [item["action_id"] for item in ranked] == ["FAST"]


def test_retracted_evidence_does_not_preserve_a_previous_exclusion():
    """Reassessment after retraction returns to unresolved rather than clearing."""
    action = [{"action_id": "RETRACT", "estimated_minutes": 1}]
    retracted = {
        "RETRACT": [
            {
                "outcome": "CONFLICTING",
                "decisions": [
                    {"shipment_id": "S-1", "held_cases": 10, "status": UNRESOLVED}
                ],
            }
        ]
    }

    ranked = rank_actions(CURRENT, action, retracted)

    assert ranked[0]["worst_case_resolved_cases"] == 0
    assert ranked[0]["outcomes"][0]["remaining_unresolved_cases"] == 10


def test_conditional_value_prevents_incorrect_dominance():
    current = [
        {"shipment_id": "S-1", "held_cases": 10, "status": POSSIBLE_INCLUSION},
        {"shipment_id": "S-2", "held_cases": 90, "status": POSSIBLE_INCLUSION},
    ]
    actions = [
        {"action_id": "CHEAP", "estimated_minutes": 1},
        {"action_id": "VALUABLE", "estimated_minutes": 2},
    ]
    resolved = lambda shipment, cases: {
        "shipment_id": shipment,
        "held_cases": cases,
        "status": EXCLUDED_UNDER_ASSUMPTIONS,
    }
    outcomes = {
        "CHEAP": [
            {"outcome": "VALID", "decisions": [resolved("S-1", 10)]},
            {"outcome": "UNAVAILABLE"},
        ],
        "VALUABLE": [
            {
                "outcome": "VALID",
                "decisions": [resolved("S-1", 10), resolved("S-2", 90)],
            },
            {"outcome": "UNAVAILABLE"},
        ],
    }
    assert [item["action_id"] for item in rank_actions(current, actions, outcomes)] == [
        "VALUABLE",
        "CHEAP",
    ]


def test_partial_outcome_retains_omitted_shipment_uncertainty():
    current = [
        {"shipment_id": "S-1", "held_cases": 10, "status": POSSIBLE_INCLUSION},
        {"shipment_id": "S-2", "held_cases": 90, "status": POSSIBLE_INCLUSION},
    ]
    ranked = rank_actions(
        current,
        [{"action_id": "A", "estimated_minutes": 1}],
        {
            "A": [
                {
                    "outcome": "VALID",
                    "decisions": [
                        {
                            "shipment_id": "S-1",
                            "held_cases": 10,
                            "status": EXCLUDED_UNDER_ASSUMPTIONS,
                        }
                    ],
                }
            ]
        },
    )
    assert ranked[0]["outcomes"][0]["remaining_unresolved_cases"] == 90
