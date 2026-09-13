"""Small Exasol-backed state store for reviewed workflow evidence."""

from __future__ import annotations

import json
from typing import Any


class ExasolWorkflowStateStore:
    def __init__(self, connection: Any, incident_id: str):
        self.connection = connection
        self.incident_id = incident_id

    def load(self) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT STATE_JSON FROM RECALLNEXT.WORKFLOW_STATE "
            "WHERE INCIDENT_ID = {incident_id}",
            {"incident_id": self.incident_id},
        ).fetchone()
        if row is None:
            return None
        return json.loads(dict(row)["state_json"])

    def save(self, state: dict[str, Any]) -> None:
        payload = json.dumps(state, sort_keys=True, separators=(",", ":"))
        self.connection.execute(
            "MERGE INTO RECALLNEXT.WORKFLOW_STATE T USING "
            "(SELECT {incident_id} AS INCIDENT_ID, {state_json} AS STATE_JSON, "
            "CURRENT_TIMESTAMP AS UPDATED_AT) S "
            "ON T.INCIDENT_ID = S.INCIDENT_ID "
            "WHEN MATCHED THEN UPDATE SET T.STATE_JSON = S.STATE_JSON, "
            "T.UPDATED_AT = S.UPDATED_AT "
            "WHEN NOT MATCHED THEN INSERT (INCIDENT_ID, STATE_JSON, UPDATED_AT) "
            "VALUES (S.INCIDENT_ID, S.STATE_JSON, S.UPDATED_AT)",
            {"incident_id": self.incident_id, "state_json": payload},
        )
