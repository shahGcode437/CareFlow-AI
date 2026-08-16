"""Phase 2 schema validation tests.

Verifies the Pydantic data-contract layer matches the approved Pydantic
Schema & Data Contract Specification v1.0: required fields, optional
fields, enum values, and the two explicit validation rules the spec
calls out (AppointmentCreate.patient_name min length 2,
AppointmentRejection.reason min length 3).

These are schema-level tests only — no repository, service, or Excel
access is exercised here (none exists yet).
"""

from datetime import date, datetime, time

import pytest
from pydantic import ValidationError

from app.api.schemas.appointment import (
    AppointmentApproval,
    AppointmentCancel,
    AppointmentCreate,
    AppointmentRejection,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentUpdate,
)
from app.api.schemas.availability import (
    AlternativeSlot,
    AlternativeSlotsResponse,
    AvailabilityRequest,
    AvailabilityResponse,
)
from app.api.schemas.common import ChatRequest, ChatResponse, ErrorDetail, ErrorResponse
from app.api.schemas.doctor import Doctor, DoctorAvailability


# --- AppointmentStatus enum -------------------------------------------------

def test_appointment_status_has_exactly_the_documented_values():
    assert {s.value for s in AppointmentStatus} == {
        "Pending",
        "Confirmed",
        "Rejected",
        "Cancelled",
        "Completed",
        "NoShow",
    }


# --- AppointmentCreate -------------------------------------------------------

def test_appointment_create_valid():
    a = AppointmentCreate(
        patient_name="Demo Patient",
        patient_phone="03000000000",
        doctor_id="DOC-001",
        doctor_name="Dr. Ahmed",
        service="General Consultation",
        appointment_date=date(2026, 8, 16),
        appointment_time=time(17, 0),
        notes=None,
    )
    assert a.doctor_id == "DOC-001"
    assert a.notes is None


def test_appointment_create_rejects_short_patient_name():
    with pytest.raises(ValidationError):
        AppointmentCreate(
            patient_name="A",  # < 2 chars, spec §4
            patient_phone="03000000000",
            doctor_id="DOC-001",
            doctor_name="Dr. Ahmed",
            service="General Consultation",
            appointment_date=date(2026, 8, 16),
            appointment_time=time(17, 0),
        )


def test_appointment_create_requires_all_mandatory_fields():
    with pytest.raises(ValidationError):
        AppointmentCreate(patient_name="Demo Patient")  # missing required fields


# --- AppointmentUpdate --------------------------------------------------------

def test_appointment_update_all_fields_optional():
    u = AppointmentUpdate()
    assert u.doctor_id is None
    assert u.appointment_date is None


def test_appointment_update_does_not_expose_locked_fields():
    # appointment_id/status/created_at/updated_at must not be accepted fields
    # on the model at all (spec §5).
    field_names = set(AppointmentUpdate.model_fields.keys())
    assert "appointment_id" not in field_names
    assert "status" not in field_names
    assert "created_at" not in field_names
    assert "updated_at" not in field_names


# --- AppointmentResponse -------------------------------------------------------

def test_appointment_response_round_trip():
    r = AppointmentResponse(
        appointment_id="APT-001",
        patient_name="Demo Patient",
        patient_phone="03000000000",
        doctor_id="DOC-001",
        doctor_name="Dr. Ahmed",
        service="General Consultation",
        appointment_date=date(2026, 8, 16),
        appointment_time=time(17, 0),
        status=AppointmentStatus.PENDING,
        created_at=datetime(2026, 8, 16, 10, 0, 0),
        updated_at=datetime(2026, 8, 16, 10, 0, 0),
        notes=None,
    )
    assert r.status == AppointmentStatus.PENDING
    assert r.model_dump()["status"] == "Pending"


# --- Cancellation / Staff actions ---------------------------------------------

def test_appointment_cancel_reason_optional():
    c = AppointmentCancel()
    assert c.reason is None


def test_appointment_approval_notes_optional():
    ap = AppointmentApproval()
    assert ap.notes is None


def test_appointment_rejection_requires_reason_min_length_3():
    with pytest.raises(ValidationError):
        AppointmentRejection(reason="no")  # 2 chars, spec §10 requires >= 3

    r = AppointmentRejection(reason="Doctor unavailable")
    assert r.reason == "Doctor unavailable"


def test_appointment_rejection_reason_is_required():
    with pytest.raises(ValidationError):
        AppointmentRejection()


# --- Availability --------------------------------------------------------------

def test_availability_request_and_response():
    req = AvailabilityRequest(
        doctor_id="DOC-001",
        appointment_date=date(2026, 8, 16),
        appointment_time=time(17, 0),
    )
    assert req.service is None

    resp = AvailabilityResponse(
        available=True,
        doctor_id="DOC-001",
        appointment_date=date(2026, 8, 16),
        appointment_time=time(17, 0),
        message="The requested slot is available.",
    )
    assert resp.available is True


def test_alternative_slots_response_nested_model():
    resp = AlternativeSlotsResponse(
        requested_slot_available=False,
        alternatives=[
            AlternativeSlot(
                doctor_id="DOC-001",
                doctor_name="Dr. Ahmed",
                appointment_date=date(2026, 8, 16),
                appointment_time=time(17, 30),
            )
        ],
    )
    assert len(resp.alternatives) == 1
    assert resp.alternatives[0].appointment_time == time(17, 30)


# --- Doctor / DoctorAvailability -------------------------------------------------

def test_doctor_schema():
    d = Doctor(doctor_id="DOC-001", doctor_name="Dr. Ahmed", specialty="General", active=True)
    assert d.active is True


def test_doctor_availability_schema():
    da = DoctorAvailability(
        availability_id="AVAIL-001",
        doctor_id="DOC-001",
        day_of_week="Sunday",
        start_time=time(9, 0),
        end_time=time(17, 0),
        slot_duration_minutes=30,
        active=True,
    )
    assert da.slot_duration_minutes == 30


# --- Common: error envelope + chat contracts -------------------------------------

def test_error_response_envelope():
    err = ErrorResponse(
        error=ErrorDetail(
            code="SLOT_UNAVAILABLE",
            message="The requested slot is no longer available.",
            request_id="REQ-001",
        )
    )
    assert err.error.code == "SLOT_UNAVAILABLE"
    assert err.error.details is None


def test_chat_request_and_response():
    req = ChatRequest(message="Mujhe Sunday 5 PM Dr. Ahmed ki appointment chahiye.")
    assert req.session_id is None

    resp = ChatResponse(
        message="Here are some available times.",
        intent="check_availability",
        requires_staff_review=False,
        request_id="REQ-001",
    )
    assert resp.data is None
