"""Shared helper: convert a failed ToolResult (Phase 5) into the
documented HTTP error envelope — FastAPI API Contract Specification v1.0
§14:

    {
      "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable safe message",
        "request_id": "REQ-001",
        "details": null
      }
    }

Reuses the existing Phase 2 ErrorResponse/ErrorDetail schemas rather
than inventing a second error format. Only failure ToolResults are
converted here — success paths return their `.data` dict directly from
each route so FastAPI validates/serializes it against the declared
response_model.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.schemas.common import ErrorDetail, ErrorResponse
from app.core.logging_config import request_id_ctx_var
from app.tools.tool_result import ToolResult

# Flagged assumption (see Phase 6 report): maps each documented tool/
# service error code (Service Design §22 / Tool Contract §16) to the
# HTTP status from the Error Contract table (FastAPI Contract §14).
# Service Design §22 lists ValidationFailure as "400/422" without
# choosing one; 400 is used here so it stays visually distinct from
# FastAPI's own automatic 422 request-body-validation responses, per
# Phase 6 instruction 9 ("validation errors should use FastAPI/
# Pydantic's normal validation mechanism unless the specification
# explicitly defines another format").
STATUS_BY_CODE: dict[str, int] = {
    "DOCTOR_NOT_FOUND": 404,
    "DOCTOR_INACTIVE": 409,
    "OUTSIDE_AVAILABILITY": 409,
    "INVALID_SLOT_TIME": 409,
    "SLOT_UNAVAILABLE": 409,
    "APPOINTMENT_NOT_FOUND": 404,
    "INVALID_APPOINTMENT_STATE": 409,
    "UNAUTHORIZED": 403,
    "REPOSITORY_ERROR": 500,
    "VALIDATION_ERROR": 400,
}


def tool_result_to_response(result: ToolResult, request: Request) -> JSONResponse:
    """Build the documented error envelope for a failed ToolResult.
    Caller is responsible for checking `result.success is False` first.
    """
    assert result.error is not None, "tool_result_to_response requires a failed ToolResult"
    status_code = STATUS_BY_CODE.get(result.error.code, 500)
    envelope = ErrorResponse(
        error=ErrorDetail(
            code=result.error.code,
            message=result.error.message,
            request_id=request_id_ctx_var.get(),
            details=None,
        )
    )
    return JSONResponse(status_code=status_code, content=envelope.model_dump())
