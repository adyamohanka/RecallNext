from data.generate_fixture import build_fixture, check_fixture, validate_fixture
from data.load_fixture import TABLE_SPECS, _to_wire_value, read_typed_rows


def test_committed_fixture_matches_generator():
    check_fixture(__import__("pathlib").Path("data/sample"))


def test_fixture_has_required_ambiguity_and_conservation():
    fixture = build_fixture()
    validate_fixture(fixture)

    lots = fixture["lot"]
    shipments = fixture["shipment"]
    containers = fixture["container"]
    mappings = fixture["shipment_container"]

    assert len(lots) == 3
    assert len(containers) == 3
    assert len(shipments) == 6
    assert sum(int(row["quantity_cases"]) for row in lots) == 30
    assert sum(int(row["quantity_cases"]) for row in shipments) == 30
    assert sum(not row["lot_id"] for row in containers) == 2
    assert sum(not row["pick_record_id"] for row in mappings) == 2

    same_code = [row for row in lots if row["lot_code"] == "REC-2026-01"]
    assert {row["lot_source_id"] for row in same_code} == {"FARM-A", "FARM-B"}
    assert sum(row["recalled"] == "true" for row in same_code) == 1


def test_loader_reads_every_csv_with_exact_types():
    from datetime import datetime
    from pathlib import Path

    data_directory = Path("data/sample")
    loaded = {
        spec.csv_name: read_typed_rows(data_directory, spec) for spec in TABLE_SPECS
    }

    assert loaded["incident"][0][1] == 1
    assert isinstance(loaded["incident"][0][4], datetime)
    assert loaded["lot"][0][5] is True
    assert loaded["container"][0][1] is None
    assert loaded["shipment_container"][1][3] is None


def test_loader_converts_timestamps_to_json_serializable_wire_values():
    from datetime import datetime

    timestamp = datetime.fromisoformat("2026-09-07T12:34:56")

    assert _to_wire_value(timestamp) == "2026-09-07 12:34:56"
    assert _to_wire_value(12) == 12
