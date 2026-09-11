"""Generate or verify the small, synthetic RecallNext demonstration fixture."""

from __future__ import annotations

import argparse
import csv
from collections.abc import Iterable
from pathlib import Path

TABLE_FIELDS: dict[str, tuple[str, ...]] = {
    "incident": (
        "incident_id",
        "incident_version",
        "snapshot_version",
        "product_id",
        "window_start",
        "window_end",
        "status",
        "created_at",
    ),
    "lot": (
        "lot_id",
        "lot_code",
        "lot_source_id",
        "product_id",
        "quantity_cases",
        "recalled",
        "received_at",
        "location_id",
        "source_event_id",
    ),
    "incident_recalled_lot": (
        "incident_id",
        "incident_version",
        "lot_id",
    ),
    "container": (
        "container_id",
        "lot_id",
        "product_id",
        "quantity_cases",
        "homogeneity_verified",
        "location_id",
        "source_event_id",
    ),
    "shipment": (
        "shipment_id",
        "product_id",
        "origin_location_id",
        "destination_id",
        "ship_time",
        "quantity_cases",
    ),
    "shipment_container": (
        "shipment_id",
        "container_id",
        "pick_quantity_cases",
        "pick_record_id",
    ),
    "event": (
        "event_id",
        "event_type",
        "event_time",
        "recorded_at",
        "source_document_id",
        "source_system",
        "snapshot_version",
    ),
    "source_coverage": (
        "incident_id",
        "incident_version",
        "source_system",
        "expected_records",
        "received_records",
        "is_complete",
        "issue_detail",
    ),
    "evidence_action": (
        "action_id",
        "incident_id",
        "incident_version",
        "action_type",
        "target_type",
        "target_id",
        "question",
        "estimated_minutes",
        "availability",
    ),
    "action_shipment": ("action_id", "shipment_id"),
}


def build_fixture() -> dict[str, list[dict[str, str]]]:
    """Return the fixed fixture without reading hidden ground truth."""

    return {
        "incident": [
            {
                "incident_id": "INC-DEMO-001",
                "incident_version": "1",
                "snapshot_version": "1",
                "product_id": "PROD-APPLE",
                "window_start": "2026-09-07 08:00:00",
                "window_end": "2026-09-07 18:00:00",
                "status": "OPEN",
                "created_at": "2026-09-07 08:05:00",
            }
        ],
        "lot": [
            {
                "lot_id": "FARM-A:REC-2026-01",
                "lot_code": "REC-2026-01",
                "lot_source_id": "FARM-A",
                "product_id": "PROD-APPLE",
                "quantity_cases": "12",
                "recalled": "true",
                "received_at": "2026-09-07 07:10:00",
                "location_id": "WH-01",
                "source_event_id": "EV-RECV-001",
            },
            {
                "lot_id": "FARM-A:GOOD-2026-01",
                "lot_code": "GOOD-2026-01",
                "lot_source_id": "FARM-A",
                "product_id": "PROD-APPLE",
                "quantity_cases": "8",
                "recalled": "false",
                "received_at": "2026-09-07 07:20:00",
                "location_id": "WH-01",
                "source_event_id": "EV-RECV-002",
            },
            {
                "lot_id": "FARM-B:REC-2026-01",
                "lot_code": "REC-2026-01",
                "lot_source_id": "FARM-B",
                "product_id": "PROD-APPLE",
                "quantity_cases": "10",
                "recalled": "false",
                "received_at": "2026-09-07 07:30:00",
                "location_id": "WH-01",
                "source_event_id": "EV-RECV-003",
            },
        ],
        "incident_recalled_lot": [
            {
                "incident_id": "INC-DEMO-001",
                "incident_version": "1",
                "lot_id": "FARM-A:REC-2026-01",
            }
        ],
        "container": [
            {
                "container_id": "C-100",
                "lot_id": "",
                "product_id": "PROD-APPLE",
                "quantity_cases": "10",
                "homogeneity_verified": "false",
                "location_id": "WH-01",
                "source_event_id": "EV-CONT-100",
            },
            {
                "container_id": "C-200",
                "lot_id": "",
                "product_id": "PROD-APPLE",
                "quantity_cases": "10",
                "homogeneity_verified": "false",
                "location_id": "WH-01",
                "source_event_id": "EV-CONT-200",
            },
            {
                "container_id": "C-300",
                "lot_id": "FARM-B:REC-2026-01",
                "product_id": "PROD-APPLE",
                "quantity_cases": "10",
                "homogeneity_verified": "true",
                "location_id": "WH-01",
                "source_event_id": "EV-CONT-300",
            },
        ],
        "shipment": [
            {
                "shipment_id": f"S-{number}",
                "product_id": "PROD-APPLE",
                "origin_location_id": "WH-01",
                "destination_id": f"STORE-{index}",
                "ship_time": f"2026-09-07 {9 + index // 2:02d}:{(index % 2) * 30:02d}:00",
                "quantity_cases": "5",
            }
            for index, number in enumerate((100, 200, 300, 400, 500, 600), start=1)
        ],
        "shipment_container": [
            {
                "shipment_id": "S-100",
                "container_id": "C-100",
                "pick_quantity_cases": "5",
                "pick_record_id": "PICK-100",
            },
            {
                "shipment_id": "S-200",
                "container_id": "C-100",
                "pick_quantity_cases": "5",
                "pick_record_id": "",
            },
            {
                "shipment_id": "S-300",
                "container_id": "C-200",
                "pick_quantity_cases": "5",
                "pick_record_id": "",
            },
            {
                "shipment_id": "S-400",
                "container_id": "C-200",
                "pick_quantity_cases": "5",
                "pick_record_id": "PICK-400",
            },
            {
                "shipment_id": "S-500",
                "container_id": "C-300",
                "pick_quantity_cases": "5",
                "pick_record_id": "PICK-500",
            },
            {
                "shipment_id": "S-600",
                "container_id": "C-300",
                "pick_quantity_cases": "5",
                "pick_record_id": "PICK-600",
            },
        ],
        "event": _event_rows(),
        "source_coverage": [
            {
                "incident_id": "INC-DEMO-001",
                "incident_version": "1",
                "source_system": "WMS_RECEIPTS",
                "expected_records": "3",
                "received_records": "3",
                "is_complete": "true",
                "issue_detail": "",
            },
            {
                "incident_id": "INC-DEMO-001",
                "incident_version": "1",
                "source_system": "WMS_CONTAINERS",
                "expected_records": "3",
                "received_records": "3",
                "is_complete": "true",
                "issue_detail": "",
            },
            {
                "incident_id": "INC-DEMO-001",
                "incident_version": "1",
                "source_system": "ERP_DISPATCH",
                "expected_records": "6",
                "received_records": "6",
                "is_complete": "true",
                "issue_detail": "",
            },
        ],
        "evidence_action": [
            {
                "action_id": "ACT-LABEL-C100",
                "incident_id": "INC-DEMO-001",
                "incident_version": "1",
                "action_type": "LABEL_LOOKUP",
                "target_type": "CONTAINER",
                "target_id": "C-100",
                "question": "Which supplier lot is shown on container C-100?",
                "estimated_minutes": "4",
                "availability": "AVAILABLE",
            },
            {
                "action_id": "ACT-PICK-C200",
                "incident_id": "INC-DEMO-001",
                "incident_version": "1",
                "action_type": "PICK_LOG_LOOKUP",
                "target_type": "CONTAINER",
                "target_id": "C-200",
                "question": "Which lots contributed to picks from container C-200?",
                "estimated_minutes": "7",
                "availability": "AVAILABLE",
            },
            {
                "action_id": "ACT-SCAN-C200",
                "incident_id": "INC-DEMO-001",
                "incident_version": "1",
                "action_type": "PHYSICAL_SCAN",
                "target_type": "CONTAINER",
                "target_id": "C-200",
                "question": "What lot code is on a traceable case remaining in C-200?",
                "estimated_minutes": "6",
                "availability": "AVAILABLE",
            },
            {
                "action_id": "ACT-MANIFEST-S200",
                "incident_id": "INC-DEMO-001",
                "incident_version": "1",
                "action_type": "DISPATCH_MANIFEST_LOOKUP",
                "target_type": "SHIPMENT",
                "target_id": "S-200",
                "question": "Which container and lot appear on shipment S-200's manifest?",
                "estimated_minutes": "10",
                "availability": "AVAILABLE",
            },
        ],
        "action_shipment": [
            {"action_id": "ACT-LABEL-C100", "shipment_id": "S-100"},
            {"action_id": "ACT-LABEL-C100", "shipment_id": "S-200"},
            {"action_id": "ACT-PICK-C200", "shipment_id": "S-300"},
            {"action_id": "ACT-PICK-C200", "shipment_id": "S-400"},
            {"action_id": "ACT-SCAN-C200", "shipment_id": "S-300"},
            {"action_id": "ACT-SCAN-C200", "shipment_id": "S-400"},
            {"action_id": "ACT-MANIFEST-S200", "shipment_id": "S-200"},
        ],
    }


def _event_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in range(1, 4):
        rows.append(
            {
                "event_id": f"EV-RECV-{index:03d}",
                "event_type": "RECEIPT",
                "event_time": f"2026-09-07 07:{index * 10:02d}:00",
                "recorded_at": f"2026-09-07 07:{index * 10 + 1:02d}:00",
                "source_document_id": f"RECEIPT-{index:03d}",
                "source_system": "WMS_RECEIPTS",
                "snapshot_version": "1",
            }
        )
    for index, number in enumerate((100, 200, 300), start=1):
        rows.append(
            {
                "event_id": f"EV-CONT-{number}",
                "event_type": "CONTAINER_SNAPSHOT",
                "event_time": f"2026-09-07 08:{index * 5:02d}:00",
                "recorded_at": f"2026-09-07 08:{index * 5 + 1:02d}:00",
                "source_document_id": "" if number != 300 else "LABEL-C300",
                "source_system": "WMS_CONTAINERS",
                "snapshot_version": "1",
            }
        )
    for index, number in enumerate((100, 200, 300, 400, 500, 600), start=1):
        rows.append(
            {
                "event_id": f"EV-DISP-{number}",
                "event_type": "DISPATCH",
                "event_time": f"2026-09-07 {9 + index // 2:02d}:{(index % 2) * 30:02d}:00",
                "recorded_at": f"2026-09-07 {9 + index // 2:02d}:{(index % 2) * 30 + 2:02d}:00",
                "source_document_id": f"MANIFEST-{number}",
                "source_system": "ERP_DISPATCH",
                "snapshot_version": "1",
            }
        )
    return rows


def validate_fixture(fixture: dict[str, list[dict[str, str]]]) -> None:
    missing_tables = set(TABLE_FIELDS) - set(fixture)
    if missing_tables:
        raise ValueError(f"fixture is missing tables: {sorted(missing_tables)}")
    for table, fields in TABLE_FIELDS.items():
        for index, row in enumerate(fixture[table], start=1):
            if tuple(row) != fields:
                raise ValueError(
                    f"{table} row {index} fields differ from the schema contract"
                )

    lots = fixture["lot"]
    if len(lots) != 3 or sum(row["recalled"] == "true" for row in lots) != 1:
        raise ValueError("fixture must contain exactly three lots and one recalled lot")
    if len(fixture["container"]) != 3 or len(fixture["shipment"]) != 6:
        raise ValueError("fixture must contain three containers and six shipments")
    if sum(int(row["quantity_cases"]) for row in lots) != sum(
        int(row["quantity_cases"]) for row in fixture["shipment"]
    ):
        raise ValueError("lot and shipment quantities must balance")


def write_fixture(output_directory: Path) -> None:
    fixture = build_fixture()
    validate_fixture(fixture)
    output_directory.mkdir(parents=True, exist_ok=True)
    for table, fields in TABLE_FIELDS.items():
        path = output_directory / f"{table}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(fixture[table])


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def check_fixture(output_directory: Path) -> None:
    expected = build_fixture()
    validate_fixture(expected)
    for table in TABLE_FIELDS:
        path = output_directory / f"{table}.csv"
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = read_csv_rows(path)
        if actual != expected[table]:
            raise ValueError(f"committed fixture differs from generator: {path}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "sample",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed CSV files without changing them",
    )
    return parser


def main(arguments: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    if args.check:
        check_fixture(args.output_dir)
        print(f"Fixture is reproducible: {args.output_dir}")
    else:
        write_fixture(args.output_dir)
        print(f"Wrote synthetic fixture: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
