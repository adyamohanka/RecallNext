from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import create_app
from backend.services.recall_workflow import default_workflow


def test_health_labels_fixture_mode():
    with TestClient(create_app()) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["data_source"] == "SYNTHETIC_FIXTURE"
        assert response.json()["database_connected"] is False
        assert response.json()["write_auth_required"] is False
        assert response.json()["document_extraction_configured"] is False


def test_production_write_routes_require_the_runtime_bearer_token(monkeypatch):
    token = "reviewer-secret-with-24-characters"
    monkeypatch.setenv("RECALLNEXT_REQUIRE_AUTH", "true")
    monkeypatch.setenv("RECALLNEXT_ADMIN_TOKEN", token)
    with TestClient(create_app()) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["write_auth_required"] is True
        payload = {
            "action_id": "ACT-MANIFEST-S200",
            "source_reference": "test://manifest",
            "proposed_fact": {
                "fact_type": "shipment_allocation",
                "shipment_id": "S-200",
                "allocations": {"FARM-A:REC-2026-01": 5},
            },
            "content_hash": "authcheck012345678",
            "review_status": "PENDING_REVIEW",
        }
        assert (
            client.post(
                "/api/incidents/INC-DEMO-001/evidence", json=payload
            ).status_code
            == 401
        )
        response = client.post(
            "/api/incidents/INC-DEMO-001/evidence",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201


def test_document_endpoint_returns_only_a_reviewable_proposal(monkeypatch):
    token = "reviewer-secret-with-24-characters"
    monkeypatch.setenv("RECALLNEXT_REQUIRE_AUTH", "true")
    monkeypatch.setenv("RECALLNEXT_ADMIN_TOKEN", token)
    monkeypatch.setenv("OPENAI_API_KEY", "provider-secret")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    def extract(self, **kwargs):
        assert kwargs["context"]["target_id"] == "S-200"
        return {
            "proposed_fact": {
                "fact_type": "shipment_allocation",
                "shipment_id": "S-200",
                "allocations": {"FARM-A:REC-2026-01": 5},
            },
            "source_reference": "upload://sha256/abc#manifest.csv",
            "content_hash": "abc123456789",
            "extraction_mode": "OPENAI_RESPONSES_API",
            "model": "test-model",
            "provider_response_id": "resp_test",
            "requires_human_review": True,
        }

    monkeypatch.setattr(
        "backend.services.document_extractor.OpenAIDocumentExtractor.extract", extract
    )
    with TestClient(create_app()) as client:
        before = client.get("/api/incidents/INC-DEMO-001").json()["current_version"]
        unauthorized = client.post(
            "/api/incidents/INC-DEMO-001/evidence-actions/ACT-MANIFEST-S200/extract-document",
            files={"document": ("manifest.csv", b"rows", "text/csv")},
        )
        assert unauthorized.status_code == 401
        response = client.post(
            "/api/incidents/INC-DEMO-001/evidence-actions/ACT-MANIFEST-S200/extract-document",
            files={"document": ("manifest.csv", b"rows", "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["requires_human_review"] is True
        assert (
            client.get("/api/incidents/INC-DEMO-001").json()["current_version"]
            == before
        )
        assert (
            client.get("/api/incidents/INC-DEMO-001/evidence").json()["evidence"] == []
        )


def test_app_lifespan_closes_workflow(monkeypatch):
    workflow = default_workflow()
    closed = False

    def close():
        nonlocal closed
        closed = True

    monkeypatch.setattr(workflow, "close", close)
    monkeypatch.setattr(app_module, "default_workflow", lambda: workflow)

    with TestClient(app_module.create_app()):
        pass

    assert closed is True


def test_incident_decisions_and_actions_match_contract():
    with TestClient(create_app()) as client:
        incident = client.get("/api/incidents/INC-DEMO-001").json()
        decisions = client.get("/api/incidents/INC-DEMO-001/decisions").json()
        actions = client.get("/api/incidents/INC-DEMO-001/evidence-actions").json()
        assert incident["current_version"] == 1
        assert decisions["version"] == 1
        assert len(decisions["decisions"]) == 6
        assert len(actions["actions"]) == 4


def test_human_acceptance_changes_version_but_submission_does_not():
    with TestClient(create_app()) as client:
        example = client.get(
            "/api/incidents/INC-DEMO-001/evidence-actions/ACT-MANIFEST-S200/example-fact"
        ).json()
        proposed = client.post(
            "/api/incidents/INC-DEMO-001/evidence",
            json={
                "action_id": "ACT-MANIFEST-S200",
                "source_reference": "synthetic/manifest.json",
                "proposed_fact": example["proposed_fact"],
                "content_hash": "0123456789abcdef",
                "review_status": "PENDING_REVIEW",
            },
        )
        assert proposed.status_code == 201
        assert client.get("/api/incidents/INC-DEMO-001").json()["current_version"] == 1
        accepted = client.post(
            f"/api/incidents/INC-DEMO-001/evidence/{proposed.json()['evidence_id']}/accept",
            json={"verified_by": "API tester", "expected_version": 1},
        )
        assert accepted.status_code == 200
        assert accepted.json()["current_version"] == 2
        assert accepted.json()["decision_diff"]


def test_stale_review_returns_conflict():
    with TestClient(create_app()) as client:
        proposed = client.post(
            "/api/incidents/INC-DEMO-001/evidence",
            json={
                "action_id": "ACT-MANIFEST-S200",
                "source_reference": "synthetic/manifest.json",
                "proposed_fact": {
                    "fact_type": "shipment_allocation",
                    "shipment_id": "S-200",
                    "allocations": {"FARM-A:REC-2026-01": 5},
                },
                "content_hash": "fedcba9876543210",
                "review_status": "PENDING_REVIEW",
            },
        ).json()
        response = client.post(
            f"/api/incidents/INC-DEMO-001/evidence/{proposed['evidence_id']}/accept",
            json={"verified_by": "API tester", "expected_version": 2},
        )
        assert response.status_code == 409


def test_malformed_or_action_mismatched_fact_is_rejected_before_review():
    with TestClient(create_app()) as client:
        base = {
            "action_id": "ACT-MANIFEST-S200",
            "source_reference": "synthetic/manifest.json",
            "content_hash": "invalid001234567",
            "review_status": "PENDING_REVIEW",
        }
        malformed = client.post(
            "/api/incidents/INC-DEMO-001/evidence",
            json={
                **base,
                "proposed_fact": {
                    "fact_type": "shipment_allocation",
                    "shipment_id": "S-200",
                    "allocations": {"FARM-A:REC-2026-01": "five"},
                },
            },
        )
        assert malformed.status_code == 422

        mismatched = client.post(
            "/api/incidents/INC-DEMO-001/evidence",
            json={
                **base,
                "content_hash": "invalid002345678",
                "proposed_fact": {
                    "fact_type": "homogeneous_container",
                    "container_id": "C-100",
                    "lot_id": "FARM-A:REC-2026-01",
                    "homogeneity_verified": True,
                },
            },
        )
        assert mismatched.status_code == 422

        incompatible_observation = client.post(
            "/api/incidents/INC-DEMO-001/evidence",
            json={
                **base,
                "action_id": "ACT-SCAN-C200",
                "content_hash": "invalid003456789",
                "proposed_fact": {
                    "fact_type": "observed_case",
                    "shipment_id": "S-300",
                    "lot_id": "FARM-B:REC-2026-01",
                    "scope": "SINGLE_CASE_ONLY",
                },
            },
        )
        assert incompatible_observation.status_code == 422


def test_human_rejection_keeps_current_version():
    with TestClient(create_app()) as client:
        proposed = client.post(
            "/api/incidents/INC-DEMO-001/evidence",
            json={
                "action_id": "ACT-MANIFEST-S200",
                "source_reference": "synthetic/manifest.json",
                "proposed_fact": {
                    "fact_type": "shipment_allocation",
                    "shipment_id": "S-200",
                    "allocations": {"FARM-A:GOOD-2026-01": 5},
                },
                "content_hash": "reject0012345678",
                "review_status": "PENDING_REVIEW",
            },
        ).json()
        response = client.post(
            f"/api/incidents/INC-DEMO-001/evidence/{proposed['evidence_id']}/reject",
            json={
                "verified_by": "API tester",
                "expected_version": 1,
                "reason": "Source is unreadable",
            },
        )
        assert response.status_code == 200
        assert response.json()["evidence"]["status"] == "REJECTED"
        assert response.json()["current_version"] == 1


def test_retraction_restores_uncertainty_and_creates_a_version():
    with TestClient(create_app()) as client:
        proposed = client.post(
            "/api/incidents/INC-DEMO-001/evidence",
            json={
                "action_id": "ACT-MANIFEST-S200",
                "source_reference": "synthetic/manifest.json",
                "proposed_fact": {
                    "fact_type": "shipment_allocation",
                    "shipment_id": "S-200",
                    "allocations": {"FARM-A:GOOD-2026-01": 5},
                },
                "content_hash": "retract0012345678",
                "review_status": "PENDING_REVIEW",
            },
        ).json()
        accepted = client.post(
            f"/api/incidents/INC-DEMO-001/evidence/{proposed['evidence_id']}/accept",
            json={"verified_by": "API tester", "expected_version": 1},
        )
        assert accepted.status_code == 200

        retracted = client.post(
            f"/api/incidents/INC-DEMO-001/evidence/{proposed['evidence_id']}/retract",
            json={
                "verified_by": "API tester",
                "expected_version": 2,
                "reason": "Manifest withdrawn by source owner",
            },
        )

        assert retracted.status_code == 200
        assert retracted.json()["evidence"]["status"] == "RETRACTED"
        assert retracted.json()["current_version"] == 3
        decisions = client.get("/api/incidents/INC-DEMO-001/decisions?version=3").json()
        s200 = next(
            item for item in decisions["decisions"] if item["shipment_id"] == "S-200"
        )
        assert s200["status"] == "POSSIBLE_INCLUSION"
