"""Validated API request models for the human evidence boundary."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class EvidenceSubmission(BaseModel):
    action_id: str = Field(min_length=1, max_length=64)
    source_reference: str = Field(min_length=1, max_length=2000)
    proposed_fact: dict[str, Any]
    content_hash: str = Field(min_length=8, max_length=128)
    review_status: Literal["PENDING_REVIEW"] = "PENDING_REVIEW"

    @field_validator("proposed_fact")
    @classmethod
    def require_fact_type(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not str(value.get("fact_type", "")).strip():
            raise ValueError("proposed_fact.fact_type is required")
        return value


class EvidenceAcceptance(BaseModel):
    verified_by: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=1)


class EvidenceRejection(EvidenceAcceptance):
    reason: str = Field(min_length=1, max_length=1000)
