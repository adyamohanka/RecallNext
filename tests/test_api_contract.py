from fastapi.testclient import TestClient

from backend.app import create_app


def test_health_labels_fixture_mode():
    with TestClient(create_app()) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["data_source"] == "SYNTHETIC_FIXTURE"
        assert response.json()["database_connected"] is False


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
                    "fact_type": "observed_case",
                    "container_id": "C-200",
                    "lot_id": "FARM-A:GOOD-2026-01",
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


def test_human_rejection_keeps_current_version():
    with TestClient(create_app()) as client:
        proposed = client.post(
            "/api/incidents/INC-DEMO-001/evidence",
            json={
                "action_id": "ACT-MANIFEST-S200",
                "source_reference": "synthetic/manifest.json",
                "proposed_fact": {
                    "fact_type": "observed_case",
                    "shipment_id": "S-200",
                    "lot_id": "FARM-A:GOOD-2026-01",
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
