"""Phase 6 route tests.

Most tests use FastAPI's TestClient with app.dependency_overrides to
inject a MagicMock(spec=AppointmentTools) — no Excel/repositories
involved, per the Phase 6 instruction to not depend on real Excel data
unless an integration test is specifically required. A small number of
integration tests at the bottom use the real tool/service/repository
stack against an isolated TEMPORARY COPY of the workbook, never the
original template, to prove the full chain actually works end to end.
"""

import shutil
from datetime import date, datetime, time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.agents.supervisor import Supervisor
from app.api.dependencies import get_appointment_tools, get_supervisor
from app.api.schemas.appointment import AppointmentResponse, AppointmentStatus
from app.main import app
from app.repositories.appointment_repository import ExcelAppointmentRepository
from app.repositories.availability_repository import ExcelAvailabilityRepository
from app.repositories.doctor_repository import ExcelDoctorRepository
from app.services.appointment_service import AppointmentService
from app.tools.appointment_tools import AppointmentTools
from app.tools.tool_result import ToolResult

ORIGINAL_TEMPLATE = (
    Path(__file__).resolve().parents[1] / "data" / "clinic_appointments_MVP_template.xlsx"
)
SUNDAY = "2026-08-16"

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
def mock_tools():
    return MagicMock(spec=AppointmentTools)


@pytest.fixture()
def client(mock_tools):
    app.dependency_overrides[get_appointment_tools] = lambda: mock_tools
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- Route registration / OpenAPI -------------------------------------------------

def test_health_route_still_works(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_openapi_includes_documented_routes(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]

    assert "post" in paths["/appointments/check-availability"]
    assert "get" in paths["/appointments/{appointment_id}"]
    assert "post" in paths["/appointments"]
    assert "patch" in paths["/appointments/{appointment_id}"]
    assert "post" in paths["/appointments/{appointment_id}/cancel"]
    assert "post" in paths["/staff/appointments/{appointment_id}/approve"]
    assert "post" in paths["/staff/appointments/{appointment_id}/reject"]
    assert "post" in paths["/chat"]  # Phase 7: previously deferred, now implemented

    # API-007 (list pending) is still deliberately NOT implemented — see
    # the Phase 6 report for the flagged gap (unchanged in Phase 7).
    assert "/staff/pending-appointments" not in paths


def test_docs_route_available(client):
    resp = client.get("/docs")
    assert resp.status_code == 200


# --- check_availability -------------------------------------------------------

def test_check_availability_success(client, mock_tools):
    mock_tools.check_availability.return_value = ToolResult.ok(
        {
            "available": True,
            "doctor_id": "DOC-001",
            "appointment_date": "2026-08-16",
            "appointment_time": "17:00:00",
            "message": "The requested slot is available.",
        }
    )

    resp = client.post(
        "/appointments/check-availability",
        json={"doctor_id": "DOC-001", "appointment_date": SUNDAY, "appointment_time": "17:00"},
    )

    assert resp.status_code == 200
    assert resp.json()["available"] is True
    mock_tools.check_availability.assert_called_once_with(
        doctor_id="DOC-001",
        appointment_date="2026-08-16",
        appointment_time="17:00:00",
        service=None,
    )


def test_check_availability_missing_field_returns_422(client, mock_tools):
    resp = client.post(
        "/appointments/check-availability",
        json={"appointment_date": SUNDAY, "appointment_time": "17:00"},  # missing doctor_id
    )
    assert resp.status_code == 422
    mock_tools.check_availability.assert_not_called()


# --- get_appointment ----------------------------------------------------------

def test_get_appointment_success(client, mock_tools):
    mock_tools.get_appointment.return_value = ToolResult.ok(
        SAMPLE_APPOINTMENT.model_dump(mode="json")
    )
    resp = client.get("/appointments/APT-001")
    assert resp.status_code == 200
    assert resp.json()["appointment_id"] == "APT-001"
    mock_tools.get_appointment.assert_called_once_with("APT-001")


def test_get_appointment_not_found_returns_404_with_error_envelope(client, mock_tools):
    mock_tools.get_appointment.return_value = ToolResult.fail(
        "APPOINTMENT_NOT_FOUND", "Appointment not found."
    )
    resp = client.get("/appointments/APT-999", headers={"X-Request-ID": "REQ-TEST-1"})
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "APPOINTMENT_NOT_FOUND"
    assert body["error"]["message"] == "Appointment not found."
    assert body["error"]["request_id"] == "REQ-TEST-1"
    assert resp.headers["x-request-id"] == "REQ-TEST-1"


# --- create_appointment ------------------------------------------------------

def test_create_appointment_success(client, mock_tools):
    mock_tools.create_appointment.return_value = ToolResult.ok(
        SAMPLE_APPOINTMENT.model_dump(mode="json")
    )

    resp = client.post(
        "/appointments",
        json={
            "patient_name": "Demo Patient",
            "patient_phone": "03000000000",
            "doctor_id": "DOC-001",
            "doctor_name": "Dr. Ahmed",
            "service": "General Consultation",
            "appointment_date": SUNDAY,
            "appointment_time": "17:00",
        },
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "Pending"
    mock_tools.create_appointment.assert_called_once()
    _, kwargs = mock_tools.create_appointment.call_args
    assert kwargs["patient_name"] == "Demo Patient"
    assert kwargs["appointment_date"] == "2026-08-16"


def test_create_appointment_missing_required_field_returns_422(client, mock_tools):
    resp = client.post(
        "/appointments",
        json={"patient_name": "Demo Patient"},  # missing everything else required
    )
    assert resp.status_code == 422
    mock_tools.create_appointment.assert_not_called()


def test_create_appointment_conflict_returns_409(client, mock_tools):
    mock_tools.create_appointment.return_value = ToolResult.fail(
        "SLOT_UNAVAILABLE", "The requested slot is already booked."
    )
    resp = client.post(
        "/appointments",
        json={
            "patient_name": "Demo Patient",
            "patient_phone": "03000000000",
            "doctor_id": "DOC-001",
            "doctor_name": "Dr. Ahmed",
            "service": "General Consultation",
            "appointment_date": SUNDAY,
            "appointment_time": "17:00",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SLOT_UNAVAILABLE"


# --- update_appointment --------------------------------------------------------

def test_update_appointment_success(client, mock_tools):
    updated = SAMPLE_APPOINTMENT.model_copy(update={"notes": "Updated"})
    mock_tools.update_appointment.return_value = ToolResult.ok(updated.model_dump(mode="json"))

    resp = client.patch("/appointments/APT-001", json={"notes": "Updated"})

    assert resp.status_code == 200
    assert resp.json()["notes"] == "Updated"
    mock_tools.update_appointment.assert_called_once()
    _, kwargs = mock_tools.update_appointment.call_args
    assert kwargs["appointment_id"] == "APT-001"
    assert kwargs["notes"] == "Updated"
    assert kwargs["appointment_date"] is None


def test_update_appointment_invalid_state_returns_409(client, mock_tools):
    mock_tools.update_appointment.return_value = ToolResult.fail(
        "INVALID_APPOINTMENT_STATE", "Appointment status 'Cancelled' does not permit updates."
    )
    resp = client.patch("/appointments/APT-001", json={"notes": "x"})
    assert resp.status_code == 409


# --- cancel_appointment ---------------------------------------------------------

def test_cancel_appointment_success(client, mock_tools):
    cancelled = SAMPLE_APPOINTMENT.model_copy(update={"status": AppointmentStatus.CANCELLED})
    mock_tools.cancel_appointment.return_value = ToolResult.ok(cancelled.model_dump(mode="json"))

    resp = client.post("/appointments/APT-001/cancel", json={"reason": "Patient request"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "Cancelled"
    mock_tools.cancel_appointment.assert_called_once_with(
        appointment_id="APT-001", reason="Patient request"
    )


def test_cancel_appointment_no_body_required_fields(client, mock_tools):
    cancelled = SAMPLE_APPOINTMENT.model_copy(update={"status": AppointmentStatus.CANCELLED})
    mock_tools.cancel_appointment.return_value = ToolResult.ok(cancelled.model_dump(mode="json"))
    resp = client.post("/appointments/APT-001/cancel", json={})
    assert resp.status_code == 200


# --- approve_appointment (staff) ----------------------------------------------------

def test_approve_appointment_success(client, mock_tools):
    approved = SAMPLE_APPOINTMENT.model_copy(update={"status": AppointmentStatus.CONFIRMED})
    mock_tools.approve_appointment.return_value = ToolResult.ok(approved.model_dump(mode="json"))

    resp = client.post(
        "/staff/appointments/APT-001/approve", json={"is_staff": True, "staff_id": "staff-1"}
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "Confirmed"
    mock_tools.approve_appointment.assert_called_once_with(
        appointment_id="APT-001", notes=None, is_staff=True, staff_id="staff-1"
    )


def test_approve_appointment_unauthorized_returns_403(client, mock_tools):
    mock_tools.approve_appointment.return_value = ToolResult.fail(
        "UNAUTHORIZED", "Caller lacks required permission for this action."
    )
    resp = client.post("/staff/appointments/APT-001/approve", json={})  # is_staff defaults False
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# --- reject_appointment (staff) -----------------------------------------------------

def test_reject_appointment_success(client, mock_tools):
    rejected = SAMPLE_APPOINTMENT.model_copy(update={"status": AppointmentStatus.REJECTED})
    mock_tools.reject_appointment.return_value = ToolResult.ok(rejected.model_dump(mode="json"))

    resp = client.post(
        "/staff/appointments/APT-001/reject",
        json={"reason": "Doctor unavailable", "is_staff": True},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "Rejected"


def test_reject_appointment_missing_reason_returns_422(client, mock_tools):
    resp = client.post("/staff/appointments/APT-001/reject", json={"is_staff": True})
    assert resp.status_code == 422
    mock_tools.reject_appointment.assert_not_called()


def test_reject_appointment_reason_too_short_returns_422(client, mock_tools):
    resp = client.post(
        "/staff/appointments/APT-001/reject", json={"reason": "no", "is_staff": True}
    )
    assert resp.status_code == 422
    mock_tools.reject_appointment.assert_not_called()


# --- /chat (Phase 7 — API-001, previously deferred) ---------------------------

@pytest.fixture()
def mock_supervisor():
    return MagicMock(spec=Supervisor)


@pytest.fixture()
def chat_client(mock_supervisor):
    app.dependency_overrides[get_supervisor] = lambda: mock_supervisor
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_chat_route_success(chat_client, mock_supervisor):
    mock_supervisor.handle_message.return_value = {
        "message": "Appointment APT-001 is Pending.",
        "intent": "get_appointment",
        "data": {"appointment_id": "APT-001"},
        "requires_staff_review": True,
        "request_id": "REQ-TEST-1",
    }

    resp = chat_client.post("/chat", json={"message": "What is the status of APT-001?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "get_appointment"
    assert body["requires_staff_review"] is True
    mock_supervisor.handle_message.assert_called_once_with(
        message="What is the status of APT-001?", session_id=None, patient_phone=None
    )


def test_chat_route_missing_message_returns_422(chat_client, mock_supervisor):
    resp = chat_client.post("/chat", json={})
    assert resp.status_code == 422
    mock_supervisor.handle_message.assert_not_called()


# --- Integration tests: real tool/service/repository stack, temp workbook copy ------

@pytest.fixture()
def excel_copy(tmp_path) -> Path:
    dest = tmp_path / "test_workbook.xlsx"
    shutil.copy(ORIGINAL_TEMPLATE, dest)
    return dest


@pytest.fixture()
def real_client(excel_copy):
    service = AppointmentService(
        appointment_repo=ExcelAppointmentRepository(excel_path=excel_copy),
        doctor_repo=ExcelDoctorRepository(excel_path=excel_copy),
        availability_repo=ExcelAvailabilityRepository(excel_path=excel_copy),
        require_staff_approval=True,
    )
    real_tools = AppointmentTools(service)
    app.dependency_overrides[get_appointment_tools] = lambda: real_tools
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_integration_check_availability_against_real_workbook(real_client):
    resp = real_client.post(
        "/appointments/check-availability",
        json={"doctor_id": "DOC-001", "appointment_date": SUNDAY, "appointment_time": "16:00"},
    )
    assert resp.status_code == 200
    assert resp.json()["available"] is True


def test_integration_get_existing_appointment_from_real_workbook(real_client):
    resp = real_client.get("/appointments/APT-001")
    assert resp.status_code == 200
    assert resp.json()["patient_name"] == "Demo Patient"


def test_integration_create_then_get_round_trip(real_client):
    create_resp = real_client.post(
        "/appointments",
        json={
            "patient_name": "Integration Patient",
            "patient_phone": "03005556666",
            "doctor_id": "DOC-002",
            "doctor_name": "Dr. Sara",
            "service": "Dermatology Consultation",
            "appointment_date": SUNDAY,
            "appointment_time": "17:30",
        },
    )
    assert create_resp.status_code == 200
    new_id = create_resp.json()["appointment_id"]

    get_resp = real_client.get(f"/appointments/{new_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["patient_name"] == "Integration Patient"


def test_integration_original_template_untouched(real_client):
    original_bytes_before = ORIGINAL_TEMPLATE.read_bytes()
    real_client.post(
        "/appointments",
        json={
            "patient_name": "Safety Check",
            "patient_phone": "0000000000",
            "doctor_id": "DOC-002",
            "doctor_name": "Dr. Sara",
            "service": "Dermatology Consultation",
            "appointment_date": SUNDAY,
            "appointment_time": "18:00",
        },
    )
    assert ORIGINAL_TEMPLATE.read_bytes() == original_bytes_before
