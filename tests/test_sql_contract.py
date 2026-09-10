from pathlib import Path

SQL_DIRECTORY = Path("sql")


def _sql(name: str) -> str:
    return (SQL_DIRECTORY / name).read_text(encoding="utf-8").upper()


def test_schema_is_non_destructive_and_has_shared_contract_tables():
    schema = _sql("001_schema.sql")

    assert "DROP SCHEMA" not in schema
    assert "CREATE SCHEMA IF NOT EXISTS RECALLNEXT" in schema
    for table in (
        "LOT",
        "CONTAINER",
        "SHIPMENT",
        "SHIPMENT_CONTAINER",
        "EVENT",
        "EVIDENCE_ACTION",
        "EVIDENCE",
        "SHIPMENT_DECISION",
        "ALLOCATION_SCENARIO",
        "SCENARIO_ALLOCATION",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema


def test_candidate_sql_uses_source_identity_and_preserves_unknown_chronology():
    candidate = _sql("003_candidate_generation.sql")

    assert "L.LOT_SOURCE_ID || ':' || L.LOT_CODE AS LOT_ID" in candidate
    assert "L.RECEIVED_AT IS NULL OR S.SHIP_TIME IS NULL" in candidate
    assert "C.LOT_ID IS NULL OR C.HOMOGENEITY_VERIFIED = FALSE" in candidate
    assert "CANDIDATE_UNIVERSE_COMPLETE" in candidate
    assert "UNRESOLVED_COVERAGE" in candidate


def test_flat_scenario_view_contains_grouping_and_safety_metadata():
    views = _sql("002_views.sql")

    for field in (
        "SCENARIO_ID",
        "SHIPMENT_ID",
        "LOT_SOURCE_ID",
        "LOT_CODE",
        "LOT_ID",
        "QUANTITY_CASES",
        "CANDIDATE_UNIVERSE_COMPLETE",
        "SOLVER_STATUS",
    ):
        assert field in views
    assert "MISSING_SOURCE_COVERAGE" in views
    assert "NO_SOURCE_COVERAGE_DECLARED" in views
    assert "NO_RECALLED_LOT_DECLARED" in views
    assert "UNKNOWN_RECALLED_LOT_REFERENCE" in views
    assert "LOT_IDENTITY_MISMATCH" in views
    assert "SHIPMENT_QUANTITY_MISMATCH" in views
    assert "CONTAINER_OVERALLOCATED" in views
