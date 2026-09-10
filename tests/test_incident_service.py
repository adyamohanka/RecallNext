import pytest

from backend.contracts import ContractError
from backend.services.incident_service import IncidentService


class EmptyStatement:
    def fetchall(self):
        return []

    def fetchone(self):
        return None


class PreparedStatement:
    def __init__(self, sql):
        self.sql = sql
        self.rows = None

    def execute_prepared(self, rows):
        self.rows = list(rows)


class RecordingConnection:
    def __init__(self):
        self.executed = []
        self.prepared = []

    def execute(self, sql, parameters=None):
        self.executed.append((sql, parameters))
        return EmptyStatement()

    def create_prepared_statement(self, sql):
        statement = PreparedStatement(sql)
        self.prepared.append(statement)
        return statement


def test_persists_scenarios_with_deterministic_ids_and_contract_fields():
    connection = RecordingConnection()
    service = IncidentService(connection)

    service.persist_scenarios(
        "INC-DEMO-001",
        1,
        [
            [
                {
                    "shipment_id": "S-100",
                    "lot_id": "FARM-A:REC-2026-01",
                    "quantity_cases": 5,
                }
            ],
            [
                {
                    "shipment_id": "S-200",
                    "lot_id": "FARM-A:REC-2026-01",
                    "quantity_cases": 5,
                }
            ],
        ],
        candidate_universe_complete=True,
        solver_status="success",
        model_version="planner-v1",
        assumptions={"integer_cases": True},
    )

    assert len(connection.executed) == 2
    assert len(connection.prepared) == 2
    metadata = connection.prepared[0].rows
    allocations = connection.prepared[1].rows
    assert [row[2] for row in metadata] == ["SCN-000001", "SCN-000002"]
    assert all(row[4] == "SUCCESS" for row in metadata)
    assert [row[2] for row in allocations] == ["SCN-000001", "SCN-000002"]
    assert allocations[0][4:] == ("FARM-A:REC-2026-01", 5)


def test_success_requires_nonempty_scenario_and_source_qualified_lot():
    service = IncidentService(RecordingConnection())

    with pytest.raises(ContractError, match="at least one feasible scenario"):
        service.persist_scenarios(
            "INC-DEMO-001",
            1,
            [],
            candidate_universe_complete=True,
            solver_status="SUCCESS",
            model_version="planner-v1",
        )
    with pytest.raises(ContractError, match="source-qualified"):
        service.persist_scenarios(
            "INC-DEMO-001",
            1,
            [[{"shipment_id": "S-100", "lot_id": "LOT-7", "quantity_cases": 1}]],
            candidate_universe_complete=True,
            solver_status="SUCCESS",
            model_version="planner-v1",
        )


def test_failed_solver_can_be_persisted_without_fake_allocations():
    connection = RecordingConnection()
    service = IncidentService(connection)

    service.persist_scenarios(
        "INC-DEMO-001",
        1,
        [],
        candidate_universe_complete=False,
        solver_status="TIMEOUT",
        model_version="planner-v1",
    )

    assert len(connection.prepared) == 1
    metadata = connection.prepared[0].rows
    assert metadata[0][2] == "SCN-ERROR"
    assert metadata[0][3:5] == (False, "TIMEOUT")


def test_decision_persistence_rejects_unsafe_status_and_invalid_bounds():
    service = IncidentService(RecordingConnection())
    base = {
        "shipment_id": "S-100",
        "min_recalled_cases": 0,
        "max_recalled_cases": 5,
        "solver_status": "SUCCESS",
        "assumptions": {},
    }

    with pytest.raises(ContractError, match="unsupported decision status"):
        service.persist_decisions(
            "INC-DEMO-001",
            1,
            [{**base, "status": "SAFE"}],
            model_version="planner-v1",
        )
    with pytest.raises(ContractError, match="cannot exceed"):
        service.persist_decisions(
            "INC-DEMO-001",
            1,
            [
                {
                    **base,
                    "status": "POSSIBLE_INCLUSION",
                    "min_recalled_cases": 6,
                }
            ],
            model_version="planner-v1",
        )
