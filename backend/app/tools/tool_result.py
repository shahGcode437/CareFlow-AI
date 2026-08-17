"""Structured tool result/error shape.

Implements the exact JSON shape documented in Appointment Agent Tool
Contract Specification v1.0 §16 ("Tool Error Contract"):

    {
      "success": false,
      "error": {
        "code": "SLOT_UNAVAILABLE",
        "message": "The requested slot is no longer available.",
        "retryable": true
      }
    }

On success, `data` holds the tool's structured result (a plain dict —
the relevant Phase 2 response schema's `model_dump()`), and `error` is
None. On failure, `data` is None and `error` is populated.
"""

from typing import Any

from pydantic import BaseModel

# Flagged assumption (see Phase 5 report): Tool Contract §16 shows only
# one worked "retryable" example (SLOT_UNAVAILABLE -> true). No table
# maps this flag for every code, so this mapping is an explicit
# interpretation, not a documented fact: an error is considered
# retryable if different input (a different slot/appointment/reason)
# could plausibly resolve it.
RETRYABLE_BY_CODE: dict[str, bool] = {
    "DOCTOR_NOT_FOUND": False,
    "DOCTOR_INACTIVE": False,
    "OUTSIDE_AVAILABILITY": True,
    "INVALID_SLOT_TIME": True,
    "SLOT_UNAVAILABLE": True,
    "APPOINTMENT_NOT_FOUND": False,
    "INVALID_APPOINTMENT_STATE": False,
    "UNAUTHORIZED": False,
    "REPOSITORY_ERROR": True,
    "VALIDATION_ERROR": True,
}


class ToolError(BaseModel):
    code: str
    message: str
    retryable: bool


class ToolResult(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    error: ToolError | None = None

    @classmethod
    def ok(cls, data: dict[str, Any]) -> "ToolResult":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, code: str, message: str) -> "ToolResult":
        return cls(
            success=False,
            data=None,
            error=ToolError(code=code, message=message, retryable=RETRYABLE_BY_CODE.get(code, False)),
        )
