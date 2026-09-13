"""Measure the real Exasol-backed API, planner, and review lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from statistics import median
from typing import Any

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import ExasolConfig
from backend.db import connect_exasol
from backend.services.incident_service import IncidentService
from planner.scenario_generator import generate_feasible_scenarios


def _milliseconds(operation: Callable[[], Any]) -> tuple[Any, float]:
    started = time.perf_counter()
    result = operation()
    return result, (time.perf_counter() - started) * 1000


def _distribution(operation: Callable[[], Any], repetitions: int) -> dict[str, float]:
    samples = [_milliseconds(operation)[1] for _ in range(repetitions)]
    ordered = sorted(samples)
    p95_index = max(0, min(len(ordered) - 1, (95 * len(ordered) + 99) // 100 - 1))
    return {
        "runs": repetitions,
        "median_ms": round(median(samples), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "min_ms": round(ordered[0], 3),
        "max_ms": round(ordered[-1], 3),
    }


def _require_ok(response: Any) -> Any:
    if not response.is_success:
        raise RuntimeError(
            f"API request failed: {response.status_code} {response.text}"
        )
    return response


def _reset_state(config: ExasolConfig, incident_id: str) -> None:
    connection = connect_exasol(config, autocommit=True)
    try:
        connection.execute(
            "DELETE FROM RECALLNEXT.WORKFLOW_STATE WHERE INCIDENT_ID = {incident_id}",
            {"incident_id": incident_id},
        )
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident-id", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--runs", type=int, default=15)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reset-before", action="store_true")
    parser.add_argument("--reset-after", action="store_true")
    arguments = parser.parse_args()
    if arguments.runs < 3:
        raise ValueError("--runs must be at least 3")

    config = ExasolConfig.from_environment()
    if arguments.reset_before:
        _reset_state(config, arguments.incident_id)

    connection = connect_exasol(config, autocommit=True)
    try:
        service = IncidentService(connection)
        incidents = service.list_incidents()
        selected = next(
            row for row in incidents if row["incident_id"] == arguments.incident_id
        )
        incident_version = int(selected["incident_version"])
        database = {
            "incident_snapshot": _distribution(
                lambda: service.load_incident_snapshot(
                    arguments.incident_id, incident_version
                ),
                arguments.runs,
            ),
            "candidate_edges": _distribution(
                lambda: service.get_candidate_edges(
                    arguments.incident_id, incident_version
                ),
                arguments.runs,
            ),
        }
    finally:
        connection.close()

    app, initialization_ms = _milliseconds(create_app)
    workflow = app.state.workflow
    planner = _distribution(
        lambda: generate_feasible_scenarios(
            workflow.candidate_edges,
            workflow.shipments,
            workflow.lots,
            candidate_universe_complete=True,
            closed_inventory=True,
        ),
        arguments.runs,
    )
    with TestClient(app) as client:
        api = {
            "incident": _distribution(
                lambda: _require_ok(
                    client.get(f"/api/incidents/{arguments.incident_id}")
                ),
                arguments.runs,
            ),
            "decisions": _distribution(
                lambda: _require_ok(
                    client.get(f"/api/incidents/{arguments.incident_id}/decisions")
                ),
                arguments.runs,
            ),
            "evidence_actions": _distribution(
                lambda: _require_ok(
                    client.get(
                        f"/api/incidents/{arguments.incident_id}/evidence-actions"
                    )
                ),
                arguments.runs,
            ),
        }
        action = _require_ok(
            client.get(f"/api/incidents/{arguments.incident_id}/evidence-actions")
        ).json()["actions"][0]
        example = _require_ok(
            client.get(
                f"/api/incidents/{arguments.incident_id}/evidence-actions/"
                f"{action['action_id']}/example-fact"
            )
        ).json()
        content = json.dumps(example["proposed_fact"], sort_keys=True)
        submission, submit_ms = _milliseconds(
            lambda: _require_ok(
                client.post(
                    f"/api/incidents/{arguments.incident_id}/evidence",
                    json={
                        "action_id": action["action_id"],
                        "source_reference": example["source_reference"],
                        "proposed_fact": example["proposed_fact"],
                        "content_hash": hashlib.sha256(
                            f"live-measurement:{time.time_ns()}:{content}".encode()
                        ).hexdigest(),
                        "review_status": "PENDING_REVIEW",
                    },
                )
            )
        )
        accepted, accept_ms = _milliseconds(
            lambda: _require_ok(
                client.post(
                    f"/api/incidents/{arguments.incident_id}/evidence/"
                    f"{submission.json()['evidence_id']}/accept",
                    json={
                        "verified_by": arguments.reviewer,
                        "expected_version": 1,
                    },
                )
            )
        )

    restarted_app, restart_initialization_ms = _milliseconds(create_app)
    with TestClient(restarted_app) as restarted_client:
        restored_version = _require_ok(
            restarted_client.get(f"/api/incidents/{arguments.incident_id}")
        ).json()["current_version"]
        if restored_version != accepted.json()["current_version"]:
            raise RuntimeError("accepted evidence was not restored after API restart")
        retracted, retract_ms = _milliseconds(
            lambda: _require_ok(
                restarted_client.post(
                    f"/api/incidents/{arguments.incident_id}/evidence/"
                    f"{submission.json()['evidence_id']}/retract",
                    json={
                        "verified_by": arguments.reviewer,
                        "expected_version": restored_version,
                        "reason": "Automated restart and retraction verification",
                    },
                )
            )
        )

    final_app, final_restart_ms = _milliseconds(create_app)
    with TestClient(final_app) as final_client:
        final_version = _require_ok(
            final_client.get(f"/api/incidents/{arguments.incident_id}")
        ).json()["current_version"]
    if final_version != retracted.json()["current_version"]:
        raise RuntimeError("retraction was not restored after API restart")

    report = {
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data_source": "EXASOL_PERSONAL",
        "database": {
            "schema": config.schema,
            "encrypted": config.encryption,
            **database,
        },
        "planner": {"complete_scenario_enumeration": planner},
        "api": {
            "initialization_ms": round(initialization_ms, 3),
            **api,
        },
        "review_lifecycle": {
            "proposal_ms": round(submit_ms, 3),
            "accept_and_persist_ms": round(accept_ms, 3),
            "restart_and_restore_ms": round(restart_initialization_ms, 3),
            "restored_version": restored_version,
            "retract_and_persist_ms": round(retract_ms, 3),
            "second_restart_and_restore_ms": round(final_restart_ms, 3),
            "restored_retracted_version": final_version,
        },
        "scope": {
            "incident_id": arguments.incident_id,
            "shipments": len(workflow.shipments),
            "candidate_edges": len(workflow.candidate_edges),
            "feasible_scenarios": len(workflow._base_scenarios),
            "warehouse_fixture_is_synthetic": True,
            "public_recall_context": (
                workflow.public_recall.get("recall_number")
                if workflow.public_recall
                else None
            ),
        },
    }
    rendered = json.dumps(report, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)

    if arguments.reset_after:
        _reset_state(config, arguments.incident_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
