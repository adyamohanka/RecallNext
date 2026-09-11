"""Run a read-only RecallNext smoke check against configured Exasol Personal."""

from __future__ import annotations

import json
from collections.abc import Iterable
from time import perf_counter

from backend.config import ExasolConfig
from backend.db import connect_exasol
from backend.services import IncidentService


def main(arguments: Iterable[str] | None = None) -> int:
    if arguments:
        raise ValueError("recallnext-smoke does not accept arguments")
    config = ExasolConfig.from_environment()
    connection = connect_exasol(config, autocommit=True)
    try:
        service = IncidentService(connection)
        started = perf_counter()
        snapshot = service.load_incident_snapshot("INC-DEMO-001", 1)
        snapshot_ms = (perf_counter() - started) * 1000

        started = perf_counter()
        candidates = service.get_candidate_edges("INC-DEMO-001", 1)
        candidate_ms = (perf_counter() - started) * 1000
    finally:
        connection.close()

    report = {
        "database": config.safe_summary(),
        "incident_id": "INC-DEMO-001",
        "incident_version": 1,
        "candidate_universe": snapshot["candidate_universe"],
        "data_quality_issues": snapshot["data_quality_issues"],
        "shipment_count": len(snapshot["shipments"]),
        "candidate_edge_count": len(candidates),
        "timing_ms": {
            "snapshot": round(snapshot_ms, 3),
            "candidate_edges": round(candidate_ms, 3),
        },
    }
    print(json.dumps(report, indent=2, default=str))

    universe = snapshot["candidate_universe"] or {}
    if universe.get("candidate_universe_complete") is not True:
        print("Smoke check failed: candidate universe is incomplete.")
        return 2
    if snapshot["data_quality_issues"]:
        print("Smoke check failed: blocking data-quality issues remain.")
        return 3
    if len(snapshot["shipments"]) != 6 or len(candidates) != 14:
        print("Smoke check failed: deterministic fixture counts differ.")
        return 4
    print("Smoke check passed against real Exasol.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
