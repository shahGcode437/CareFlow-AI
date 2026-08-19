"""Appointment HTTP routes.

Implements FastAPI API Contract Specification v1.0's appointment
endpoints: API-002 (check-availability), API-003 (get), API-004
(create), API-005 (update/reschedule), API-006 (cancel).

Routes are intentionally thin: parse/validate the HTTP request via the
existing Phase 2 Pydantic schemas, call the matching Phase 5
AppointmentTools method, and translate the ToolResult into an HTTP
response. No availability/conflict/state-transition logic exists here —
all of that is inside AppointmentService (Phase 4), reached exclusively
through AppointmentTools (Phase 5).

No explicit success status_code is set on any route: no specification
document states a success status (e.g. 201 for creation) for any
endpoint — only the Error Contract table documents failure statuses —
so FastAPI's plain default (200) is used rather than assuming an
undocumented REST convention.
"""

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_appointment_tools
from app.api.routes._tool_result_response import tool_result_to_response
from app.api.schemas.appointment import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.api.schemas.availability import AvailabilityRequest, AvailabilityResponse
from app.tools.appointment_tools import AppointmentTools

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/check-availability", response_model=AvailabilityResponse)
def check_availability(
    body: AvailabilityRequest,
    http_request: Request,
    tools: AppointmentTools = Depends(get_appointment_tools),
):
    """API-002. Always returns an AvailabilityResponse body —
    unavailability is reported IN the response (available=False), not
    as an HTTP error, matching AppointmentService.check_availability()'s
    own documented behavior (Phase 4). The failure branch below only
    handles the defensive/unexpected case, since FastAPI already
    validates the request body before this function runs.
    """
    result = tools.check_availability(
        doctor_id=body.doctor_id,
        appointment_date=body.appointment_date.isoformat(),
        appointment_time=body.appointment_time.isoformat(),
        service=body.service,
    )
    if not result.success:
        return tool_result_to_response(result, http_request)
    return result.data


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: str,
    http_request: Request,
    tools: AppointmentTools = Depends(get_appointment_tools),
):
    """API-003."""
    result = tools.get_appointment(appointment_id)
    if not result.success:
        return tool_result_to_response(result, http_request)
    return result.data


@router.post("", response_model=AppointmentResponse)
def create_appointment(
    body: AppointmentCreate,
    http_request: Request,
    tools: AppointmentTools = Depends(get_appointment_tools),
):
    """API-004."""
    result = tools.create_appointment(
        patient_name=body.patient_name,
        patient_phone=body.patient_phone,
        doctor_id=body.doctor_id,
        doctor_name=body.doctor_name,
        service=body.service,
        appointment_date=body.appointment_date.isoformat(),
        appointment_time=body.appointment_time.isoformat(),
        notes=body.notes,
    )
    if not result.success:
        return tool_result_to_response(result, http_request)
    return result.data


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: str,
    body: AppointmentUpdate,
    http_request: Request,
    tools: AppointmentTools = Depends(get_appointment_tools),
):
    """API-005. Re-checking availability when scheduling fields change
    is handled entirely inside AppointmentService.update_appointment()
    (Phase 4) — this route does not duplicate that decision.
    """
    result = tools.update_appointment(
        appointment_id=appointment_id,
        doctor_id=body.doctor_id,
        doctor_name=body.doctor_name,
        service=body.service,
        appointment_date=body.appointment_date.isoformat() if body.appointment_date else None,
        appointment_time=body.appointment_time.isoformat() if body.appointment_time else None,
        notes=body.notes,
    )
    if not result.success:
        return tool_result_to_response(result, http_request)
    return result.data


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: str,
    body: AppointmentCancel,
    http_request: Request,
    tools: AppointmentTools = Depends(get_appointment_tools),
):
    """API-006. Always a status transition — never a row deletion,
    since neither the tool, service, nor repository beneath this route
    has a delete capability.
    """
    result = tools.cancel_appointment(appointment_id=appointment_id, reason=body.reason)
    if not result.success:
        return tool_result_to_response(result, http_request)
    return result.data
