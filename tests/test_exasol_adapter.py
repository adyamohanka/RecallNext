from planner import classify_shipments, planner_input_from_candidate_rows
from planner.models import POSSIBLE_INCLUSION, UNRESOLVED

SHIPMENTS = [
    {"shipment_id": "S-1", "quantity_cases": 10},
    {"shipment_id": "S-2", "quantity_cases": 10},
]


LOTS = [
    {"lot_id": "FARM-A:REC", "quantity_cases": 10},
    {"lot_id": "FARM-A:OTHER", "quantity_cases": 10},
]


def test_groups_source_qualified_sql_rows_into_stable_scenarios():
    rows = [
        {"scenario_id": "B", "shipment_id": "S-2", "lot_source_id": "FARM-A", "lot_code": "REC", "quantity_cases": 10},
        {"scenario_id": "A", "shipment_id": "S-1", "lot_source_id": "FARM-A", "lot_code": "REC", "quantity_cases": 10},
        {"scenario_id": "A", "shipment_id": "S-2", "lot_source_id": "FARM-A", "lot_code": "OTHER", "quantity_cases": 10},
        {"scenario_id": "B", "shipment_id": "S-1", "lot_source_id": "FARM-A", "lot_code": "OTHER", "quantity_cases": 10},
    ]

    adapter_input = planner_input_from_candidate_rows(SHIPMENTS, rows, ["FARM-A:REC"])
    decisions = classify_shipments(LOTS, **adapter_input)

    assert adapter_input["candidate_allocations"][0][0]["shipment_id"] == "S-1"
    assert [decision["status"] for decision in decisions] == [POSSIBLE_INCLUSION, POSSIBLE_INCLUSION]


def test_missing_scenario_grouping_fails_closed_as_unresolved():
    rows = [{"shipment_id": "S-1", "lot_source_id": "FARM-A", "lot_code": "REC", "quantity_cases": 4}]

    adapter_input = planner_input_from_candidate_rows(SHIPMENTS, rows, ["FARM-A:REC"])
    decisions = classify_shipments(LOTS, **adapter_input)

    assert adapter_input["assumptions"]["candidate_universe_complete"] is False
    assert all(decision["status"] == UNRESOLVED for decision in decisions)


def test_duplicate_candidate_rows_fail_closed():
    row = {"scenario_id": "A", "shipment_id": "S-1", "lot_source_id": "FARM-A", "lot_code": "REC", "quantity_cases": 4}

    adapter_input = planner_input_from_candidate_rows(SHIPMENTS, [row, row], ["FARM-A:REC"])

    assert adapter_input["assumptions"]["solver_status"] == "MALFORMED_CANDIDATE_ROWS"


def test_sql_null_or_blank_identity_fields_fail_closed_instead_of_becoming_strings():
    base_row = {
        "scenario_id": "A",
        "shipment_id": "S-1",
        "lot_source_id": "FARM-A",
        "lot_code": "REC",
        "quantity_cases": 4,
    }

    for field, invalid_value in (("scenario_id", None), ("shipment_id", "  "), ("lot_source_id", None), ("lot_code", "")):
        row = {**base_row, field: invalid_value}
        adapter_input = planner_input_from_candidate_rows(SHIPMENTS, [row], ["FARM-A:REC"])
        decisions = classify_shipments(LOTS, **adapter_input)

        assert adapter_input["assumptions"]["candidate_universe_complete"] is False
        assert all(decision["status"] == UNRESOLVED for decision in decisions)


def test_partial_sql_scenarios_remain_unresolved_with_explicit_inventory():
    rows = [{"scenario_id": "A", "shipment_id": "S-1", "lot_source_id": "FARM-A", "lot_code": "REC", "quantity_cases": 4}]
    adapter_input = planner_input_from_candidate_rows(SHIPMENTS, rows, ["FARM-A:REC"])
    decisions = classify_shipments(LOTS, **adapter_input)
    assert all(decision["status"] == UNRESOLVED for decision in decisions)
    assert all(decision["solver_status"] == "INVALID_SCENARIO" for decision in decisions)
