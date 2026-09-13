"""RecallNext FastAPI application."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.models import (
    EvidenceAcceptance,
    EvidenceRejection,
    EvidenceRetraction,
    EvidenceSubmission,
)
from backend.security import WriteAuth
from backend.services.document_extractor import (
    DocumentExtractionError,
    DocumentExtractionUnavailable,
    OpenAIDocumentExtractor,
    OpenAIExtractionConfig,
    UnsupportedDocumentError,
)
from backend.services.recall_workflow import (
    ConflictError,
    WorkflowError,
    default_workflow,
)


def create_app() -> FastAPI:
    workflow = default_workflow()
    write_auth = WriteAuth.from_environment()
    extraction_config = OpenAIExtractionConfig.from_environment()
    extractor = (
        OpenAIDocumentExtractor(extraction_config) if extraction_config else None
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            if extractor is not None:
                extractor.close()
            workflow.close()

    app = FastAPI(
        title="RecallNext API",
        version="0.1.0",
        description="Deterministic recall investigation with explicit human evidence review.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            item.strip()
            for item in os.environ.get(
                "RECALLNEXT_ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if item.strip()
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.state.workflow = workflow
    app.state.document_extractor = extractor
    app.state.write_auth = write_auth

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
            "form-action 'self'; img-src 'self' data:; object-src 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    def require_incident(incident_id: str) -> None:
        if incident_id != workflow.incident_id:
            raise HTTPException(status_code=404, detail="incident not found")

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "data_source": workflow.data_source,
            "database_connected": workflow.database_connected,
            "detail": workflow.data_source_detail,
            "write_auth_required": write_auth.required,
            "document_extraction_configured": extractor is not None,
        }

    @app.get("/api/incidents")
    def list_incidents() -> dict[str, object]:
        incident = workflow.incident()
        return {
            "incidents": [
                {
                    "incident_id": incident["incident_id"],
                    "current_version": incident["current_version"],
                    "title": incident["title"],
                    "status": "OPEN",
                    "data_source": incident["data_source"],
                }
            ]
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
            "source_reference": workflow.source_reference(action_id),
            "extraction_mode": "DETERMINISTIC_CANDIDATE_PREVIEW",
        }

    @app.get("/api/incidents/{incident_id}/evidence")
    def get_evidence(incident_id: str) -> dict[str, object]:
        require_incident(incident_id)
        return workflow.evidence_log()

    @app.post(
        "/api/incidents/{incident_id}/evidence-actions/{action_id}/extract-document",
        dependencies=[Depends(write_auth.require)],
    )
    async def extract_document(
        incident_id: str,
        action_id: str,
        document: Annotated[UploadFile, File()],
    ) -> dict[str, object]:
        require_incident(incident_id)
        if not workflow.has_action(action_id):
            raise HTTPException(status_code=404, detail="action not found")
        if extractor is None:
            raise HTTPException(
                status_code=503,
                detail="Live document extraction is not configured",
            )
        content = await document.read(extractor.config.max_document_bytes + 1)
        await document.close()
        if len(content) > extractor.config.max_document_bytes:
            raise HTTPException(
                status_code=413, detail="Uploaded document is too large"
            )
        try:
            result = extractor.extract(
                context=workflow.extraction_context(action_id),
                filename=document.filename,
                content_type=document.content_type,
                content=content,
            )
            workflow.validate_fact(action_id, result["proposed_fact"])
            return {"action_id": action_id, **result}
        except UnsupportedDocumentError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except WorkflowError as error:
            raise HTTPException(
                status_code=422,
                detail=f"Extracted fact failed the action contract: {error}",
            ) from error
        except DocumentExtractionUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except DocumentExtractionError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @app.post(
        "/api/incidents/{incident_id}/evidence",
        status_code=201,
        dependencies=[Depends(write_auth.require)],
    )
    def submit_evidence(
        incident_id: str, submission: EvidenceSubmission
    ) -> dict[str, object]:
        require_incident(incident_id)
        try:
            return workflow.submit_evidence(submission.model_dump())
        except ConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except WorkflowError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post(
        "/api/incidents/{incident_id}/evidence/{evidence_id}/accept",
        dependencies=[Depends(write_auth.require)],
    )
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

    @app.post(
        "/api/incidents/{incident_id}/evidence/{evidence_id}/reject",
        dependencies=[Depends(write_auth.require)],
    )
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

    @app.post(
        "/api/incidents/{incident_id}/evidence/{evidence_id}/retract",
        dependencies=[Depends(write_auth.require)],
    )
    def retract_evidence(
        incident_id: str, evidence_id: str, retraction: EvidenceRetraction
    ) -> dict[str, object]:
        require_incident(incident_id)
        try:
            return workflow.retract_evidence(
                evidence_id,
                retraction.verified_by,
                retraction.expected_version,
                retraction.reason,
            )
        except ConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except WorkflowError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    static_value = os.environ.get("RECALLNEXT_STATIC_DIR", "").strip()
    if static_value:
        static_directory = Path(static_value).resolve()
        if not (static_directory / "index.html").is_file():
            raise RuntimeError(
                f"RECALLNEXT_STATIC_DIR has no compiled index.html: {static_directory}"
            )
        app.mount(
            "/", StaticFiles(directory=static_directory, html=True), name="frontend"
        )

    return app


app = create_app()
