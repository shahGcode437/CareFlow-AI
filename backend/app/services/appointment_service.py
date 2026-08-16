"""AppointmentService — deterministic business-rule layer.

Implements Appointment Service Design Specification v1.0 §4-15 exactly:
check_availability, find_alternative_slots, create_appointment,
get_appointment, update_appointment, cancel_appointment,
approve_appointment, reject_appointment.

This module contains NO Excel/openpyxl/pandas access — persistence goes
exclusively through the repository interfaces injected into the
constructor (app.repositories.interfaces).

THREE FLAGGED, UNRESOLVED SPECIFICATION GAPS (see Phase 4 report for
full detail — summarized here at the point where each matters):

  1. Staff-approval policy (Config sheet `require_staff_approval`) has
     no approved access path (no ConfigRepository is documented, and
     this Service must not touch Excel directly). Exposed as an
     explicit constructor parameter (`require_staff_approval`) instead
     of being silently wired to the workbook.

  2. Audit_Log field mapping remains genuinely conflicting across specs
     (Service Design §21 vs. the real Excel columns; no Pydantic model
     defined). Every documented "create audit event" step in this file
     is a deliberate no-op, not a silent omission.

  3. AppointmentRepository (Service Design §17) has no method to
     enumerate existing appointments, so a sequential "APT-001"-style
     ID cannot be generated without adding an unapproved repository
     method. IDs are generated as "APT-" + a random unique suffix
     instead. See _generate_appointment_id().
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import NamedTuple

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
from app.repositories.interfaces import (
    AppointmentRepository,
    AvailabilityRepository,
    DoctorRepository,
)
from app.services.exceptions import (
    AppointmentNotFound,
    DoctorInactive,
    DoctorNotFound,
    InvalidAppointmentState,
    InvalidSlotTime,
    OutsideAvailability,
    SlotUnavailable,
    UnauthorizedAction,
)

# Service Design §6: these statuses have "No standard mutation in MVP" —
# used to gate update/cancel eligibility.
_LOCKED_STATES = {
    AppointmentStatus.REJECTED,
    AppointmentStatus.CANCELLED,
    AppointmentStatus.COMPLETED,
    AppointmentStatus.NOSHOW,
}

_REASON_CODE_TO_EXCEPTION = {
    "DOCTOR_NOT_FOUND": DoctorNotFound,
    "DOCTOR_INACTIVE": DoctorInactive,
    "OUTSIDE_AVAILABILITY": OutsideAvailability,
    "INVALID_SLOT_TIME": InvalidSlotTime,
    "SLOT_UNAVAILABLE": SlotUnavailable,
}


class _AvailabilityOutcome(NamedTuple):
    available: bool
    reason_code: str | None
    message: str


@dataclass
class StaffContext:
    """Placeholder staff-authorization context.

    Flagged Phase 4 decision: no specification defines an actual
    authentication/authorization mechanism — it is explicitly listed as
    an open decision everywhere staff actions are discussed, and
    authentication is out of Phase 4 scope. This is the minimal
    mechanical placeholder needed to satisfy Service Design §14/§15
    step 1 ("Verify staff authorization context") without building a
    real auth system.
    """

    is_staff: bool
    staff_id: str | None = None


class AppointmentService:
    """Implements the eight service methods from Service Design §4."""

    def __init__(
        self,
        appointment_repo: AppointmentRepository,
        doctor_repo: DoctorRepository,
        availability_repo: AvailabilityRepository,
        require_staff_approval: bool = True,
        max_alternative_slots: int = 3,
    ):
        self._appointments = appointment_repo
        self._doctors = doctor_repo
        self._availability = availability_repo
        # Flagged gap #1 (see module docstring): the authoritative
        # source for this is the workbook's Config sheet, but no
        # approved access path exists. Exposed as an explicit dependency.
        self.require_staff_approval = require_staff_approval
        # Service Design §10 explicitly calls the maximum alternatives
        # count an open decision that must be configurable, not
        # hard-coded — hence a constructor parameter.
        self.max_alternative_slots = max_alternative_slots

    # ------------------------------------------------------------------
    # Internal helpers (not part of the documented public interface)
    # ------------------------------------------------------------------

    def _generate_appointment_id(self) -> str:
        """See flagged gap #3 in the module docstring."""
        return f"APT-{uuid.uuid4().hex[:8]}"

    def _active_availability_windows(self, doctor_id: str, day_name: str):
        return [row for row in self._availability.get_for_day(doctor_id, day_name) if row.active]

    def _generate_slot_times(self, windows) -> list[time]:
        """Valid slot start times across all active windows (Service
        Design §9): a slot is valid only if its full duration fits
        before the window's end_time.
        """
        anchor = date.min
        slots: list[time] = []
        for window in windows:
            start_dt = datetime.combine(anchor, window.start_time)
            end_dt = datetime.combine(anchor, window.end_time)
            step = timedelta(minutes=window.slot_duration_minutes)
            current = start_dt
            while current + step <= end_dt:
                slots.append(current.time())
                current += step
        return slots

    def _evaluate_slot(
        self,
        doctor_id: str,
        target_date: date,
        target_time: time,
        exclude_appointment_id: str | None = None,
    ) -> _AvailabilityOutcome:
        """Single source of truth for the availability decision
        algorithm (Service Design §7-8). Never raises; used both by
        check_availability (must always return a response) and, via
        _require_available(), by the mutating methods.
        """
        doctor = self._doctors.get_by_id(doctor_id)
        if doctor is None:
            return _AvailabilityOutcome(False, "DOCTOR_NOT_FOUND", "Doctor not found.")
        if not doctor.active:
            return _AvailabilityOutcome(
                False, "DOCTOR_INACTIVE", "Doctor is not currently active."
            )

        day_name = target_date.strftime("%A")
        windows = self._active_availability_windows(doctor_id, day_name)
        if not windows:
            return _AvailabilityOutcome(
                False,
                "OUTSIDE_AVAILABILITY",
                "No availability configured for the requested day.",
            )

        in_hours = any(w.start_time <= target_time < w.end_time for w in windows)
        if not in_hours:
            return _AvailabilityOutcome(
                False,
                "OUTSIDE_AVAILABILITY",
                "Requested time is outside the doctor's available hours.",
            )

        valid_slots = set(self._generate_slot_times(windows))
        if target_time not in valid_slots:
            return _AvailabilityOutcome(
                False,
                "INVALID_SLOT_TIME",
                "Requested time does not align with the doctor's slot schedule.",
            )

        if self._appointments.exists_conflict(
            doctor_id, target_date, target_time, exclude_appointment_id
        ):
            return _AvailabilityOutcome(
                False, "SLOT_UNAVAILABLE", "The requested slot is already booked."
            )

        return _AvailabilityOutcome(True, None, "The requested slot is available.")

    def _require_available(
        self,
        doctor_id: str,
        target_date: date,
        target_time: time,
        exclude_appointment_id: str | None = None,
    ) -> None:
        """Same evaluation as _evaluate_slot but raises the matching
        ServiceError on failure. Used immediately before every write,
        per Service Design's "an earlier availability check is
        advisory" instruction.
        """
        outcome = self._evaluate_slot(doctor_id, target_date, target_time, exclude_appointment_id)
        if not outcome.available:
            raise _REASON_CODE_TO_EXCEPTION[outcome.reason_code](outcome.message)

    def _resolve_doctor(self, doctor_id: str):
        """Fetch and validate an active doctor, raising on failure."""
        doctor = self._doctors.get_by_id(doctor_id)
        if doctor is None:
            raise DoctorNotFound()
        if not doctor.active:
            raise DoctorInactive()
        return doctor

    # ------------------------------------------------------------------
    # Documented service methods (Service Design §4)
    # ------------------------------------------------------------------

    def check_availability(self, request: AvailabilityRequest) -> AvailabilityResponse:
        """Service Design §7-8. Read-only; unavailability is reported
        IN the response (never raised), per the documented
        AvailabilityResponse contract.
        """
        outcome = self._evaluate_slot(
            request.doctor_id, request.appointment_date, request.appointment_time
        )
        return AvailabilityResponse(
            available=outcome.available,
            doctor_id=request.doctor_id,
            appointment_date=request.appointment_date,
            appointment_time=request.appointment_time,
            message=outcome.message,
        )

    def find_alternative_slots(
        self, request: AvailabilityRequest, preferences: dict | None = None
    ) -> AlternativeSlotsResponse:
        """Service Design §10.

        `preferences` matches the documented signature shape (Service
        Design §4 / Tool Contract §6) but is unused: no specification
        defines its structure.

        Date-expansion to nearby dates is NOT implemented — Service
        Design §10 explicitly calls the search horizon an open decision
        rather than a hard-coded assumption. This searches the
        requested date only.
        """
        requested_outcome = self._evaluate_slot(
            request.doctor_id, request.appointment_date, request.appointment_time
        )

        doctor = self._doctors.get_by_id(request.doctor_id)
        alternatives: list[AlternativeSlot] = []
        if doctor is not None and doctor.active:
            day_name = request.appointment_date.strftime("%A")
            windows = self._active_availability_windows(request.doctor_id, day_name)
            candidate_times = sorted(set(self._generate_slot_times(windows)))

            requested_dt = datetime.combine(date.min, request.appointment_time)
            scored: list[tuple[float, time]] = []
            for candidate in candidate_times:
                if candidate == request.appointment_time:
                    continue  # not an "alternative" to itself
                if self._appointments.exists_conflict(
                    request.doctor_id, request.appointment_date, candidate
                ):
                    continue
                distance = abs(
                    (datetime.combine(date.min, candidate) - requested_dt).total_seconds()
                )
                scored.append((distance, candidate))

            scored.sort(key=lambda pair: pair[0])
            for _, candidate in scored[: self.max_alternative_slots]:
                alternatives.append(
                    AlternativeSlot(
                        doctor_id=request.doctor_id,
                        doctor_name=doctor.doctor_name,
                        appointment_date=request.appointment_date,
                        appointment_time=candidate,
                    )
                )

        return AlternativeSlotsResponse(
            requested_slot_available=requested_outcome.available,
            alternatives=alternatives,
        )

    def create_appointment(self, request: AppointmentCreate) -> AppointmentResponse:
        """Service Design §11.

        Audit event creation (documented step 7) is deliberately a
        no-op — see flagged gap #2 in the module docstring.

        doctor_name is always resolved from DoctorRepository rather
        than trusting the client-supplied value, per Pydantic Schema
        Spec §13 ("doctor_name ... No preferred direct authority /
        Resolved, validated").
        """
        doctor = self._resolve_doctor(request.doctor_id)

        # Re-check availability immediately before write (step 2).
        self._require_available(
            request.doctor_id, request.appointment_date, request.appointment_time
        )

        now = datetime.now()
        initial_status = (
            AppointmentStatus.PENDING
            if self.require_staff_approval
            else AppointmentStatus.CONFIRMED
        )

        appointment = AppointmentResponse(
            appointment_id=self._generate_appointment_id(),
            patient_name=request.patient_name,
            patient_phone=request.patient_phone,
            doctor_id=request.doctor_id,
            doctor_name=doctor.doctor_name,
            service=request.service,
            appointment_date=request.appointment_date,
            appointment_time=request.appointment_time,
            status=initial_status,
            created_at=now,
            updated_at=now,
            notes=request.notes,
        )
        return self._appointments.create(appointment)

    def get_appointment(self, appointment_id: str) -> AppointmentResponse:
        """Service Design §4. Raises AppointmentNotFound if missing."""
        appointment = self._appointments.get_by_id(appointment_id)
        if appointment is None:
            raise AppointmentNotFound()
        return appointment

    def update_appointment(
        self, appointment_id: str, update: AppointmentUpdate
    ) -> AppointmentResponse:
        """Service Design §12.

        Only fields present on AppointmentUpdate may change —
        appointment_id/status/created_at/updated_at are not exposed by
        that schema at all, so they cannot be modified through this
        method. Disallowed entirely when the current status is one
        Service Design §6 marks "No standard mutation in MVP"
        (Rejected, Cancelled, Completed, NoShow).

        Audit event creation (documented step 10) is deliberately a
        no-op — see flagged gap #2 in the module docstring.
        """
        existing = self._appointments.get_by_id(appointment_id)
        if existing is None:
            raise AppointmentNotFound()

        if existing.status in _LOCKED_STATES:
            raise InvalidAppointmentState(
                f"Appointment status '{existing.status.value}' does not permit updates."
            )

        effective_doctor_id = (
            update.doctor_id if update.doctor_id is not None else existing.doctor_id
        )
        effective_date = (
            update.appointment_date
            if update.appointment_date is not None
            else existing.appointment_date
        )
        effective_time = (
            update.appointment_time
            if update.appointment_time is not None
            else existing.appointment_time
        )
        effective_service = update.service if update.service is not None else existing.service

        scheduling_changed = (
            effective_doctor_id != existing.doctor_id
            or effective_date != existing.appointment_date
            or effective_time != existing.appointment_time
        )

        doctor_name = existing.doctor_name
        if scheduling_changed:
            doctor = self._resolve_doctor(effective_doctor_id)
            doctor_name = doctor.doctor_name
            self._require_available(
                effective_doctor_id,
                effective_date,
                effective_time,
                exclude_appointment_id=appointment_id,
            )

        updated = existing.model_copy(
            update={
                "doctor_id": effective_doctor_id,
                "doctor_name": doctor_name,
                "service": effective_service,
                "appointment_date": effective_date,
                "appointment_time": effective_time,
                "notes": update.notes if update.notes is not None else existing.notes,
                "updated_at": datetime.now(),
            }
        )
        return self._appointments.update(updated)

    def cancel_appointment(
        self, appointment_id: str, cancel_request: AppointmentCancel
    ) -> AppointmentResponse:
        """Service Design §13. Status transition only — the row is
        never deleted (AppointmentRepository has no delete method at
        all). Allowed only from Pending/Confirmed, per the transitions
        explicitly listed in Service Design §6.

        Audit event creation (documented step 6) is deliberately a
        no-op — see flagged gap #2 in the module docstring.
        `cancel_request.reason` is accepted per the documented schema
        but, with audit logging out of scope this phase, has nowhere
        approved to be persisted.
        """
        existing = self._appointments.get_by_id(appointment_id)
        if existing is None:
            raise AppointmentNotFound()

        if existing.status not in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED):
            raise InvalidAppointmentState(
                f"Appointment status '{existing.status.value}' cannot be cancelled."
            )

        updated = existing.model_copy(
            update={"status": AppointmentStatus.CANCELLED, "updated_at": datetime.now()}
        )
        return self._appointments.update(updated)

    def approve_appointment(
        self,
        appointment_id: str,
        approval: AppointmentApproval,
        staff_context: StaffContext,
    ) -> AppointmentResponse:
        """Service Design §14. Staff-only (see StaffContext docstring
        for the flagged authorization placeholder). Only Pending ->
        Confirmed is a documented transition for this operation.

        Audit event creation (documented step 8) is deliberately a
        no-op — see flagged gap #2 in the module docstring.
        """
        if not staff_context.is_staff:
            raise UnauthorizedAction()

        existing = self._appointments.get_by_id(appointment_id)
        if existing is None:
            raise AppointmentNotFound()

        if existing.status != AppointmentStatus.PENDING:
            raise InvalidAppointmentState(
                f"Appointment status '{existing.status.value}' cannot be approved."
            )

        # Step 4: re-check any critical booking conflict before
        # confirmation. Excludes itself — a Pending appointment already
        # occupies this exact slot in the workbook.
        self._require_available(
            existing.doctor_id,
            existing.appointment_date,
            existing.appointment_time,
            exclude_appointment_id=appointment_id,
        )

        updated = existing.model_copy(
            update={"status": AppointmentStatus.CONFIRMED, "updated_at": datetime.now()}
        )
        return self._appointments.update(updated)

    def reject_appointment(
        self,
        appointment_id: str,
        rejection: AppointmentRejection,
        staff_context: StaffContext,
    ) -> AppointmentResponse:
        """Service Design §15. Staff-only. Only Pending -> Rejected is a
        documented transition. `rejection.reason` is required and
        length-validated by the Pydantic schema already (min 3 chars),
        so no duplicate validation is performed here.

        Audit event creation (documented step 8) is deliberately a
        no-op — see flagged gap #2 in the module docstring. The reason
        is accepted per the schema but, with audit logging out of scope
        this phase, has nowhere approved to be persisted.
        """
        if not staff_context.is_staff:
            raise UnauthorizedAction()

        existing = self._appointments.get_by_id(appointment_id)
        if existing is None:
            raise AppointmentNotFound()

        if existing.status != AppointmentStatus.PENDING:
            raise InvalidAppointmentState(
                f"Appointment status '{existing.status.value}' cannot be rejected."
            )

        updated = existing.model_copy(
            update={"status": AppointmentStatus.REJECTED, "updated_at": datetime.now()}
        )
        return self._appointments.update(updated)
