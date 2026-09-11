from planner.allocation_bounds import classify_shipments
from planner.models import (
    CONFIRMED_INCLUSION,
    EXCLUDED_UNDER_ASSUMPTIONS,
    POSSIBLE_INCLUSION,
    UNRESOLVED,
)
from planner.oracle import oracle_classify_scenarios

LOTS = [
    {"lot_id": "SOURCE-A:RECALLED", "quantity_cases": 10},
    {"lot_id": "SOURCE-B:OTHER", "quantity_cases": 10},
]
SHIPMENTS = [
    {"shipment_id": "S-1", "quantity_cases": 10},
    {"shipment_id": "S-2", "quantity_cases": 10},
]
SUCCESS = {
    "candidate_universe_complete": True,
    "solver_status": "SUCCESS",
    "inventory_balance_mode": "CLOSED",
}


def scenario(first_recalled: int):
    return [
        {
            "shipment_id": "S-1",
            "lot_id": "SOURCE-A:RECALLED",
            "quantity_cases": first_recalled,
        },
        {
            "shipment_id": "S-1",
            "lot_id": "SOURCE-B:OTHER",
            "quantity_cases": 10 - first_recalled,
        },
        {
            "shipment_id": "S-2",
            "lot_id": "SOURCE-A:RECALLED",
            "quantity_cases": 10 - first_recalled,
        },
        {
            "shipment_id": "S-2",
            "lot_id": "SOURCE-B:OTHER",
            "quantity_cases": first_recalled,
        },
    ]


def test_classifies_confirmed_possible_and_excluded():
    confirmed = classify_shipments(
        LOTS, SHIPMENTS, [scenario(4), scenario(2)], ["SOURCE-A:RECALLED"], SUCCESS
    )
    assert all(item["status"] == CONFIRMED_INCLUSION for item in confirmed)
    possible = classify_shipments(
        LOTS, SHIPMENTS, [scenario(10), scenario(0)], ["SOURCE-A:RECALLED"], SUCCESS
    )
    assert all(item["status"] == POSSIBLE_INCLUSION for item in possible)
    excluded = classify_shipments(
        LOTS, SHIPMENTS, [scenario(0)], ["SOURCE-B:OTHER"], SUCCESS
    )
    assert excluded[0]["status"] == CONFIRMED_INCLUSION
    assert excluded[1]["status"] == EXCLUDED_UNDER_ASSUMPTIONS


def test_metadata_is_required_for_scope_narrowing():
    result = classify_shipments(LOTS, SHIPMENTS, [scenario(0)], ["SOURCE-A:RECALLED"])
    assert all(item["status"] == UNRESOLVED for item in result)
    assert result[0]["solver_status"] == "MISSING_VALIDATION_METADATA"


def test_missing_coverage_timeout_and_empty_universe_are_unresolved():
    for assumptions, scenarios in [
        ({**SUCCESS, "candidate_universe_complete": False}, [scenario(0)]),
        ({**SUCCESS, "solver_status": "TIMEOUT"}, [scenario(0)]),
        (SUCCESS, []),
    ]:
        result = classify_shipments(
            LOTS, SHIPMENTS, scenarios, ["SOURCE-A:RECALLED"], assumptions
        )
        assert all(item["status"] == UNRESOLVED for item in result)


def test_unknown_or_empty_recalled_lot_reference_is_unresolved():
    for recalled in ([], ["SOURCE-A:TYPO"]):
        result = classify_shipments(LOTS, SHIPMENTS, [scenario(0)], recalled, SUCCESS)
        assert all(item["status"] == UNRESOLVED for item in result)
        assert result[0]["solver_status"] == "INVALID_RECALLED_LOT_REFERENCE"


def test_incomplete_or_unbalanced_scenario_is_unresolved():
    incomplete = [
        [{"shipment_id": "S-1", "lot_id": "SOURCE-A:RECALLED", "quantity_cases": 10}]
    ]
    result = classify_shipments(
        LOTS, SHIPMENTS, incomplete, ["SOURCE-A:RECALLED"], SUCCESS
    )
    assert all(item["status"] == UNRESOLVED for item in result)
    assert result[0]["solver_status"] == "INVALID_SCENARIO"


def test_independent_oracle_agrees_on_bounds_and_statuses():
    scenarios = [scenario(value) for value in range(11)]
    actual = classify_shipments(
        LOTS, SHIPMENTS, scenarios, ["SOURCE-A:RECALLED"], SUCCESS
    )
    expected = oracle_classify_scenarios(SHIPMENTS, scenarios, ["SOURCE-A:RECALLED"])
    for got, wanted in zip(actual, expected):
        assert {key: got[key] for key in wanted} == wanted


def test_same_code_from_another_source_is_distinct():
    lots = [
        {"lot_id": "A:LOT-7", "quantity_cases": 1},
        {"lot_id": "B:LOT-7", "quantity_cases": 1},
    ]
    shipments = [
        {"shipment_id": "S-1", "quantity_cases": 1},
        {"shipment_id": "S-2", "quantity_cases": 1},
    ]
    rows = [
        [
            {"shipment_id": "S-1", "lot_id": "A:LOT-7", "quantity_cases": 1},
            {"shipment_id": "S-2", "lot_id": "B:LOT-7", "quantity_cases": 1},
        ]
    ]
    decisions = classify_shipments(
        lots,
        shipments,
        rows,
        ["A:LOT-7"],
        {**SUCCESS, "inventory_balance_mode": "CLOSED"},
    )
    assert [item["status"] for item in decisions] == [
        CONFIRMED_INCLUSION,
        EXCLUDED_UNDER_ASSUMPTIONS,
    ]
