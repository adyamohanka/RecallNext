"""RecallNext FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.models import EvidenceAcceptance, EvidenceRejection, EvidenceSubmission
from backend.services.recall_workflow import (
    ConflictError,
    WorkflowError,
    default_workflow,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="RecallNext API",
        version="0.1.0",
        description="Deterministic recall investigation with explicit human evidence review.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    workflow = default_workflow()
    app.state.workflow = workflow

    def require_incident(incident_id: str) -> None:
        if incident_id != workflow.incident_id:
            raise HTTPException(status_code=404, detail="incident not found")

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "data_source": workflow.data_source,
            "database_connected": False,
            "detail": workflow.data_source_detail,
        }

    @app.get("/api/incidents/{incident_id}")
    def get_incident(incident_id: str) -> dict[str, object]:
        require_incident(incident_id)
        return workflow.incident()

    @app.get("/api/incidents/{incident_id}/decisions")
    def get_decisions(
        incident_id: str, version: int | None = Query(default=None, ge=1)
    ) -> dict[str, object]:
        require_incident(incident_id)
        try:
            return workflow.decisions(version)
        except WorkflowError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/api/incidents/{incident_id}/evidence-actions")
    def get_evidence_actions(incident_id: str) -> dict[str, object]:
        require_incident(incident_id)
        return workflow.evidence_actions()

    @app.get("/api/incidents/{incident_id}/diff")
    def get_diff(
        incident_id: str, from_version: int = Query(ge=1), to_version: int = Query(ge=1)
    ) -> dict[str, object]:
        require_incident(incident_id)
        try:
            return {
                "incident_id": incident_id,
                "from_version": from_version,
                "to_version": to_version,
                "changes": workflow.diff(from_version, to_version),
            }
        except WorkflowError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/api/incidents/{incident_id}/evidence-actions/{action_id}/example-fact")
    def example_fact(incident_id: str, action_id: str) -> dict[str, object]:
        require_incident(incident_id)
        if not workflow.has_action(action_id):
            raise HTTPException(status_code=404, detail="action not found")
        return {
            "action_id": action_id,
            "proposed_fact": workflow.example_fact(action_id),
            "extraction_mode": "SYNTHETIC_EXAMPLE",
        }

    @app.post("/api/incidents/{incident_id}/evidence", status_code=201)
    def submit_evidence(
        incident_id: str, submission: EvidenceSubmission
    ) -> dict[str, object]:
        require_incident(incident_id)
        try:
            return workflow.submit_evidence(submission.model_dump())
        except WorkflowError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/incidents/{incident_id}/evidence/{evidence_id}/accept")
    def accept_evidence(
        incident_id: str, evidence_id: str, acceptance: EvidenceAcceptance
    ) -> dict[str, object]:
        require_incident(incident_id)
        try:
            return workflow.accept_evidence(
                evidence_id, acceptance.verified_by, acceptance.expected_version
            )
        except ConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except WorkflowError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/incidents/{incident_id}/evidence/{evidence_id}/reject")
    def reject_evidence(
        incident_id: str, evidence_id: str, rejection: EvidenceRejection
    ) -> dict[str, object]:
        require_incident(incident_id)
        try:
            return workflow.reject_evidence(
                evidence_id,
                rejection.verified_by,
                rejection.expected_version,
                rejection.reason,
            )
        except ConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except WorkflowError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    return app


app = create_app()
