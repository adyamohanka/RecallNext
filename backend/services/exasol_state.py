"""Small Exasol-backed state store for reviewed workflow evidence."""

from __future__ import annotations

import json
from typing import Any


class ConcurrentStateWriteError(RuntimeError):
    """Raised when another worker changed the incident state first."""


class ExasolWorkflowStateStore:
    def __init__(self, connection: Any, incident_id: str):
        self.connection = connection
        self.incident_id = incident_id
        self._expected_state_json: str | None = None

    def load(self) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT STATE_JSON FROM RECALLNEXT.WORKFLOW_STATE "
            "WHERE INCIDENT_ID = {incident_id}",
            {"incident_id": self.incident_id},
        ).fetchone()
        if row is None:
            self._expected_state_json = None
            return None
        payload = str(dict(row)["state_json"])
        self._expected_state_json = payload
        return json.loads(payload)

    def save(self, state: dict[str, Any]) -> None:
        payload = json.dumps(state, sort_keys=True, separators=(",", ":"))
        expected = self._expected_state_json
        if expected is None:
            statement = self.connection.execute(
                "INSERT INTO RECALLNEXT.WORKFLOW_STATE "
                "(INCIDENT_ID, STATE_JSON, UPDATED_AT) "
                "SELECT {incident_id}, {state_json}, CURRENT_TIMESTAMP "
                "WHERE NOT EXISTS (SELECT 1 FROM RECALLNEXT.WORKFLOW_STATE "
                "WHERE INCIDENT_ID = {incident_id})",
                {"incident_id": self.incident_id, "state_json": payload},
            )
        else:
            statement = self.connection.execute(
                "UPDATE RECALLNEXT.WORKFLOW_STATE SET STATE_JSON = {state_json}, "
                "UPDATED_AT = CURRENT_TIMESTAMP WHERE INCIDENT_ID = {incident_id} "
                "AND STATE_JSON = {expected_state_json}",
                {
                    "incident_id": self.incident_id,
                    "state_json": payload,
                    "expected_state_json": expected,
                },
            )
        if statement.rowcount() != 1:
            raise ConcurrentStateWriteError(
                "workflow state changed in another API worker"
            )
        self._expected_state_json = payload
