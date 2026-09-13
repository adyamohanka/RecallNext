import hashlib
import json

import httpx
import pytest

from backend.services.document_extractor import (
    DocumentExtractionError,
    OpenAIDocumentExtractor,
    OpenAIExtractionConfig,
    UnsupportedDocumentError,
)


def manifest_context() -> dict[str, object]:
    return {
        "action_id": "ACT-MANIFEST-S200",
        "action_type": "DISPATCH_MANIFEST_LOOKUP",
        "target_id": "S-200",
        "known_lot_ids": ["FARM-A:GOOD-2026-01", "FARM-A:REC-2026-01"],
        "shipment_ids": ["S-200"],
        "expected_quantities": {"S-200": 5},
    }


def test_openai_extraction_is_structured_bounded_and_not_stored():
    source = b"shipment_id,lot_id,quantity_cases\nS-200,FARM-A:REC-2026-01,5\n"

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer test-secret"
        assert payload["store"] is False
        assert payload["model"] == "test-model"
        schema = payload["text"]["format"]["schema"]
        lot_enum = schema["properties"]["allocations"]["items"]["properties"]["lot_id"][
            "enum"
        ]
        assert lot_enum == manifest_context()["known_lot_ids"]
        assert "UNTRUSTED SOURCE CONTENT" in payload["input"][1]["content"][0]["text"]
        output = {
            "document_supports_fact": True,
            "reason": "Complete manifest row",
            "shipment_id": "S-200",
            "allocations": [{"lot_id": "FARM-A:REC-2026-01", "quantity_cases": 5}],
        }
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "output": [
                    {"content": [{"type": "output_text", "text": json.dumps(output)}]}
                ],
            },
        )

    extractor = OpenAIDocumentExtractor(
        OpenAIExtractionConfig("test-secret", "test-model", 10, 1024 * 1024),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = extractor.extract(
        context=manifest_context(),
        filename="manifest.csv",
        content_type="text/csv",
        content=source,
    )

    assert result["proposed_fact"] == {
        "fact_type": "shipment_allocation",
        "shipment_id": "S-200",
        "allocations": {"FARM-A:REC-2026-01": 5},
    }
    assert result["content_hash"] == hashlib.sha256(source).hexdigest()
    assert result["source_reference"].endswith("#manifest.csv")
    assert result["requires_human_review"] is True


def test_extraction_rejects_a_source_that_does_not_establish_the_fact():
    output = {
        "document_supports_fact": False,
        "reason": "The quantity is missing",
        "shipment_id": "S-200",
        "allocations": [],
    }
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"output_text": json.dumps(output)})
        )
    )
    extractor = OpenAIDocumentExtractor(
        OpenAIExtractionConfig("test-secret", "test-model", 10, 1024), client
    )

    with pytest.raises(UnsupportedDocumentError, match="quantity is missing"):
        extractor.extract(
            context=manifest_context(),
            filename="manifest.txt",
            content_type="text/plain",
            content=b"shipment S-200",
        )


def test_extraction_rejects_duplicate_lot_rows():
    output = {
        "document_supports_fact": True,
        "reason": "Rows found",
        "shipment_id": "S-200",
        "allocations": [
            {"lot_id": "FARM-A:REC-2026-01", "quantity_cases": 2},
            {"lot_id": "FARM-A:REC-2026-01", "quantity_cases": 3},
        ],
    }
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"output_text": json.dumps(output)})
        )
    )
    extractor = OpenAIDocumentExtractor(
        OpenAIExtractionConfig("test-secret", "test-model", 10, 1024), client
    )

    with pytest.raises(DocumentExtractionError, match="duplicate or invalid lot"):
        extractor.extract(
            context=manifest_context(),
            filename="manifest.json",
            content_type="application/json",
            content=b"{}",
        )


def test_extraction_rejects_unapproved_file_types_before_network_call():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: pytest.fail("provider must not be called")
        )
    )
    extractor = OpenAIDocumentExtractor(
        OpenAIExtractionConfig("test-secret", "test-model", 10, 1024), client
    )

    with pytest.raises(UnsupportedDocumentError, match="Use PDF"):
        extractor.extract(
            context=manifest_context(),
            filename="macro.docm",
            content_type="application/vnd.ms-word.document.macroenabled.12",
            content=b"not safe",
        )
