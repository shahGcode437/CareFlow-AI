"""Doctor and doctor-availability schemas.

Implements Pydantic Schema & Data Contract Specification v1.0 §11
exactly, mapped 1:1 to the verified Doctors and Availability sheets in
clinic_appointments_MVP_template.xlsx (Phase 0 inspection).

Note: day_of_week is kept as a plain string per spec §11.2 (the spec does
not define an enum of weekday values), so no enum is invented here.
"""

from datetime import time

from pydantic import BaseModel


class Doctor(BaseModel):
    """Spec §11.1 — Doctor. Maps to Doctors sheet."""

    doctor_id: str
    doctor_name: str
    specialty: str
    active: bool


class DoctorAvailability(BaseModel):
    """Spec §11.2 — DoctorAvailability. Maps to Availability sheet."""

    availability_id: str
    doctor_id: str
    day_of_week: str
    start_time: time
    end_time: time
    slot_duration_minutes: int
    active: bool
