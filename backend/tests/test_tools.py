"""Phase 5 Agent Tools tests.

Uses unittest.mock.MagicMock(spec=AppointmentService) so tools are
tested in isolation from repositories/Excel entirely — these tests
exercise only the tool layer's validate/call/convert behavior, not the
business logic already covered by tests/test_appointment_service.py.
"""

from datetime import date, datetime, time
from unittest.mock import MagicMock

import pytest

from app.api.schemas.appointment import AppointmentResponse, AppointmentStatus
from app.api.schemas.availability import AlternativeSlotsResponse, AvailabilityResponse
from app.services.appointment_service import AppointmentService, StaffContext
from app.services.exceptions import (
    AppointmentNotFound,
    DoctorNotFound,
    SlotUnavailable,
    UnauthorizedAction,
)
from app.tools.appointment_tools import AppointmentTools

SAMPLE_APPOINTMENT = AppointmentResponse(
    appointment_id="APT-001",
    patient_name="Demo Patient",
    patient_phone="03000000000",
    doctor_id="DOC-001",
    doctor_name="Dr. Ahmed",
    service="General Consultation",
    appointment_date=date(2026, 8, 16),
    appointment_time=time(17, 0),
    status=AppointmentStatus.PENDING,
    created_at=datetime(2026, 8, 16, 10, 0),
    updated_at=datetime(2026, 8, 16, 10, 0),
    notes=None,
)


@pytest.fixture()
def mock_service():
    return MagicMock(spec=AppointmentService)


@pytest.fixture()
def tools(mock_service):
    return AppointmentTools(mock_service)


# --- All 8 tools exist -----------------------------------------------------

@pytest.mark.parametrize(
    "tool_name",
    [
        "check_availability",
        "find_alternative_slots",
        "create_appointment",
        "get_appointment",
        "update_appointment",
        "cancel_appointment",
        "approve_appointment",
        "reject_appointment",
    ],
)
def test_tool_exists(tool_name):
    assert hasattr(AppointmentTools, tool_name)
    assert callable(getattr(AppointmentTools, tool_name))


# --- TOOL-001 check_availability -----------------------------------------------

def test_check_availability_calls_service_correctly(tools, mock_service):
    mock_service.check_availability.return_value = AvailabilityResponse(
        available=True,
        doctor_id="DOC-001",
        appointment_date=date(2026, 8, 16),
        appointment_time=time(17, 0),
        message="The requested slot is available.",
    )

    result = tools.check_availability(
        doctor_id="DOC-001", appointment_date="2026-08-16", appointment_time="17:00"
    )

    assert result.success is True
    assert result.data["available"] is True
    assert result.data["message"] == "The requested slot is available."

    mock_service.check_availability.assert_called_once()
    (request_arg,), _ = mock_service.check_availability.call_args
    assert request_arg.doctor_id == "DOC-001"
    assert request_arg.appointment_date == date(2026, 8, 16)
    assert request_arg.appointment_time == time(17, 0)


def test_check_availability_invalid_date_returns_validation_error(tools, mock_service):
    result = tools.check_availability(
        doctor_id="DOC-001", appointment_date="not-a-date", appointment_time="17:00"
    )
    assert result.success is False
    assert result.error.code == "VALIDATION_ERROR"
    assert result.error.retryable is True
    mock_service.check_availability.assert_not_called()


# --- TOOL-002 find_alternative_slots --------------------------------------------

def test_find_alternative_slots_calls_service_correctly(tools, mock_service):
    mock_service.find_alternative_slots.return_value = AlternativeSlotsResponse(
        requested_slot_available=False, alternatives=[]
    )

    result = tools.find_alternative_slots(
        doctor_id="DOC-001",
        appointment_date="2026-08-16",
        appointment_time="17:00",
        preferences={"prefer_morning": True},
    )

    assert result.success is True
    assert result.data["requested_slot_available"] is False

    mock_service.find_alternative_slots.assert_called_once()
    (request_arg, preferences_arg), _ = mock_service.find_alternative_slots.call_args
    assert request_arg.doctor_id == "DOC-001"
    assert preferences_arg == {"prefer_morning": True}


# --- TOOL-003 create_appointment -------------------------------------------------

def test_create_appointment_calls_service_correctly(tools, mock_service):
    mock_service.create_appointment.return_value = SAMPLE_APPOINTMENT

    result = tools.create_appointment(
        patient_name="Demo Patient",
        patient_phone="03000000000",
        doctor_id="DOC-001",
        doctor_name="Dr. Ahmed",
        service="General Consultation",
        appointment_date="2026-08-16",
        appointment_time="17:00",
    )

    assert result.success is True
    assert result.data["appointment_id"] == "APT-001"
    assert result.data["status"] == "Pending"

    mock_service.create_appointment.assert_called_once()
    (request_arg,), _ = mock_service.create_appointment.call_args
    assert request_arg.patient_name == "Demo Patient"
    assert request_arg.doctor_id == "DOC-001"


def test_create_appointment_doctor_not_found_translated(tools, mock_service):
    mock_service.create_appointment.side_effect = DoctorNotFound("Doctor not found.")

    result = tools.create_appointment(
        patient_name="Demo Patient",
        patient_phone="03000000000",
        doctor_id="DOC-999",
        doctor_name="Nobody",
        service="General Consultation",
        appointment_date="2026-08-16",
        appointment_time="17:00",
    )

    assert result.success is False
    assert result.error.code == "DOCTOR_NOT_FOUND"
    assert result.error.retryable is False


def test_create_appointment_conflict_translated(tools, mock_service):
    mock_service.create_appointment.side_effect = SlotUnavailable(
        "The requested slot is already booked."
    )

    result = tools.create_appointment(
        patient_name="Demo Patient",
        patient_phone="03000000000",
        doctor_id="DOC-001",
        doctor_name="Dr. Ahmed",
        service="General Consultation",
        appointment_date="2026-08-16",
        appointment_time="17:00",
    )

    assert result.success is False
    assert result.error.code == "SLOT_UNAVAILABLE"
    assert result.error.retryable is True


# --- TOOL-004 get_appointment --------------------------------------------------

def test_get_appointment_calls_service_correctly(tools, mock_service):
    mock_service.get_appointment.return_value = SAMPLE_APPOINTMENT
    result = tools.get_appointment("APT-001")

    assert result.success is True
    assert result.data["appointment_id"] == "APT-001"
    mock_service.get_appointment.assert_called_once_with("APT-001")


def test_get_appointment_not_found_translated(tools, mock_service):
    mock_service.get_appointment.side_effect = AppointmentNotFound("Appointment not found.")
    result = tools.get_appointment("APT-DOES-NOT-EXIST")

    assert result.success is False
    assert result.error.code == "APPOINTMENT_NOT_FOUND"
    assert result.error.retryable is False


def test_get_appointment_unexpected_error_not_swallowed(tools, mock_service):
    mock_service.get_appointment.side_effect = RuntimeError("unexpected bug")
    with pytest.raises(RuntimeError):
        tools.get_appointment("APT-001")


# --- TOOL-005 update_appointment -----------------------------------------------

def test_update_appointment_only_provided_fields_forwarded(tools, mock_service):
    mock_service.update_appointment.return_value = SAMPLE_APPOINTMENT

    result = tools.update_appointment(appointment_id="APT-001", notes="Updated via tool")

    assert result.success is True
    mock_service.update_appointment.assert_called_once()
    (appt_id_arg, update_arg), _ = mock_service.update_appointment.call_args
    assert appt_id_arg == "APT-001"
    assert update_arg.notes == "Updated via tool"
    assert update_arg.doctor_id is None
    assert update_arg.appointment_date is None
    assert update_arg.appointment_time is None


# --- TOOL-006 cancel_appointment -----------------------------------------------

def test_cancel_appointment_calls_service_correctly(tools, mock_service):
    cancelled = SAMPLE_APPOINTMENT.model_copy(update={"status": AppointmentStatus.CANCELLED})
    mock_service.cancel_appointment.return_value = cancelled

    result = tools.cancel_appointment("APT-001", reason="Patient request")

    assert result.success is True
    assert result.data["status"] == "Cancelled"
    mock_service.cancel_appointment.assert_called_once()
    (appt_id_arg, cancel_arg), _ = mock_service.cancel_appointment.call_args
    assert appt_id_arg == "APT-001"
    assert cancel_arg.reason == "Patient request"


# --- TOOL-007 approve_appointment (staff-only) -----------------------------------

def test_approve_appointment_default_is_staff_false(tools, mock_service):
    mock_service.approve_appointment.side_effect = UnauthorizedAction()

    result = tools.approve_appointment("APT-001")  # is_staff not supplied

    assert result.success is False
    assert result.error.code == "UNAUTHORIZED"
    (appt_id_arg, approval_arg, staff_context_arg), _ = mock_service.approve_appointment.call_args
    assert isinstance(staff_context_arg, StaffContext)
    assert staff_context_arg.is_staff is False


def test_approve_appointment_with_explicit_staff_context(tools, mock_service):
    approved = SAMPLE_APPOINTMENT.model_copy(update={"status": AppointmentStatus.CONFIRMED})
    mock_service.approve_appointment.return_value = approved

    result = tools.approve_appointment("APT-001", is_staff=True, staff_id="staff-001")

    assert result.success is True
    assert result.data["status"] == "Confirmed"
    (_, _, staff_context_arg), _ = mock_service.approve_appointment.call_args
    assert staff_context_arg.is_staff is True
    assert staff_context_arg.staff_id == "staff-001"


# --- TOOL-008 reject_appointment (staff-only) ------------------------------------

def test_reject_appointment_calls_service_correctly(tools, mock_service):
    rejected = SAMPLE_APPOINTMENT.model_copy(update={"status": AppointmentStatus.REJECTED})
    mock_service.reject_appointment.return_value = rejected

    result = tools.reject_appointment("APT-001", reason="Doctor unavailable", is_staff=True)

    assert result.success is True
    assert result.data["status"] == "Rejected"
    (appt_id_arg, rejection_arg, staff_context_arg), _ = mock_service.reject_appointment.call_args
    assert rejection_arg.reason == "Doctor unavailable"
    assert staff_context_arg.is_staff is True


def test_reject_appointment_reason_too_short_returns_validation_error(tools, mock_service):
    result = tools.reject_appointment("APT-001", reason="no", is_staff=True)

    assert result.success is False
    assert result.error.code == "VALIDATION_ERROR"
    mock_service.reject_appointment.assert_not_called()


# --- Boundary: tools must not touch Excel/repositories directly -----------------

def test_tools_source_does_not_reference_excel_or_repositories():
    import inspect

    import app.tools.appointment_tools as tools_module
    import app.tools.tool_result as result_module

    source = inspect.getsource(tools_module) + inspect.getsource(result_module)
    forbidden = ["openpyxl", "pandas", "app.repositories", "import pandas"]
    for token in forbidden:
        assert token not in source, f"Tools layer must not reference '{token}'"
