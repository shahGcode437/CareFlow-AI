"""Shared/common schemas.

Contains two documented contract groups that don't belong to a single
domain module:

  1. The error envelope from FastAPI API Contract Specification v1.0 §14.
  2. ChatRequest / ChatResponse from FastAPI API Contract Specification
     v1.0 §4.1-4.2 (used by POST /chat).

Neither spec's proposed schema module layout (Pydantic spec §20 /
FastAPI spec §19) names a dedicated file for these, so they are grouped
here as shared/API-level contracts rather than invented into a new,
undocumented module.
"""

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """FastAPI API Contract Specification §14 — error envelope, inner object."""

    code: str
    message: str
    request_id: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """FastAPI API Contract Specification §14 — error envelope, outer object."""

    error: ErrorDetail


class ChatRequest(BaseModel):
    """FastAPI API Contract Specification §4.1 — Chat Request."""

    message: str
    session_id: str | None = None
    patient_phone: str | None = None


class ChatResponse(BaseModel):
    """FastAPI API Contract Specification §4.2 — Chat Response."""

    message: str
    intent: str
    data: dict[str, Any] | None = None
    requires_staff_review: bool
    request_id: str
