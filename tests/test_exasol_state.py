import json

import pytest

import backend.services.recall_workflow as workflow_module
from backend.services.exasol_state import (
    ConcurrentStateWriteError,
    ExasolWorkflowStateStore,
)
from backend.services.recall_workflow import ConflictError, default_workflow


class FakeStatement:
    def __init__(self, row=None, affected=0):
        self.row = row
        self.affected = affected

    def fetchone(self):
        return self.row

    def rowcount(self):
        return self.affected


class SharedStateTable:
    def __init__(self):
        self.payload = None


class FakeConnection:
    def __init__(self, table):
        self.table = table

    def execute(self, sql, parameters):
        if sql.startswith("SELECT STATE_JSON"):
            row = (
                {"state_json": self.table.payload}
                if self.table.payload is not None
                else None
            )
            return FakeStatement(row=row)
        if sql.startswith("INSERT INTO"):
            if self.table.payload is not None:
                return FakeStatement(affected=0)
            self.table.payload = parameters["state_json"]
            return FakeStatement(affected=1)
        if sql.startswith("UPDATE"):
            if self.table.payload != parameters["expected_state_json"]:
                return FakeStatement(affected=0)
            self.table.payload = parameters["state_json"]
            return FakeStatement(affected=1)
        raise AssertionError(f"Unexpected SQL: {sql}")


def test_compare_and_swap_rejects_stale_state_writer():
    table = SharedStateTable()
    first = ExasolWorkflowStateStore(FakeConnection(table), "INC-1")
    second = ExasolWorkflowStateStore(FakeConnection(table), "INC-1")

    assert first.load() is None
    assert second.load() is None
    first.save({"current_version": 1})

    with pytest.raises(ConcurrentStateWriteError, match="another API worker"):
        second.save({"current_version": 2})

    assert json.loads(table.payload) == {"current_version": 1}


def test_compare_and_swap_rejects_stale_update_writer():
    table = SharedStateTable()
    seed = ExasolWorkflowStateStore(FakeConnection(table), "INC-1")
    seed.load()
    seed.save({"current_version": 1})
    first = ExasolWorkflowStateStore(FakeConnection(table), "INC-1")
    second = ExasolWorkflowStateStore(FakeConnection(table), "INC-1")
    assert first.load() == {"current_version": 1}
    assert second.load() == {"current_version": 1}

    first.save({"current_version": 2})
    with pytest.raises(ConcurrentStateWriteError, match="another API worker"):
        second.save({"current_version": 3})

    assert json.loads(table.payload) == {"current_version": 2}


def test_workflow_resyncs_after_concurrent_write_conflict():
    table = SharedStateTable()
    first = default_workflow()
    second = default_workflow()
    first._state_store = ExasolWorkflowStateStore(
        FakeConnection(table), first.incident_id
    )
    second._state_store = ExasolWorkflowStateStore(
        FakeConnection(table), second.incident_id
    )
    first._restore_state()
    second._restore_state()

    action_id = first.actions[0]["action_id"]
    first_record = first.submit_evidence(
        {
            "action_id": action_id,
            "source_reference": "fixture://first-worker",
            "proposed_fact": first.example_fact(action_id),
            "content_hash": "first-worker-content",
            "review_status": "PENDING_REVIEW",
        }
    )

    with pytest.raises(ConflictError, match="refresh and retry"):
        second.submit_evidence(
            {
                "action_id": action_id,
                "source_reference": "fixture://second-worker",
                "proposed_fact": second.example_fact(action_id),
                "content_hash": "second-worker-content",
                "review_status": "PENDING_REVIEW",
            }
        )

    restored = second.evidence_log()["evidence"]
    assert [item["evidence_id"] for item in restored] == [first_record["evidence_id"]]
    assert restored[0]["source_reference"] == "fixture://first-worker"


def test_workflow_fingerprint_covers_action_contract():
    workflow = default_workflow()
    original = workflow._base_fingerprint
    workflow.actions[0]["target_id"] = "CHANGED-TARGET"
    workflow._initialize_plan(
        True,
        {
            "inventory_balance_mode": "CLOSED",
            "synthetic_data": True,
            "data_quality_issues": [],
        },
    )

    assert workflow._base_fingerprint != original


def test_default_workflow_closes_connection_when_loading_fails(monkeypatch):
    class FailingConnection:
        closed = False

        def close(self):
            self.closed = True

    class FailingService:
        def __init__(self, connection):
            self.connection = connection

        def list_incidents(self):
            raise RuntimeError("database read failed")

    connection = FailingConnection()
    monkeypatch.setenv("RECALLNEXT_DATA_SOURCE", "EXASOL_PERSONAL")
    monkeypatch.setattr(
        workflow_module.ExasolConfig, "from_environment", lambda: object()
    )
    monkeypatch.setattr(
        workflow_module, "connect_exasol", lambda config, autocommit: connection
    )
    monkeypatch.setattr(workflow_module, "IncidentService", FailingService)

    with pytest.raises(RuntimeError, match="database read failed"):
        workflow_module.default_workflow()

    assert connection.closed is True
