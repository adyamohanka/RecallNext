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
            "group_quantity_cases": 1,
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


def test_group_demand_uses_pick_quantity_not_largest_lot_cap():
    result = generate_feasible_scenarios(
        [
            {
                "shipment_id": "S1",
                "container_id": "C1",
                "lot_id": "L1",
                "group_quantity_cases": 10,
                "min_quantity_cases": 0,
                "max_quantity_cases": 6,
            },
            {
                "shipment_id": "S1",
                "container_id": "C1",
                "lot_id": "L2",
                "group_quantity_cases": 10,
                "min_quantity_cases": 0,
                "max_quantity_cases": 4,
            },
        ],
        [{"shipment_id": "S1", "quantity_cases": 10}],
        [
            {"lot_id": "L1", "quantity_cases": 6},
            {"lot_id": "L2", "quantity_cases": 4},
        ],
        candidate_universe_complete=True,
    )
    assert result["solver_status"] == "SUCCESS"
    assert result["candidate_allocations"] == [
        [
            {
                "shipment_id": "S1",
                "container_id": "C1",
                "lot_id": "L1",
                "quantity_cases": 6,
            },
            {
                "shipment_id": "S1",
                "container_id": "C1",
                "lot_id": "L2",
                "quantity_cases": 4,
            },
        ]
    ]


def test_missing_group_quantity_fails_closed():
    edges, shipments, lots = inputs()
    del edges[0]["group_quantity_cases"]
    result = generate_feasible_scenarios(
        edges, shipments, lots, candidate_universe_complete=True
    )
    assert result["solver_status"] == "INVALID_CANDIDATE_EDGE"
    assert result["candidate_allocations"] == []
    assert result["candidate_universe_complete"] is False


def test_duplicate_inventory_identifiers_block_scenario_generation():
    edges, shipments, lots = inputs()

    duplicate_shipment = generate_feasible_scenarios(
        edges,
        [*shipments, shipments[0]],
        lots,
        candidate_universe_complete=True,
    )
    duplicate_lot = generate_feasible_scenarios(
        edges,
        shipments,
        [*lots, lots[0]],
        candidate_universe_complete=True,
    )

    assert duplicate_shipment == {
        "candidate_allocations": [],
        "solver_status": "DUPLICATE_SHIPMENT_ID",
        "candidate_universe_complete": False,
    }
    assert duplicate_lot == {
        "candidate_allocations": [],
        "solver_status": "DUPLICATE_LOT_ID",
        "candidate_universe_complete": False,
    }
