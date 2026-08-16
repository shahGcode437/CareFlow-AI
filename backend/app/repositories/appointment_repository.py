"""Excel-backed AppointmentRepository implementation.

Maps rows of the Appointments sheet to/from app.api.schemas.appointment.
AppointmentResponse. Column names and order were verified directly
against clinic_appointments_MVP_template.xlsx (Phase 3 inspection) and
match the Pydantic Schema & Data Contract Specification §12
Excel<->Pydantic mapping exactly:

    appointment_id, patient_name, patient_phone, doctor_id, doctor_name,
    service, appointment_date, appointment_time, status, created_at,
    updated_at, notes

No business logic (state transitions, approval rules, availability
decisions) is implemented here — only persistence and retrieval, per
the Phase 3 repository design rules.
"""

from datetime import date, time

from app.api.schemas.appointment import AppointmentResponse, AppointmentStatus
from app.core.config import get_settings
from app.repositories import _workbook_access as wa
from app.repositories._excel_types import (
    format_date,
    format_datetime,
    format_time,
    parse_date,
    parse_datetime,
    parse_time,
)
from app.repositories.interfaces import AppointmentRepository

SHEET_NAME = "Appointments"

# Service Design §8 Availability Rules table states explicitly:
# "Cancelled appointment at slot -> Does not block slot." No other
# status is explicitly declared non-blocking anywhere in the approved
# specifications. This repository therefore treats exactly that one,
# directly-stated exception as non-blocking, and every other documented
# status (Pending, Confirmed, Rejected, Completed, NoShow) as blocking.
# This is a literal application of the one rule that IS spelled out, not
# an invented rule — but it has not been independently confirmed for
# Rejected/Completed/NoShow, and should be revisited when the
# Appointment Service (Phase 4) is built on top of this method.
NON_BLOCKING_STATUSES = {AppointmentStatus.CANCELLED}


def _row_to_response(row: dict) -> AppointmentResponse:
    return AppointmentResponse(
        appointment_id=row["appointment_id"],
        patient_name=row["patient_name"],
        patient_phone=row["patient_phone"],
        doctor_id=row["doctor_id"],
        doctor_name=row["doctor_name"],
        service=row["service"],
        appointment_date=parse_date(row["appointment_date"]),
        appointment_time=parse_time(row["appointment_time"]),
        status=AppointmentStatus(row["status"]),
        created_at=parse_datetime(row["created_at"]),
        updated_at=parse_datetime(row["updated_at"]),
        notes=row.get("notes"),
    )


def _response_to_row(appointment: AppointmentResponse) -> dict:
    return {
        "appointment_id": appointment.appointment_id,
        "patient_name": appointment.patient_name,
        "patient_phone": appointment.patient_phone,
        "doctor_id": appointment.doctor_id,
        "doctor_name": appointment.doctor_name,
        "service": appointment.service,
        "appointment_date": format_date(appointment.appointment_date),
        "appointment_time": format_time(appointment.appointment_time),
        "status": appointment.status.value,
        "created_at": format_datetime(appointment.created_at),
        "updated_at": format_datetime(appointment.updated_at),
        "notes": appointment.notes,
    }


class ExcelAppointmentRepository(AppointmentRepository):
    """Excel-backed implementation of AppointmentRepository.

    Accepts an explicit `excel_path` so tests can point it at an
    isolated temporary copy of the workbook (never the original
    template). Defaults to the configured application workbook path.
    """

    def __init__(self, excel_path=None):
        self._path = excel_path or get_settings().resolved_excel_file_path

    def get_by_id(self, appointment_id: str) -> AppointmentResponse | None:
        for row in wa.read_rows(self._path, SHEET_NAME):
            if row.get("appointment_id") == appointment_id:
                return _row_to_response(row)
        return None

    def list_by_doctor_and_date(
        self, doctor_id: str, target_date: date
    ) -> list[AppointmentResponse]:
        target_str = format_date(target_date)
        results = []
        for row in wa.read_rows(self._path, SHEET_NAME):
            if row.get("doctor_id") == doctor_id and row.get("appointment_date") == target_str:
                results.append(_row_to_response(row))
        return results

    def create(self, appointment: AppointmentResponse) -> AppointmentResponse:
        row = _response_to_row(appointment)
        with wa.WRITE_LOCK:
            wa.append_row(self._path, SHEET_NAME, row)
        return appointment

    def update(self, appointment: AppointmentResponse) -> AppointmentResponse:
        row = _response_to_row(appointment)
        with wa.WRITE_LOCK:
            found = wa.update_row_by_key(
                self._path, SHEET_NAME, "appointment_id", appointment.appointment_id, row
            )
        if not found:
            raise ValueError(
                f"Cannot update: appointment_id '{appointment.appointment_id}' not found."
            )
        return appointment

    def exists_conflict(
        self,
        doctor_id: str,
        target_date: date,
        target_time: time,
        exclude_appointment_id: str | None = None,
    ) -> bool:
        target_date_str = format_date(target_date)
        target_time_str = format_time(target_time)
        for row in wa.read_rows(self._path, SHEET_NAME):
            if row.get("doctor_id") != doctor_id:
                continue
            if row.get("appointment_date") != target_date_str:
                continue
            if row.get("appointment_time") != target_time_str:
                continue
            if exclude_appointment_id and row.get("appointment_id") == exclude_appointment_id:
                continue
            if AppointmentStatus(row["status"]) in NON_BLOCKING_STATUSES:
                continue
            return True
        return False
