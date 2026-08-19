"""Staff-only appointment action routes.

Implements FastAPI API Contract Specification v1.0 API-008 (approve) and
API-009 (reject).

API-007 (GET /staff/pending-appointments) is documented in the API
contract but is DELIBERATELY NOT implemented in Phase 6 — flagged gap,
see the Phase 6 report: no Phase 4 AppointmentService method and no
Phase 5 tool exist to power it (Service Design §4's core 8-method
interface and Tool Contract §3's 8-tool inventory both omit a "list
pending" capability, and AppointmentRepository has no "list all"
method). Implementing it here would require either querying a
repository directly from a route — violating the required layering —
or inventing a new service/tool method, which is out of Phase 6 scope.

Real staff authentication is explicitly out of scope (every spec that
mentions it calls the mechanism an open decision). The `is_staff`/
`staff_id` fields below are the SAME placeholder mechanism
AppointmentService already defined in Phase 4 (StaffContext) — this is
a flagged, temporary bridge, not a documented API contract. Routes do
not decide authorization themselves; they only forward caller-supplied
values, exactly as the Phase 5 tools already do.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.dependencies import get_appointment_tools
from app.api.routes._tool_result_response import tool_result_to_response
from app.api.schemas.appointment import AppointmentResponse
from app.tools.appointment_tools import AppointmentTools

router = APIRouter(prefix="/staff", tags=["staff"])


class StaffApprovalRequest(BaseModel):
    """HTTP body for API-008. Wraps the documented AppointmentApproval
    field (notes) plus the flagged staff-context placeholder — see this
    module's docstring."""

    notes: str | None = None
    is_staff: bool = False
    staff_id: str | None = None


class StaffRejectionRequest(BaseModel):
    """HTTP body for API-009. Wraps the documented AppointmentRejection
    field (reason, required, min length 3 — matching Pydantic Schema
    Spec §10) plus the flagged staff-context placeholder."""

    reason: str = Field(..., min_length=3)
    is_staff: bool = False
    staff_id: str | None = None


@router.post("/appointments/{appointment_id}/approve", response_model=AppointmentResponse)
def approve_appointment(
    appointment_id: str,
    body: StaffApprovalRequest,
    http_request: Request,
    tools: AppointmentTools = Depends(get_appointment_tools),
):
    """API-008."""
    result = tools.approve_appointment(
        appointment_id=appointment_id,
        notes=body.notes,
        is_staff=body.is_staff,
        staff_id=body.staff_id,
    )
    if not result.success:
        return tool_result_to_response(result, http_request)
    return result.data


@router.post("/appointments/{appointment_id}/reject", response_model=AppointmentResponse)
def reject_appointment(
    appointment_id: str,
    body: StaffRejectionRequest,
    http_request: Request,
    tools: AppointmentTools = Depends(get_appointment_tools),
):
    """API-009."""
    result = tools.reject_appointment(
        appointment_id=appointment_id,
        reason=body.reason,
        is_staff=body.is_staff,
        staff_id=body.staff_id,
    )
    if not result.success:
        return tool_result_to_response(result, http_request)
    return result.data
