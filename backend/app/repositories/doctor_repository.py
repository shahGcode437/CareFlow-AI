"""Excel-backed DoctorRepository implementation.

Maps rows of the Doctors sheet to/from app.api.schemas.doctor.Doctor.
Column names verified directly against
clinic_appointments_MVP_template.xlsx: doctor_id, doctor_name,
specialty, active — matching Pydantic Schema & Data Contract
Specification §11.1 / §12 exactly. Read-only sheet for the MVP (no
create/update method is documented for DoctorRepository in Service
Design §17, so none is implemented here).
"""

from app.api.schemas.doctor import Doctor
from app.core.config import get_settings
from app.repositories import _workbook_access as wa
from app.repositories.interfaces import DoctorRepository

SHEET_NAME = "Doctors"


def _row_to_doctor(row: dict) -> Doctor:
    return Doctor(
        doctor_id=row["doctor_id"],
        doctor_name=row["doctor_name"],
        specialty=row["specialty"],
        active=bool(row["active"]),
    )


class ExcelDoctorRepository(DoctorRepository):
    """Excel-backed implementation of DoctorRepository."""

    def __init__(self, excel_path=None):
        self._path = excel_path or get_settings().resolved_excel_file_path

    def get_by_id(self, doctor_id: str) -> Doctor | None:
        for row in wa.read_rows(self._path, SHEET_NAME):
            if row.get("doctor_id") == doctor_id:
                return _row_to_doctor(row)
        return None

    def list_active(self) -> list[Doctor]:
        return [
            _row_to_doctor(row)
            for row in wa.read_rows(self._path, SHEET_NAME)
            if bool(row.get("active"))
        ]
