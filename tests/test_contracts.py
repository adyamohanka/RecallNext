from decimal import Decimal

import pytest

from backend.contracts import (
    ContractError,
    build_planner_payload,
    source_qualified_lot_id,
)


def test_groups_flat_rows_into_stable_complete_scenarios():
    rows = [
        {
            "scenario_id": "SCN-2",
            "shipment_id": "S-200",
            "lot_source_id": "FARM-A",
            "lot_code": "REC-2026-01",
            "lot_id": "FARM-A:REC-2026-01",
            "quantity_cases": Decimal(8),
        },
        {
            "scenario_id": "SCN-1",
            "shipment_id": "S-100",
            "lot_source_id": "FARM-A",
            "lot_code": "REC-2026-01",
            "lot_id": "FARM-A:REC-2026-01",
            "quantity_cases": Decimal(12),
        },
    ]

    payload = build_planner_payload(
        rows, candidate_universe_complete=True, solver_status="success"
    )

    assert payload == {
        "candidate_allocations": [
            [
                {
                    "shipment_id": "S-100",
                    "lot_id": "FARM-A:REC-2026-01",
                    "quantity_cases": 12,
                }
            ],
            [
                {
                    "shipment_id": "S-200",
                    "lot_id": "FARM-A:REC-2026-01",
                    "quantity_cases": 8,
                }
            ],
        ],
        "assumptions": {
            "candidate_universe_complete": True,
            "solver_status": "SUCCESS",
        },
    }


def test_source_qualified_key_matches_planner_contract():
    assert source_qualified_lot_id("FARM-A", "LOT-7") == "FARM-A:LOT-7"
    assert source_qualified_lot_id("FARM-A", "LOT-7") != "FARM-B:LOT-7"
    with pytest.raises(ContractError, match="non-empty"):
        source_qualified_lot_id(None, None)
    with pytest.raises(ContractError, match="cannot contain"):
        source_qualified_lot_id("FARM:A", "LOT-7")


def test_rejects_lot_key_mismatch_and_duplicate_allocation():
    row = {
        "scenario_id": "SCN-1",
        "shipment_id": "S-100",
        "lot_source_id": "FARM-A",
        "lot_code": "LOT-7",
        "lot_id": "FARM-A|LOT-7",
        "quantity_cases": 1,
    }
    with pytest.raises(ContractError, match="does not match"):
        build_planner_payload(
            [row], candidate_universe_complete=True, solver_status="SUCCESS"
        )

    corrected = {**row, "lot_id": "FARM-A:LOT-7"}
    with pytest.raises(ContractError, match="duplicate"):
        build_planner_payload(
            [corrected, corrected],
            candidate_universe_complete=True,
            solver_status="SUCCESS",
        )


@pytest.mark.parametrize("quantity", [-1, True, Decimal("1.5"), "1"])
def test_rejects_invalid_quantities(quantity):
    with pytest.raises(ContractError, match="quantity_cases"):
        build_planner_payload(
            [
                {
                    "scenario_id": "SCN-1",
                    "shipment_id": "S-100",
                    "lot_source_id": "FARM-A",
                    "lot_code": "LOT-7",
                    "quantity_cases": quantity,
                }
            ],
            candidate_universe_complete=True,
            solver_status="SUCCESS",
        )


def test_preserves_incomplete_or_failed_state_for_planner():
    payload = build_planner_payload(
        [], candidate_universe_complete=False, solver_status="timeout"
    )

    assert payload["candidate_allocations"] == []
    assert payload["assumptions"] == {
        "candidate_universe_complete": False,
        "solver_status": "TIMEOUT",
    }


def test_raw_edge_without_scenario_id_cannot_masquerade_as_scenario():
    with pytest.raises(ContractError, match="scenario_id"):
        build_planner_payload(
            [
                {
                    "shipment_id": "S-100",
                    "lot_source_id": "FARM-A",
                    "lot_code": "LOT-7",
                    "quantity_cases": 1,
                }
            ],
            candidate_universe_complete=True,
            solver_status="SUCCESS",
        )
