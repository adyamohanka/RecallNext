"""Bearer-token protection for state-changing RecallNext endpoints."""

from __future__ import annotations

import hmac
import os
from collections.abc import Mapping
from dataclasses import dataclass

from fastapi import Header, HTTPException

from backend.config import ConfigurationError


def _boolean(environment: Mapping[str, str], name: str, default: bool) -> bool:
    raw = environment.get(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false")


@dataclass(frozen=True)
class WriteAuth:
    """Validate a runtime bearer token without exposing it to the frontend."""

    required: bool
    token: str | None

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> WriteAuth:
        values = os.environ if environment is None else environment
        required = _boolean(values, "RECALLNEXT_REQUIRE_AUTH", True)
        token = values.get("RECALLNEXT_ADMIN_TOKEN", "").strip() or None
        if required and (token is None or len(token) < 24):
            raise ConfigurationError(
                "RECALLNEXT_ADMIN_TOKEN must contain at least 24 characters when "
                "RECALLNEXT_REQUIRE_AUTH is true"
            )
        return cls(required=required, token=token)

    def require(self, authorization: str | None = Header(default=None)) -> None:
        if not self.required:
            return
        scheme, separator, supplied = (authorization or "").partition(" ")
        valid = (
            separator == " "
            and scheme.lower() == "bearer"
            and bool(supplied)
            and self.token is not None
            and hmac.compare_digest(supplied, self.token)
        )
        if not valid:
            raise HTTPException(
                status_code=401,
                detail="A valid reviewer access key is required",
                headers={"WWW-Authenticate": "Bearer"},
            )
