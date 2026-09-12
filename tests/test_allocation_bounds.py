from planner.allocation_bounds import classify_shipments
from planner.models import (
    CONFIRMED_INCLUSION,
    EXCLUDED_UNDER_ASSUMPTIONS,
    POSSIBLE_INCLUSION,
    UNRESOLVED,
)
from planner.oracle import oracle_classify


SHIPMENTS = [
    {"shipment_id": "S-1", "quantity_cases": 10},
    {"shipment_id": "S-2", "quantity_cases": 10},
]


def test_classifies_confirmed_possible_and_excluded_from_feasible_scenarios():
    scenarios = [
        [
            {"shipment_id": "S-1", "lot_id": "RECALLED", "quantity_cases": 4},
            {"shipment_id": "S-2", "lot_id": "OTHER", "quantity_cases": 10},
        ],
        [
            {"shipment_id": "S-1", "lot_id": "RECALLED", "quantity_cases": 2},
            {"shipment_id": "S-2", "lot_id": "OTHER", "quantity_cases": 10},
        ],
    ]

    decisions = classify_shipments([], SHIPMENTS, scenarios, ["RECALLED"])

    assert decisions[0]["status"] == CONFIRMED_INCLUSION
    assert decisions[0]["min_recalled_cases"] == 2
    assert decisions[1]["status"] == EXCLUDED_UNDER_ASSUMPTIONS


def test_unknown_mapping_remains_possible_in_a_complete_candidate_universe():
    scenarios = [
        [{"shipment_id": "S-1", "lot_id": "RECALLED", "quantity_cases": 5}],
        [{"shipment_id": "S-2", "lot_id": "RECALLED", "quantity_cases": 5}],
    ]

    decisions = classify_shipments([], SHIPMENTS, scenarios, ["RECALLED"])

    assert [item["status"] for item in decisions] == [POSSIBLE_INCLUSION, POSSIBLE_INCLUSION]


def test_missing_coverage_cannot_exclude_a_shipment():
    decisions = classify_shipments(
        [], SHIPMENTS, [[]], ["RECALLED"], {"candidate_universe_complete": False}
    )

    assert all(item["status"] == UNRESOLVED for item in decisions)


def test_conflict_or_timeout_is_unresolved_even_when_no_recalled_row_exists():
    decisions = classify_shipments([], SHIPMENTS, [[]], ["RECALLED"], {"solver_status": "TIMEOUT"})

    assert all(item["status"] == UNRESOLVED for item in decisions)


def test_contradictory_evidence_is_unresolved_not_an_exclusion():
    decisions = classify_shipments([], SHIPMENTS, [[]], ["RECALLED"], {"solver_status": "CONFLICT"})

    assert all(item["status"] == UNRESOLVED for item in decisions)


def test_empty_feasible_set_is_unresolved_not_excluded():
    decisions = classify_shipments([], SHIPMENTS, [], ["RECALLED"])

    assert all(item["status"] == UNRESOLVED for item in decisions)


def test_infeasible_quantity_balance_is_unresolved_not_a_false_exclusion():
    scenarios = [[{"shipment_id": "S-1", "lot_id": "OTHER", "quantity_cases": 11}]]

    decisions = classify_shipments([], SHIPMENTS, scenarios, ["RECALLED"])

    assert all(item["status"] == UNRESOLVED for item in decisions)
    assert all(item["solver_status"] == "INFEASIBLE_CANDIDATE_ALLOCATION" for item in decisions)


def test_duplicate_candidate_rows_that_overfill_a_shipment_are_unresolved():
    scenarios = [
        [
            {"shipment_id": "S-1", "lot_id": "OTHER", "quantity_cases": 6},
            {"shipment_id": "S-1", "lot_id": "OTHER", "quantity_cases": 6},
        ]
    ]

    decisions = classify_shipments([], SHIPMENTS, scenarios, ["RECALLED"])

    assert all(item["status"] == UNRESOLVED for item in decisions)


def test_mixed_container_scan_cannot_clear_a_shipment_without_homogeneity_evidence():
    # The scan locates a recalled lot in one plausible allocation, but another
    # allocation still puts it in the shipment. A single scan cannot exclude it.
    scenarios = [
        [{"shipment_id": "S-1", "lot_id": "RECALLED", "quantity_cases": 4}],
        [{"shipment_id": "S-1", "lot_id": "OTHER", "quantity_cases": 4}],
    ]

    decisions = classify_shipments([], SHIPMENTS, scenarios, ["RECALLED"])

    assert decisions[0]["status"] == POSSIBLE_INCLUSION


def test_tiny_oracle_and_planner_agree():
    expected = oracle_classify(
        SHIPMENTS,
        ["RECALLED", "OTHER"],
        {"RECALLED": 1, "OTHER": 1},
        ["RECALLED"],
    )
    direct = classify_shipments(
        [],
        SHIPMENTS,
        [
            [
                {"shipment_id": "S-1", "lot_id": "RECALLED", "quantity_cases": 1},
                {"shipment_id": "S-1", "lot_id": "OTHER", "quantity_cases": 1},
            ],
            [
                {"shipment_id": "S-1", "lot_id": "RECALLED", "quantity_cases": 1},
                {"shipment_id": "S-2", "lot_id": "OTHER", "quantity_cases": 1},
            ],
            [
                {"shipment_id": "S-2", "lot_id": "RECALLED", "quantity_cases": 1},
                {"shipment_id": "S-1", "lot_id": "OTHER", "quantity_cases": 1},
            ],
            [
                {"shipment_id": "S-2", "lot_id": "RECALLED", "quantity_cases": 1},
                {"shipment_id": "S-2", "lot_id": "OTHER", "quantity_cases": 1},
            ],
        ],
        ["RECALLED"],
    )
    assert direct == expected


def test_oracle_does_not_call_the_production_classifier(monkeypatch):
    import planner.allocation_bounds

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("oracle must remain independent")

    monkeypatch.setattr(planner.allocation_bounds, "classify_shipments", fail_if_called)

    decisions = oracle_classify(SHIPMENTS, ["RECALLED"], {"RECALLED": 1}, ["RECALLED"])

    assert [decision["status"] for decision in decisions] == [POSSIBLE_INCLUSION, POSSIBLE_INCLUSION]


def test_same_lot_code_from_another_source_is_not_treated_as_recalled():
    scenarios = [
        [
            {"shipment_id": "S-1", "lot_id": "SOURCE-A:LOT-7", "quantity_cases": 4},
            {"shipment_id": "S-2", "lot_id": "SOURCE-B:LOT-7", "quantity_cases": 4},
        ]
    ]

    decisions = classify_shipments([], SHIPMENTS, scenarios, ["SOURCE-A:LOT-7"])

    assert decisions[0]["status"] == CONFIRMED_INCLUSION
    assert decisions[1]["status"] == EXCLUDED_UNDER_ASSUMPTIONS


def test_invalid_candidate_quantity_is_rejected_instead_of_silently_reconciled():
    scenarios = [[{"shipment_id": "S-1", "lot_id": "RECALLED", "quantity_cases": -1}]]

    import pytest

    with pytest.raises(ValueError, match="non-negative"):
        classify_shipments([], SHIPMENTS, scenarios, ["RECALLED"])
