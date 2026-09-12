import pytest

from backend.services.recall_workflow import ConflictError, default_workflow


def submission(workflow, fact=None, content_hash="abc12345"):
    return workflow.submit_evidence(
        {
            "action_id": "ACT-MANIFEST-S200",
            "source_reference": "synthetic/manifest.json",
            "proposed_fact": fact or workflow.example_fact("ACT-MANIFEST-S200"),
            "content_hash": content_hash,
            "review_status": "PENDING_REVIEW",
        }
    )


def test_fixture_workflow_builds_complete_initial_state():
    workflow = default_workflow()
    incident = workflow.incident()
    assert incident["data_source"] == "SYNTHETIC_FIXTURE"
    assert incident["summary"]["feasible_scenarios"] == 125
    assert incident["summary"]["status_counts"] == {
        "POSSIBLE_INCLUSION": 4,
        "EXCLUDED_UNDER_ASSUMPTIONS": 2,
    }
    assert len(workflow.evidence_actions()["actions"]) == 4


def test_submission_does_not_change_decisions_until_acceptance():
    workflow = default_workflow()
    before = workflow.decisions()
    evidence = submission(workflow)
    assert workflow.current_version == 1
    assert workflow.decisions() == before
    result = workflow.accept_evidence(evidence["evidence_id"], "Reviewer", 1)
    assert result["current_version"] == 2
    assert result["decision_diff"][0]["new_status"] == "CONFIRMED_INCLUSION"


def test_stale_acceptance_is_rejected():
    workflow = default_workflow()
    evidence = submission(workflow)
    with pytest.raises(ConflictError):
        workflow.accept_evidence(evidence["evidence_id"], "Reviewer", 2)


def test_rejection_records_review_without_changing_version():
    workflow = default_workflow()
    before = workflow.decisions()
    evidence = submission(workflow)
    result = workflow.reject_evidence(
        evidence["evidence_id"], "Reviewer", 1, "Source is unreadable"
    )
    assert result["evidence"]["status"] == "REJECTED"
    assert result["evidence"]["rejection_reason"] == "Source is unreadable"
    assert result["decision_diff"] == []
    assert workflow.current_version == 1
    assert workflow.decisions() == before


def test_only_current_pending_evidence_is_deduplicated():
    workflow = default_workflow()
    pending = submission(workflow, content_hash="repeatable-hash")
    duplicate = submission(workflow, content_hash="repeatable-hash")

    assert duplicate["duplicate"] is True
    assert duplicate["evidence_id"] == pending["evidence_id"]

    workflow.reject_evidence(pending["evidence_id"], "Reviewer", 1, "Unreadable")
    after_rejection = submission(workflow, content_hash="repeatable-hash")

    assert after_rejection["duplicate"] is False
    assert after_rejection["evidence_id"] != pending["evidence_id"]


def test_stale_duplicate_hash_creates_a_current_reviewable_proposal():
    workflow = default_workflow()
    stale = submission(workflow, content_hash="stale-repeatable-hash")
    advancing = submission(workflow, content_hash="advancing-hash")
    workflow.accept_evidence(advancing["evidence_id"], "Reviewer", 1)

    current = submission(workflow, content_hash="stale-repeatable-hash")

    assert current["duplicate"] is False
    assert current["incident_version"] == 2
    assert current["evidence_id"] != stale["evidence_id"]


def test_contradiction_creates_unresolved_version():
    workflow = default_workflow()
    fact = {
        "fact_type": "shipment_allocation",
        "shipment_id": "S-200",
        "allocations": {"FARM-B:REC-2026-01": 5},
    }
    evidence = submission(workflow, fact, "conflict1")
    result = workflow.accept_evidence(evidence["evidence_id"], "Reviewer", 1)
    assert result["solver_status"] == "CONFLICT"
    assert all(
        item["status"] == "UNRESOLVED" for item in workflow.decisions()["decisions"]
    )
