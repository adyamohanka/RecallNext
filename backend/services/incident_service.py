"""Read-only incident data and versioned planner-result persistence."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from backend.contracts import (
    PLANNER_SUCCESS,
    ContractError,
    build_planner_payload,
    source_qualified_lot_id,
)

FIXED_DECISION_STATUSES = {
    "CONFIRMED_INCLUSION",
    "POSSIBLE_INCLUSION",
    "EXCLUDED_UNDER_ASSUMPTIONS",
    "UNRESOLVED",
}


class IncidentNotFoundError(LookupError):
    """Raised when an incident version is absent from Exasol."""


def _rows(statement: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in statement.fetchall()]


def _one(statement: Any) -> dict[str, Any] | None:
    row = statement.fetchone()
    return None if row is None else dict(row)


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise ContractError(f"{name} must be a non-negative integer")
    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise ContractError(f"{name} must be an integer")
        value = int(value)
    if not isinstance(value, int) or value < 0:
        raise ContractError(f"{name} must be a non-negative integer")
    return value


def _utc_timestamp() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IncidentService:
    """Thin data boundary; it never guesses, solves, or accepts evidence."""

    def __init__(self, connection: Any):
        self.connection = connection

    def list_incidents(self) -> list[dict[str, Any]]:
        """Return the latest stored version of every Exasol incident."""

        return _rows(
            self.connection.execute(
                "SELECT I.INCIDENT_ID, I.INCIDENT_VERSION, I.SNAPSHOT_VERSION, "
                "I.PRODUCT_ID, I.STATUS, I.CREATED_AT "
                "FROM RECALLNEXT.INCIDENT I "
                "JOIN (SELECT INCIDENT_ID, MAX(INCIDENT_VERSION) AS INCIDENT_VERSION "
                "FROM RECALLNEXT.INCIDENT GROUP BY INCIDENT_ID) L "
                "ON L.INCIDENT_ID = I.INCIDENT_ID "
                "AND L.INCIDENT_VERSION = I.INCIDENT_VERSION "
                "ORDER BY I.CREATED_AT DESC, I.INCIDENT_ID"
            )
        )

    def load_workflow_records(
        self, incident_id: str, incident_version: int
    ) -> dict[str, Any]:
        """Load the complete bounded incident component used by the API planner."""

        snapshot = self.load_incident_snapshot(incident_id, incident_version)
        parameters = {
            "incident_id": incident_id,
            "incident_version": incident_version,
        }
        product_id = snapshot["incident"]["product_id"]
        product_parameters = {"product_id": product_id}
        lots = _rows(
            self.connection.execute(
                "SELECT LOT_ID, LOT_CODE, LOT_SOURCE_ID, PRODUCT_ID, "
                "QUANTITY_CASES, RECALLED, RECEIVED_AT, LOCATION_ID, SOURCE_EVENT_ID "
                "FROM RECALLNEXT.LOT WHERE PRODUCT_ID = {product_id} "
                "ORDER BY LOT_SOURCE_ID, LOT_CODE",
                product_parameters,
            )
        )
        containers = _rows(
            self.connection.execute(
                "SELECT DISTINCT C.CONTAINER_ID, C.LOT_ID, C.PRODUCT_ID, "
                "C.QUANTITY_CASES, C.HOMOGENEITY_VERIFIED, C.LOCATION_ID, "
                "C.SOURCE_EVENT_ID FROM RECALLNEXT.CONTAINER C "
                "JOIN RECALLNEXT.SHIPMENT_CONTAINER SC "
                "ON SC.CONTAINER_ID = C.CONTAINER_ID "
                "JOIN RECALLNEXT.SHIPMENT S ON S.SHIPMENT_ID = SC.SHIPMENT_ID "
                "WHERE S.PRODUCT_ID = {product_id} ORDER BY C.CONTAINER_ID",
                product_parameters,
            )
        )
        shipment_containers = _rows(
            self.connection.execute(
                "SELECT SC.SHIPMENT_ID, SC.CONTAINER_ID, SC.PICK_QUANTITY_CASES, "
                "SC.PICK_RECORD_ID FROM RECALLNEXT.SHIPMENT_CONTAINER SC "
                "JOIN RECALLNEXT.SHIPMENT S ON S.SHIPMENT_ID = SC.SHIPMENT_ID "
                "WHERE S.PRODUCT_ID = {product_id} "
                "ORDER BY SC.SHIPMENT_ID, SC.CONTAINER_ID",
                product_parameters,
            )
        )
        actions = _rows(
            self.connection.execute(
                "SELECT ACTION_ID, INCIDENT_ID, INCIDENT_VERSION, ACTION_TYPE, "
                "TARGET_TYPE, TARGET_ID, QUESTION, ESTIMATED_MINUTES, AVAILABILITY "
                "FROM RECALLNEXT.EVIDENCE_ACTION "
                "WHERE INCIDENT_ID = {incident_id} "
                "AND INCIDENT_VERSION = {incident_version} ORDER BY ACTION_ID",
                parameters,
            )
        )
        action_shipments = _rows(
            self.connection.execute(
                "SELECT A.ACTION_ID, A.SHIPMENT_ID "
                "FROM RECALLNEXT.ACTION_SHIPMENT A "
                "JOIN RECALLNEXT.EVIDENCE_ACTION E ON E.ACTION_ID = A.ACTION_ID "
                "WHERE E.INCIDENT_ID = {incident_id} "
                "AND E.INCIDENT_VERSION = {incident_version} "
                "ORDER BY A.ACTION_ID, A.SHIPMENT_ID",
                parameters,
            )
        )
        public_recall = _one(
            self.connection.execute(
                "SELECT SOURCE_NAME, RECALL_NUMBER, EVENT_ID, CLASSIFICATION, "
                "RECALL_STATUS, REPORT_DATE, RECALL_INITIATION_DATE, RECALLING_FIRM, "
                "PRODUCT_DESCRIPTION, CODE_INFO, DISTRIBUTION_PATTERN, "
                "REASON_FOR_RECALL, SOURCE_URL, DATASET_LAST_UPDATED, FETCHED_AT "
                "FROM RECALLNEXT.PUBLIC_RECALL_SOURCE "
                "WHERE INCIDENT_ID = {incident_id} ORDER BY FETCHED_AT DESC LIMIT 1",
                {"incident_id": incident_id},
            )
        )
        return {
            **snapshot,
            "lots": lots,
            "containers": containers,
            "shipment_containers": shipment_containers,
            "actions": actions,
            "action_shipments": action_shipments,
            "candidate_edges": self.get_candidate_edges(
                incident_id, incident_version
            ),
            "public_recall": public_recall,
        }

    def load_incident_snapshot(
        self, incident_id: str, incident_version: int
    ) -> dict[str, Any]:
        parameters = {
            "incident_id": incident_id,
            "incident_version": incident_version,
        }
        incident = _one(
            self.connection.execute(
                "SELECT INCIDENT_ID, INCIDENT_VERSION, SNAPSHOT_VERSION, PRODUCT_ID, "
                "WINDOW_START, WINDOW_END, STATUS, CREATED_AT "
                "FROM RECALLNEXT.INCIDENT "
                "WHERE INCIDENT_ID = {incident_id} "
                "AND INCIDENT_VERSION = {incident_version}",
                parameters,
            )
        )
        if incident is None:
            raise IncidentNotFoundError(
                f"incident version not found: {incident_id}@{incident_version}"
            )

        recalled_lots = _rows(
            self.connection.execute(
                "SELECT L.LOT_ID, L.LOT_SOURCE_ID, L.LOT_CODE, L.PRODUCT_ID, "
                "L.QUANTITY_CASES "
                "FROM RECALLNEXT.INCIDENT_RECALLED_LOT R "
                "JOIN RECALLNEXT.LOT L ON L.LOT_ID = R.LOT_ID "
                "WHERE R.INCIDENT_ID = {incident_id} "
                "AND R.INCIDENT_VERSION = {incident_version} "
                "ORDER BY L.LOT_SOURCE_ID, L.LOT_CODE",
                parameters,
            )
        )
        shipments = _rows(
            self.connection.execute(
                "SELECT S.SHIPMENT_ID, S.DESTINATION_ID, S.SHIP_TIME, "
                "S.QUANTITY_CASES "
                "FROM RECALLNEXT.SHIPMENT S "
                "JOIN RECALLNEXT.INCIDENT I ON I.PRODUCT_ID = S.PRODUCT_ID "
                "WHERE I.INCIDENT_ID = {incident_id} "
                "AND I.INCIDENT_VERSION = {incident_version} "
                "AND (I.WINDOW_START IS NULL OR S.SHIP_TIME IS NULL "
                "OR S.SHIP_TIME >= I.WINDOW_START) "
                "AND (I.WINDOW_END IS NULL OR S.SHIP_TIME IS NULL "
                "OR S.SHIP_TIME <= I.WINDOW_END) "
                "ORDER BY S.SHIPMENT_ID",
                parameters,
            )
        )
        universe = _one(
            self.connection.execute(
                "SELECT CANDIDATE_UNIVERSE_COMPLETE, BLOCKING_ISSUE_COUNT "
                "FROM RECALLNEXT.V_CANDIDATE_UNIVERSE_STATUS "
                "WHERE INCIDENT_ID = {incident_id} "
                "AND INCIDENT_VERSION = {incident_version}",
                parameters,
            )
        )
        issues = _rows(
            self.connection.execute(
                "SELECT ISSUE_CODE, ENTITY_TYPE, ENTITY_ID, DETAIL "
                "FROM RECALLNEXT.V_DATA_QUALITY_ISSUE "
                "WHERE INCIDENT_ID = {incident_id} "
                "AND INCIDENT_VERSION = {incident_version} "
                "ORDER BY ISSUE_CODE, ENTITY_TYPE, ENTITY_ID",
                parameters,
            )
        )
        return {
            "incident": incident,
            "recalled_lots": recalled_lots,
            "shipments": shipments,
            "candidate_universe": universe,
            "data_quality_issues": issues,
        }

    def get_candidate_edges(
        self, incident_id: str, incident_version: int
    ) -> list[dict[str, Any]]:
        return _rows(
            self.connection.execute(
                "SELECT INCIDENT_ID, INCIDENT_VERSION, SHIPMENT_ID, CONTAINER_ID, "
                "GROUP_QUANTITY_CASES, LOT_SOURCE_ID, LOT_CODE, LOT_ID, MIN_QUANTITY_CASES, "
                "MAX_QUANTITY_CASES, CANDIDATE_REASON, CONSTRAINT_STATUS, "
                "PICK_RECORD_ID, LOT_SOURCE_EVENT_ID, CONTAINER_SOURCE_EVENT_ID, "
                "CANDIDATE_UNIVERSE_COMPLETE, IS_RECALLED_LOT "
                "FROM RECALLNEXT.V_CANDIDATE_ALLOCATION "
                "WHERE INCIDENT_ID = {incident_id} "
                "AND INCIDENT_VERSION = {incident_version} "
                "ORDER BY SHIPMENT_ID, CONTAINER_ID, LOT_SOURCE_ID, LOT_CODE",
                {
                    "incident_id": incident_id,
                    "incident_version": incident_version,
                },
            )
        )

    def get_planner_scenarios(
        self, incident_id: str, incident_version: int
    ) -> dict[str, Any]:
        parameters = {
            "incident_id": incident_id,
            "incident_version": incident_version,
        }
        metadata = _rows(
            self.connection.execute(
                "SELECT DISTINCT CANDIDATE_UNIVERSE_COMPLETE, SOLVER_STATUS "
                "FROM RECALLNEXT.ALLOCATION_SCENARIO "
                "WHERE INCIDENT_ID = {incident_id} "
                "AND INCIDENT_VERSION = {incident_version}",
                parameters,
            )
        )
        if not metadata:
            universe = _one(
                self.connection.execute(
                    "SELECT CANDIDATE_UNIVERSE_COMPLETE "
                    "FROM RECALLNEXT.V_CANDIDATE_UNIVERSE_STATUS "
                    "WHERE INCIDENT_ID = {incident_id} "
                    "AND INCIDENT_VERSION = {incident_version}",
                    parameters,
                )
            )
            complete = (
                False if universe is None else universe["candidate_universe_complete"]
            )
            return build_planner_payload(
                [],
                candidate_universe_complete=complete,
                solver_status="NO_SCENARIO_RESULT",
            )
        if len(metadata) != 1:
            raise ContractError(
                "scenario rows disagree on solver status or universe completeness"
            )
        flat_rows = _rows(
            self.connection.execute(
                "SELECT SCENARIO_ID, SHIPMENT_ID, LOT_SOURCE_ID, LOT_CODE, LOT_ID, "
                "QUANTITY_CASES FROM RECALLNEXT.V_PLANNER_SCENARIO_ALLOCATION "
                "WHERE INCIDENT_ID = {incident_id} "
                "AND INCIDENT_VERSION = {incident_version} "
                "ORDER BY SCENARIO_ID, SHIPMENT_ID, LOT_SOURCE_ID, LOT_CODE",
                parameters,
            )
        )
        return build_planner_payload(
            flat_rows,
            candidate_universe_complete=metadata[0]["candidate_universe_complete"],
            solver_status=metadata[0]["solver_status"],
        )

    def get_candidate_allocations(
        self, incident_id: str, incident_version: int
    ) -> dict[str, Any]:
        """Compatibility name used in Sakthi's team brief."""

        return self.get_planner_scenarios(incident_id, incident_version)

    def get_evidence_actions(
        self, incident_id: str, incident_version: int
    ) -> list[dict[str, Any]]:
        return _rows(
            self.connection.execute(
                "SELECT ACTION_ID, ACTION_TYPE, TARGET_TYPE, TARGET_ID, QUESTION, "
                "ESTIMATED_MINUTES, AVAILABILITY, SHIPMENT_ID, HELD_CASES "
                "FROM RECALLNEXT.V_EVIDENCE_ACTION_IMPACT "
                "WHERE INCIDENT_ID = {incident_id} "
                "AND INCIDENT_VERSION = {incident_version} "
                "ORDER BY ACTION_ID, SHIPMENT_ID",
                {
                    "incident_id": incident_id,
                    "incident_version": incident_version,
                },
            )
        )

    def persist_scenarios(
        self,
        incident_id: str,
        incident_version: int,
        candidate_allocations: Sequence[Sequence[Mapping[str, Any]]],
        *,
        candidate_universe_complete: bool,
        solver_status: str,
        model_version: str,
        assumptions: Mapping[str, Any] | None = None,
    ) -> None:
        """Replace one version's solver output; caller controls commit/rollback."""

        if not isinstance(candidate_universe_complete, bool):
            raise ContractError("candidate_universe_complete must be a boolean")
        if not isinstance(solver_status, str):
            raise ContractError("solver_status must be a string")
        normalized_status = solver_status.strip().upper()
        if not normalized_status:
            raise ContractError("solver_status must be non-empty")
        if normalized_status == PLANNER_SUCCESS and not candidate_allocations:
            raise ContractError("SUCCESS requires at least one feasible scenario")
        if normalized_status == PLANNER_SUCCESS and not candidate_universe_complete:
            raise ContractError("SUCCESS requires a complete candidate universe")
        if normalized_status != PLANNER_SUCCESS and candidate_allocations:
            raise ContractError(
                "a non-success solver result cannot contain allocations"
            )
        if not isinstance(model_version, str) or not model_version.strip():
            raise ContractError("model_version must be non-empty")

        parameters = {
            "incident_id": incident_id,
            "incident_version": incident_version,
        }
        universe = _one(
            self.connection.execute(
                "SELECT CANDIDATE_UNIVERSE_COMPLETE "
                "FROM RECALLNEXT.V_CANDIDATE_UNIVERSE_STATUS "
                "WHERE INCIDENT_ID = {incident_id} "
                "AND INCIDENT_VERSION = {incident_version}",
                parameters,
            )
        )
        if universe is None:
            raise ContractError("incident version has no canonical universe status")
        canonical_complete = universe.get("candidate_universe_complete")
        if not isinstance(canonical_complete, bool):
            raise ContractError("canonical candidate universe status must be a boolean")
        if candidate_universe_complete and not canonical_complete:
            raise ContractError(
                "caller cannot upgrade an incomplete canonical candidate universe"
            )

        allowed_pairs: set[tuple[str, str]] = set()
        if candidate_allocations:
            candidate_rows = _rows(
                self.connection.execute(
                    "SELECT DISTINCT SHIPMENT_ID, LOT_ID "
                    "FROM RECALLNEXT.V_CANDIDATE_ALLOCATION "
                    "WHERE INCIDENT_ID = {incident_id} "
                    "AND INCIDENT_VERSION = {incident_version}",
                    parameters,
                )
            )
            for candidate in candidate_rows:
                shipment_id = str(candidate.get("shipment_id", "")).strip()
                lot_id = str(candidate.get("lot_id", "")).strip()
                if not shipment_id or not lot_id:
                    raise ContractError("canonical candidate identity cannot be empty")
                allowed_pairs.add((shipment_id, lot_id))

        metadata_rows: list[tuple[object, ...]] = []
        allocation_rows: list[tuple[object, ...]] = []
        scenario_source: Sequence[Sequence[Mapping[str, Any]]]
        scenario_source = candidate_allocations if candidate_allocations else ((),)
        assumptions_json = json.dumps(
            dict(assumptions or {}), sort_keys=True, separators=(",", ":")
        )
        created_at = _utc_timestamp()
        for index, scenario in enumerate(scenario_source, start=1):
            scenario_id = f"SCN-{index:06d}" if candidate_allocations else "SCN-ERROR"
            if normalized_status == PLANNER_SUCCESS and not scenario:
                raise ContractError("a successful scenario cannot be empty")
            metadata_rows.append(
                (
                    incident_id,
                    incident_version,
                    scenario_id,
                    candidate_universe_complete,
                    normalized_status,
                    model_version,
                    assumptions_json,
                    created_at,
                )
            )
            seen: set[tuple[str, str]] = set()
            for row in scenario:
                shipment_id = str(row.get("shipment_id", "")).strip()
                lot_id = str(row.get("lot_id", "")).strip()
                if not shipment_id or not lot_id:
                    raise ContractError("shipment_id and lot_id must be non-empty")
                lot_parts = lot_id.split(":")
                if len(lot_parts) != 2 or source_qualified_lot_id(*lot_parts) != lot_id:
                    raise ContractError(
                        "lot_id must use the source-qualified LOT_SOURCE_ID:LOT_CODE format"
                    )
                key = (shipment_id, lot_id)
                if key in seen:
                    raise ContractError(
                        "duplicate shipment/lot allocation within one scenario"
                    )
                if key not in allowed_pairs:
                    raise ContractError(
                        "scenario shipment/lot pair is outside the canonical "
                        "candidate universe"
                    )
                seen.add(key)
                allocation_rows.append(
                    (
                        incident_id,
                        incident_version,
                        scenario_id,
                        shipment_id,
                        lot_id,
                        _integer(row.get("quantity_cases"), "quantity_cases"),
                    )
                )
        self.connection.execute(
            "DELETE FROM RECALLNEXT.SCENARIO_ALLOCATION "
            "WHERE INCIDENT_ID = {incident_id} "
            "AND INCIDENT_VERSION = {incident_version}",
            parameters,
        )
        self.connection.execute(
            "DELETE FROM RECALLNEXT.ALLOCATION_SCENARIO "
            "WHERE INCIDENT_ID = {incident_id} "
            "AND INCIDENT_VERSION = {incident_version}",
            parameters,
        )
        metadata_statement = self.connection.create_prepared_statement(
            "INSERT INTO RECALLNEXT.ALLOCATION_SCENARIO "
            "(INCIDENT_ID, INCIDENT_VERSION, SCENARIO_ID, "
            "CANDIDATE_UNIVERSE_COMPLETE, SOLVER_STATUS, MODEL_VERSION, "
            "ASSUMPTIONS_JSON, CREATED_AT) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )
        metadata_statement.execute_prepared(metadata_rows)
        if allocation_rows:
            allocation_statement = self.connection.create_prepared_statement(
                "INSERT INTO RECALLNEXT.SCENARIO_ALLOCATION "
                "(INCIDENT_ID, INCIDENT_VERSION, SCENARIO_ID, SHIPMENT_ID, "
                "LOT_ID, QUANTITY_CASES) VALUES (?, ?, ?, ?, ?, ?)"
            )
            allocation_statement.execute_prepared(allocation_rows)

    def persist_decisions(
        self,
        incident_id: str,
        incident_version: int,
        decisions: Iterable[Mapping[str, Any]],
        *,
        model_version: str,
        evidence_references: Sequence[str] = (),
    ) -> None:
        """Persist deterministic planner decisions without committing them."""

        if not isinstance(model_version, str) or not model_version.strip():
            raise ContractError("model_version must be non-empty")
        rows: list[tuple[object, ...]] = []
        for decision in decisions:
            status = str(decision.get("status", "")).strip().upper()
            if status not in FIXED_DECISION_STATUSES:
                raise ContractError(f"unsupported decision status: {status!r}")
            shipment_id = str(decision.get("shipment_id", "")).strip()
            solver_status = str(decision.get("solver_status", "")).strip().upper()
            if not shipment_id or not solver_status:
                raise ContractError("shipment_id and solver_status must be non-empty")
            minimum = _integer(decision.get("min_recalled_cases"), "min_recalled_cases")
            maximum = _integer(decision.get("max_recalled_cases"), "max_recalled_cases")
            if minimum > maximum:
                raise ContractError(
                    "min_recalled_cases cannot exceed max_recalled_cases"
                )
            assumptions = dict(decision.get("assumptions", {}))
            if (
                assumptions.get("candidate_universe_complete") is not True
                and status != "UNRESOLVED"
            ):
                raise ContractError(
                    "an incomplete candidate universe requires UNRESOLVED"
                )
            if solver_status != PLANNER_SUCCESS and status != "UNRESOLVED":
                raise ContractError("a failed solver requires UNRESOLVED")
            status_matches_bounds = {
                "CONFIRMED_INCLUSION": minimum > 0,
                "POSSIBLE_INCLUSION": minimum == 0 and maximum > 0,
                "EXCLUDED_UNDER_ASSUMPTIONS": maximum == 0,
                "UNRESOLVED": True,
            }
            if not status_matches_bounds[status]:
                raise ContractError("decision status does not match its bounds")
            rows.append(
                (
                    incident_id,
                    incident_version,
                    shipment_id,
                    minimum,
                    maximum,
                    status,
                    solver_status,
                    json.dumps(
                        assumptions,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    json.dumps(list(evidence_references), separators=(",", ":")),
                    model_version,
                    _utc_timestamp(),
                )
            )

        parameters = {
            "incident_id": incident_id,
            "incident_version": incident_version,
        }
        self.connection.execute(
            "DELETE FROM RECALLNEXT.SHIPMENT_DECISION "
            "WHERE INCIDENT_ID = {incident_id} "
            "AND INCIDENT_VERSION = {incident_version}",
            parameters,
        )
        if not rows:
            return
        statement = self.connection.create_prepared_statement(
            "INSERT INTO RECALLNEXT.SHIPMENT_DECISION "
            "(INCIDENT_ID, INCIDENT_VERSION, SHIPMENT_ID, MIN_RECALLED_CASES, "
            "MAX_RECALLED_CASES, STATUS, SOLVER_STATUS, ASSUMPTIONS_JSON, "
            "EVIDENCE_REFERENCES_JSON, MODEL_VERSION, CREATED_AT) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        statement.execute_prepared(rows)
