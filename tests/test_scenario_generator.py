from planner.scenario_generator import generate_feasible_scenarios


def inputs():
    lots = [{"lot_id": "R", "quantity_cases": 1}, {"lot_id": "G", "quantity_cases": 1}]
    shipments = [
        {"shipment_id": "S1", "quantity_cases": 1},
        {"shipment_id": "S2", "quantity_cases": 1},
    ]
    edges = [
        {
            "shipment_id": shipment,
            "container_id": shipment,
            "lot_id": lot,
            "min_quantity_cases": 0,
            "max_quantity_cases": 1,
        }
        for shipment in ("S1", "S2")
        for lot in ("R", "G")
    ]
    return edges, shipments, lots


def test_generates_complete_conserved_scenarios():
    result = generate_feasible_scenarios(*inputs(), candidate_universe_complete=True)
    assert result["solver_status"] == "SUCCESS"
    assert len(result["candidate_allocations"]) == 2


def test_limit_never_returns_a_partial_universe():
    result = generate_feasible_scenarios(
        *inputs(), candidate_universe_complete=True, max_combinations=1
    )
    assert result["candidate_allocations"] == []
    assert result["candidate_universe_complete"] is False
    assert result["solver_status"] == "LIMIT_REACHED"
