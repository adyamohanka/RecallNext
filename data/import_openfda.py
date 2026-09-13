"""Import one official openFDA food enforcement record into Exasol."""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from backend.config import ExasolConfig
from backend.db import connect_exasol

BASE_ENDPOINT = "https://api.fda.gov/food/enforcement.json"
SOURCE_DOCUMENTATION = "https://open.fda.gov/apis/food/enforcement/"


def fetch_recall(recall_number: str, api_key: str = "") -> tuple[dict[str, Any], str]:
    parameters = {
        "search": f'recall_number:"{recall_number}"',
        "limit": "1",
    }
    if api_key:
        parameters["api_key"] = api_key
    request_url = f"{BASE_ENDPOINT}?{urllib.parse.urlencode(parameters)}"
    request = urllib.request.Request(
        request_url,
        headers={"User-Agent": "RecallNext/0.1 hackathon prototype"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    results = payload.get("results", [])
    if len(results) != 1 or results[0].get("recall_number") != recall_number:
        raise RuntimeError(f"openFDA did not return exactly {recall_number}")
    return results[0], str(payload.get("meta", {}).get("last_updated", ""))


def import_recall(
    connection: Any,
    incident_id: str,
    record: dict[str, Any],
    dataset_last_updated: str,
) -> None:
    parameters = {
        "incident_id": incident_id,
        "source_name": "openFDA food enforcement",
        "recall_number": str(record["recall_number"]),
        "event_id": str(record.get("event_id", "")),
        "classification": str(record.get("classification", "")),
        "recall_status": str(record.get("status", "")),
        "report_date": str(record.get("report_date", "")),
        "recall_initiation_date": str(record.get("recall_initiation_date", "")),
        "recalling_firm": str(record.get("recalling_firm", "")),
        "product_description": str(record.get("product_description", "")),
        "code_info": str(record.get("code_info", "")),
        "distribution_pattern": str(record.get("distribution_pattern", "")),
        "reason_for_recall": str(record.get("reason_for_recall", "")),
        "source_url": (
            f"{BASE_ENDPOINT}?search=recall_number:{urllib.parse.quote(record['recall_number'])}"
        ),
        "dataset_last_updated": dataset_last_updated,
        "fetched_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }
    connection.execute(
        "MERGE INTO RECALLNEXT.PUBLIC_RECALL_SOURCE T USING (SELECT "
        "{incident_id} AS INCIDENT_ID, {source_name} AS SOURCE_NAME, "
        "{recall_number} AS RECALL_NUMBER, {event_id} AS EVENT_ID, "
        "{classification} AS CLASSIFICATION, {recall_status} AS RECALL_STATUS, "
        "{report_date} AS REPORT_DATE, "
        "{recall_initiation_date} AS RECALL_INITIATION_DATE, "
        "{recalling_firm} AS RECALLING_FIRM, "
        "{product_description} AS PRODUCT_DESCRIPTION, {code_info} AS CODE_INFO, "
        "{distribution_pattern} AS DISTRIBUTION_PATTERN, "
        "{reason_for_recall} AS REASON_FOR_RECALL, {source_url} AS SOURCE_URL, "
        "{dataset_last_updated} AS DATASET_LAST_UPDATED, "
        "{fetched_at} AS FETCHED_AT) S "
        "ON T.INCIDENT_ID = S.INCIDENT_ID AND T.SOURCE_NAME = S.SOURCE_NAME "
        "AND T.RECALL_NUMBER = S.RECALL_NUMBER "
        "WHEN MATCHED THEN UPDATE SET T.EVENT_ID = S.EVENT_ID, "
        "T.CLASSIFICATION = S.CLASSIFICATION, T.RECALL_STATUS = S.RECALL_STATUS, "
        "T.REPORT_DATE = S.REPORT_DATE, "
        "T.RECALL_INITIATION_DATE = S.RECALL_INITIATION_DATE, "
        "T.RECALLING_FIRM = S.RECALLING_FIRM, "
        "T.PRODUCT_DESCRIPTION = S.PRODUCT_DESCRIPTION, T.CODE_INFO = S.CODE_INFO, "
        "T.DISTRIBUTION_PATTERN = S.DISTRIBUTION_PATTERN, "
        "T.REASON_FOR_RECALL = S.REASON_FOR_RECALL, T.SOURCE_URL = S.SOURCE_URL, "
        "T.DATASET_LAST_UPDATED = S.DATASET_LAST_UPDATED, "
        "T.FETCHED_AT = S.FETCHED_AT "
        "WHEN NOT MATCHED THEN INSERT (INCIDENT_ID, SOURCE_NAME, RECALL_NUMBER, "
        "EVENT_ID, CLASSIFICATION, RECALL_STATUS, REPORT_DATE, "
        "RECALL_INITIATION_DATE, RECALLING_FIRM, PRODUCT_DESCRIPTION, CODE_INFO, "
        "DISTRIBUTION_PATTERN, REASON_FOR_RECALL, SOURCE_URL, "
        "DATASET_LAST_UPDATED, FETCHED_AT) VALUES (S.INCIDENT_ID, S.SOURCE_NAME, "
        "S.RECALL_NUMBER, S.EVENT_ID, S.CLASSIFICATION, S.RECALL_STATUS, "
        "S.REPORT_DATE, S.RECALL_INITIATION_DATE, S.RECALLING_FIRM, "
        "S.PRODUCT_DESCRIPTION, S.CODE_INFO, S.DISTRIBUTION_PATTERN, "
        "S.REASON_FOR_RECALL, S.SOURCE_URL, S.DATASET_LAST_UPDATED, S.FETCHED_AT)",
        parameters,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--incident-id",
        default=os.environ.get("RECALLNEXT_INCIDENT_ID", ""),
        required=not bool(os.environ.get("RECALLNEXT_INCIDENT_ID", "")),
    )
    parser.add_argument(
        "--recall-number",
        default=os.environ.get("OPENFDA_RECALL_NUMBER", ""),
        required=not bool(os.environ.get("OPENFDA_RECALL_NUMBER", "")),
    )
    arguments = parser.parse_args()
    record, updated = fetch_recall(
        arguments.recall_number,
        os.environ.get("OPENFDA_API_KEY", "").strip(),
    )
    connection = connect_exasol(ExasolConfig.from_environment(), autocommit=True)
    try:
        import_recall(connection, arguments.incident_id, record, updated)
    finally:
        connection.close()
    print(
        json.dumps(
            {
                "incident_id": arguments.incident_id,
                "recall_number": record["recall_number"],
                "classification": record.get("classification"),
                "dataset_last_updated": updated,
                "documentation": SOURCE_DOCUMENTATION,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
