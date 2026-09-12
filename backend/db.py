"""Small PyExasol connection and SQL-script helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ExasolConfig


class ExasolDependencyError(RuntimeError):
    """Raised when the official Exasol connector is unavailable."""


def connect_exasol(
    config: ExasolConfig, *, autocommit: bool = False, open_schema: bool = True
) -> Any:
    """Open a real encrypted PyExasol connection.

    The import is lazy so contract and fixture tests can run without network or
    database access. Calling this function never creates a mock connection.
    """

    try:
        import pyexasol
    except ImportError as error:
        raise ExasolDependencyError(
            "PyExasol is not installed; run `python -m pip install -e .`"
        ) from error

    return pyexasol.connect(
        dsn=config.dsn,
        user=config.user,
        password=config.password,
        schema=config.schema if open_schema else "",
        autocommit=autocommit,
        compression=config.compression,
        encryption=config.encryption,
        query_timeout=config.query_timeout_seconds,
        fetch_dict=True,
        lower_ident=True,
        client_name="RecallNext",
        client_version="0.1.0",
    )


def execute_sql_file(connection: Any, path: Path) -> None:
    """Execute every statement in a UTF-8 SQL file through PyExasol."""

    if not path.is_file():
        raise FileNotFoundError(path)
    script = path.read_text(encoding="utf-8")
    if not script.strip():
        raise ValueError(f"SQL script is empty: {path}")
    connection.execute_sql_script(script)


def bootstrap_schema(connection: Any, sql_directory: Path) -> None:
    """Apply the ordered, non-destructive RecallNext schema scripts."""

    paths = [
        sql_directory / "001_schema.sql",
        sql_directory / "002_views.sql",
        sql_directory / "003_candidate_generation.sql",
    ]
    for path in paths:
        execute_sql_file(connection, path)
