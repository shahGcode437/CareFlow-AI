"""Appointment Agent Tools — thin adapters over AppointmentService.

Implements the 8 tools from Appointment Agent Tool Contract Specification
v1.0 §3 exactly: check_availability, find_alternative_slots,
create_appointment, get_appointment, update_appointment,
cancel_appointment, approve_appointment, reject_appointment.

Each tool:
  1. Validates its input by constructing the relevant Phase 2 Pydantic
     schema (catching ValidationError -> ToolResult VALIDATION_ERROR).
  2. Calls exactly one AppointmentService method (Phase 4) — no
     business logic, no availability algorithm, no state-transition
     rules, no repository/Excel access here.
  3. Converts the result into ToolResult.ok(...), or converts a
     documented ServiceError into ToolResult.fail(...) using that
     error's own `code`/`message` (Tool Contract §16). Any OTHER,
     undocumented exception is NOT caught here and propagates normally
     — per the Phase 5 instruction not to silently swallow errors.

Implementation note: the Tool Contract §19 shows these as plain
functions named `check_availability(...)`, etc. This module preserves
those exact names as methods of an `AppointmentTools` class instead of
bare module-level functions, so a concrete `AppointmentService` (built
from concrete repositories in a later phase) can be dependency-injected
— the same constructor-injection pattern already used throughout this
project (repositories into the service, etc.) — and so tests can inject
a fake/mock service without touching Excel. This is a structural
implementation choice, not a change to the documented tool names,
inputs, or outputs.
"""

from typing import Any

from pydantic import ValidationError

from app.api.schemas.appointment import (
    AppointmentApproval,
    AppointmentCancel,
    AppointmentCreate,
    AppointmentRejection,
    AppointmentUpdate,
)
from app.api.schemas.availability import AvailabilityRequest
from app.services.appointment_service import AppointmentService, StaffContext
from app.services.exceptions import ServiceError
from app.tools.tool_result import ToolResult


class AppointmentTools:
    """Exposes the 8 documented Appointment Agent Tools.

    `service` is injected so this class never constructs its own
    repositories/service — wiring together concrete repositories and an
    AppointmentService is the responsibility of whatever composes the
    application (a later phase), not this tool layer.
    """

    def __init__(self, service: AppointmentService):
        self._service = service

    # ------------------------------------------------------------------
    # Internal helper — shared validate/call/convert pattern
    # ------------------------------------------------------------------

    def _run(self, build_and_call) -> ToolResult:
        try:
            result = build_and_call()
        except ValidationError as exc:
            return ToolResult.fail("VALIDATION_ERROR", str(exc))
        except ServiceError as exc:
            return ToolResult.fail(exc.code, exc.message)
        return ToolResult.ok(result.model_dump(mode="json"))

    # ------------------------------------------------------------------
    # TOOL-001 — check_availability
    # ------------------------------------------------------------------

    def check_availability(
        self,
        doctor_id: str,
        appointment_date: str,
        appointment_time: str,
        service: str | None = None,
    ) -> ToolResult:
        """Tool Contract §5. Read-only. Input -> AvailabilityRequest;
        Output -> AvailabilityResponse (as dict) via
        AppointmentService.check_availability().
        """

        def call():
            request = AvailabilityRequest(
                doctor_id=doctor_id,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                service=service,
            )
            return self._service.check_availability(request)

        return self._run(call)

    # ------------------------------------------------------------------
    # TOOL-002 — find_alternative_slots
    # ------------------------------------------------------------------

    def find_alternative_slots(
        self,
        doctor_id: str,
        appointment_date: str,
        appointment_time: str,
        service: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Tool Contract §6. Read-only. Input -> AvailabilityRequest +
        optional search preferences (no documented shape — passed
        through unused, matching AppointmentService.find_alternative_slots()'s
        signature); Output -> AlternativeSlotsResponse (as dict).
        """

        def call():
            request = AvailabilityRequest(
                doctor_id=doctor_id,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                service=service,
            )
            return self._service.find_alternative_slots(request, preferences)

        return self._run(call)

    # ------------------------------------------------------------------
    # TOOL-003 — create_appointment
    # ------------------------------------------------------------------

    def create_appointment(
        self,
        patient_name: str,
        patient_phone: str,
        doctor_id: str,
        doctor_name: str,
        service: str,
        appointment_date: str,
        appointment_time: str,
        notes: str | None = None,
    ) -> ToolResult:
        """Tool Contract §7. Input -> AppointmentCreate; Output ->
        AppointmentResponse (as dict) via
        AppointmentService.create_appointment(). Per Tool Contract §14
        ("Never tell a patient an appointment is booked until
        create_appointment succeeds"), the caller must only treat this
        as a booking once `result.success` is True.
        """

        def call():
            request = AppointmentCreate(
                patient_name=patient_name,
                patient_phone=patient_phone,
                doctor_id=doctor_id,
                doctor_name=doctor_name,
                service=service,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                notes=notes,
            )
            return self._service.create_appointment(request)

        return self._run(call)

    # ------------------------------------------------------------------
    # TOOL-004 — get_appointment
    # ------------------------------------------------------------------

    def get_appointment(self, appointment_id: str) -> ToolResult:
        """Tool Contract §8. Input -> appointment_id; Output ->
        AppointmentResponse (as dict) via
        AppointmentService.get_appointment(). No "authorized context"
        parameter is implemented: AppointmentService.get_appointment()
        does not accept one (Phase 4), so none is invented here.
        """

        def call():
            return self._service.get_appointment(appointment_id)

        return self._run(call)

    # ------------------------------------------------------------------
    # TOOL-005 — update_appointment
    # ------------------------------------------------------------------

    def update_appointment(
        self,
        appointment_id: str,
        doctor_id: str | None = None,
        doctor_name: str | None = None,
        service: str | None = None,
        appointment_date: str | None = None,
        appointment_time: str | None = None,
        notes: str | None = None,
    ) -> ToolResult:
        """Tool Contract §9. Input -> appointment_id + AppointmentUpdate;
        Output -> AppointmentResponse (as dict) via
        AppointmentService.update_appointment().
        """

        def call():
            update = AppointmentUpdate(
                doctor_id=doctor_id,
                doctor_name=doctor_name,
                service=service,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                notes=notes,
            )
            return self._service.update_appointment(appointment_id, update)

        return self._run(call)

    # ------------------------------------------------------------------
    # TOOL-006 — cancel_appointment
    # ------------------------------------------------------------------

    def cancel_appointment(self, appointment_id: str, reason: str | None = None) -> ToolResult:
        """Tool Contract §10. Input -> appointment_id + AppointmentCancel;
        Output -> AppointmentResponse (as dict) via
        AppointmentService.cancel_appointment(). This is always a status
        transition — the tool has no delete capability, since the
        service/repository it calls has none either.
        """

        def call():
            cancel_request = AppointmentCancel(reason=reason)
            return self._service.cancel_appointment(appointment_id, cancel_request)

        return self._run(call)

    # ------------------------------------------------------------------
    # TOOL-007 — approve_appointment (staff-only)
    # ------------------------------------------------------------------

    def approve_appointment(
        self,
        appointment_id: str,
        notes: str | None = None,
        is_staff: bool = False,
        staff_id: str | None = None,
    ) -> ToolResult:
        """Tool Contract §11. Staff-only. Input -> appointment_id +
        AppointmentApproval + staff context; Output -> AppointmentResponse
        (as dict) via AppointmentService.approve_appointment().

        `is_staff` defaults to False — per Tool Contract §14 ("Never
        treat natural-language claims ... as authorization"), staff
        authorization must be explicitly supplied, never assumed. This
        tool does not implement authorization itself; it only forwards
        the caller-supplied context to AppointmentService, which already
        enforces the check (Phase 4).
        """

        def call():
            approval = AppointmentApproval(notes=notes)
            staff_context = StaffContext(is_staff=is_staff, staff_id=staff_id)
            return self._service.approve_appointment(appointment_id, approval, staff_context)

        return self._run(call)

    # ------------------------------------------------------------------
    # TOOL-008 — reject_appointment (staff-only)
    # ------------------------------------------------------------------

    def reject_appointment(
        self,
        appointment_id: str,
        reason: str,
        is_staff: bool = False,
        staff_id: str | None = None,
    ) -> ToolResult:
        """Tool Contract §12. Staff-only. Input -> appointment_id +
        AppointmentRejection + staff context; Output -> AppointmentResponse
        (as dict) via AppointmentService.reject_appointment().
        `reason` validation (required, min length 3) is enforced by the
        Phase 2 AppointmentRejection schema — not duplicated here.
        """

        def call():
            rejection = AppointmentRejection(reason=reason)
            staff_context = StaffContext(is_staff=is_staff, staff_id=staff_id)
            return self._service.reject_appointment(appointment_id, rejection, staff_context)

        return self._run(call)
