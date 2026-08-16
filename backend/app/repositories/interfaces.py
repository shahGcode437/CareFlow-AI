"""Abstract repository interfaces.

Method names and signatures are taken directly from the Appointment
Service Design Specification v1.0 §17 ("Proposed Repository Interface").
No additional methods are added beyond what that section documents,
per the Phase 3 instruction not to invent repository methods without
flagging them first.

Parameter/return type hints use the Phase 2 Pydantic schemas
(app.api.schemas) where the specification's data model makes the type
unambiguous. Two type-hint decisions were not spelled out verbatim by
the spec and are documented at the point of decision below:

  - AppointmentRepository.create()/update() accept and return
    AppointmentResponse. By the time the Service layer calls the
    repository (Service Design §11 "Create Appointment" steps 3-6, §12
    "Update / Reschedule" steps 7-9), it has already generated the
    appointment_id, resolved the status, and computed timestamps — so
    the repository receives/returns the fully-populated shape, not the
    partial AppointmentCreate/AppointmentUpdate input schemas.

  - AuditRepository.create() accepts `dict[str, Any]` rather than a
    Pydantic schema. See audit_repository.py's module docstring for the
    unresolved Audit_Log specification conflict this reflects.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from app.api.schemas.appointment import AppointmentResponse
from app.api.schemas.doctor import Doctor, DoctorAvailability


class AppointmentRepository(ABC):
    """Service Design §17 — AppointmentRepository."""

    @abstractmethod
    def get_by_id(self, appointment_id: str) -> AppointmentResponse | None:
        """Retrieve a single appointment by its ID, or None if not found."""

    @abstractmethod
    def list_by_doctor_and_date(
        self, doctor_id: str, target_date: date
    ) -> list[AppointmentResponse]:
        """List all appointments for a given doctor on a given date."""

    @abstractmethod
    def create(self, appointment: AppointmentResponse) -> AppointmentResponse:
        """Persist a new, fully-populated appointment record."""

    @abstractmethod
    def update(self, appointment: AppointmentResponse) -> AppointmentResponse:
        """Persist changes to an existing, fully-populated appointment record."""

    @abstractmethod
    def exists_conflict(
        self,
        doctor_id: str,
        target_date: date,
        target_time,
        exclude_appointment_id: str | None = None,
    ) -> bool:
        """Return True if a blocking appointment already occupies this
        doctor/date/time slot."""


class DoctorRepository(ABC):
    """Service Design §17 — DoctorRepository."""

    @abstractmethod
    def get_by_id(self, doctor_id: str) -> Doctor | None:
        """Retrieve a single doctor by ID, or None if not found."""

    @abstractmethod
    def list_active(self) -> list[Doctor]:
        """List all doctors currently marked active."""


class AvailabilityRepository(ABC):
    """Service Design §17 — AvailabilityRepository."""

    @abstractmethod
    def get_for_doctor(self, doctor_id: str) -> list[DoctorAvailability]:
        """List all availability rules configured for a doctor."""

    @abstractmethod
    def get_for_day(self, doctor_id: str, day_of_week: str) -> list[DoctorAvailability]:
        """List availability rules configured for a doctor on a specific day."""


class AuditRepository(ABC):
    """Service Design §17 — AuditRepository.

    See audit_repository.py for the flagged Audit_Log specification
    conflict this interface's loose typing reflects.
    """

    @abstractmethod
    def create(self, event: dict[str, Any]) -> None:
        """Persist an audit event row."""
