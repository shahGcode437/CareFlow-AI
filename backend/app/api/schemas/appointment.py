"""Appointment domain schemas.

Implements Pydantic Schema & Data Contract Specification v1.0 §3-6, §9-10
exactly. Field names, types, and validation rules are taken verbatim from
that document. Business rules (availability, conflicts, state-transition
legality) are explicitly NOT implemented here — per spec §1 and §19,
those belong to the Appointment Service (Phase 4).
"""

from datetime import date, datetime, time
from enum import Enum

from pydantic import BaseModel, Field


class AppointmentStatus(str, Enum):
    """Spec §3 — Appointment Status Enum.

    Only these six values are valid for the MVP status field, unless a
    future specification version changes the enum.
    """

    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"
    NOSHOW = "NoShow"


class AppointmentCreate(BaseModel):
    """Spec §4 — represents a request to create an appointment."""

    patient_name: str = Field(..., min_length=2)
    patient_phone: str = Field(
        ...,
        min_length=1,
        description=(
            "Validated contact string; exact phone policy remains "
            "configurable (Open Decision, spec §21)."
        ),
    )
    doctor_id: str
    doctor_name: str
    service: str
    appointment_date: date
    appointment_time: time
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    """Spec §5 — fields that may change during rescheduling/update.

    Intentionally does NOT expose appointment_id, status, created_at, or
    updated_at as freely editable fields, per spec §5.
    """

    doctor_id: str | None = None
    doctor_name: str | None = None
    service: str | None = None
    appointment_date: date | None = None
    appointment_time: time | None = None
    notes: str | None = None


class AppointmentResponse(BaseModel):
    """Spec §6 — a complete appointment returned by the API/service."""

    appointment_id: str
    patient_name: str
    patient_phone: str
    doctor_id: str
    doctor_name: str
    service: str
    appointment_date: date
    appointment_time: time
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime
    notes: str | None = None


class AppointmentCancel(BaseModel):
    """Spec §9 — Cancellation Schema.

    The appointment ID is supplied through the endpoint path/operation
    context rather than the request body (spec §9), so it is not a field
    here.
    """

    reason: str | None = None


class AppointmentApproval(BaseModel):
    """Spec §10 — Staff Action Schemas: AppointmentApproval."""

    notes: str | None = None


class AppointmentRejection(BaseModel):
    """Spec §10 — Staff Action Schemas: AppointmentRejection.

    Reason is required with a minimum of 3 characters, per spec §10.
    """

    reason: str = Field(..., min_length=3)
