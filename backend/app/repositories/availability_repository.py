"""Excel-backed AvailabilityRepository implementation.

Maps rows of the Availability sheet to/from
app.api.schemas.doctor.DoctorAvailability. Column names verified
directly against clinic_appointments_MVP_template.xlsx:
availability_id, doctor_id, day_of_week, start_time, end_time,
slot_duration_minutes, active — matching Pydantic Schema & Data Contract
Specification §11.2 / §12 exactly. Read-only sheet for the MVP (no
create/update method is documented for AvailabilityRepository in
Service Design §17, so none is implemented here).
"""

from app.api.schemas.doctor import DoctorAvailability
from app.core.config import get_settings
from app.repositories import _workbook_access as wa
from app.repositories._excel_types import parse_time
from app.repositories.interfaces import AvailabilityRepository

SHEET_NAME = "Availability"


def _row_to_availability(row: dict) -> DoctorAvailability:
    return DoctorAvailability(
        availability_id=row["availability_id"],
        doctor_id=row["doctor_id"],
        day_of_week=row["day_of_week"],
        start_time=parse_time(row["start_time"]),
        end_time=parse_time(row["end_time"]),
        slot_duration_minutes=int(row["slot_duration_minutes"]),
        active=bool(row["active"]),
    )


class ExcelAvailabilityRepository(AvailabilityRepository):
    """Excel-backed implementation of AvailabilityRepository."""

    def __init__(self, excel_path=None):
        self._path = excel_path or get_settings().resolved_excel_file_path

    def get_for_doctor(self, doctor_id: str) -> list[DoctorAvailability]:
        return [
            _row_to_availability(row)
            for row in wa.read_rows(self._path, SHEET_NAME)
            if row.get("doctor_id") == doctor_id
        ]

    def get_for_day(self, doctor_id: str, day_of_week: str) -> list[DoctorAvailability]:
        return [
            _row_to_availability(row)
            for row in wa.read_rows(self._path, SHEET_NAME)
            if row.get("doctor_id") == doctor_id and row.get("day_of_week") == day_of_week
        ]
