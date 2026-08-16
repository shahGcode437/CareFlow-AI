"""Deterministic service-level exceptions.

Implements the error model from Appointment Service Design Specification
v1.0 §22 ("Service Error Model"), with error `code` strings cross-checked
against Appointment Agent Tool Contract Specification v1.0 §16 ("Tool
Error Contract") where both documents describe the same failure —the two
tables agree on every code they share. `INVALID_SLOT_TIME` appears only
in the Service Design's §8 Availability Rules table; it is included here
for completeness since that table explicitly names it.

`http_status` mirrors the API mapping from Service Design §22 for a
future FastAPI layer (Phase 6) to translate these into HTTP responses.
That translation is NOT implemented here — out of Phase 4 scope.
"""


class ServiceError(Exception):
    """Base class for all deterministic business-rule failures."""

    code: str = "SERVICE_ERROR"
    http_status: int = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(f"[{self.code}] {message}")


class DoctorNotFound(ServiceError):
    code = "DOCTOR_NOT_FOUND"
    http_status = 404

    def __init__(self, message: str = "Doctor not found."):
        super().__init__(message)


class DoctorInactive(ServiceError):
    code = "DOCTOR_INACTIVE"
    http_status = 409

    def __init__(self, message: str = "Doctor is not currently active."):
        super().__init__(message)


class OutsideAvailability(ServiceError):
    code = "OUTSIDE_AVAILABILITY"
    http_status = 409

    def __init__(self, message: str = "Requested time is outside the doctor's available hours."):
        super().__init__(message)


class InvalidSlotTime(ServiceError):
    code = "INVALID_SLOT_TIME"
    http_status = 409

    def __init__(
        self,
        message: str = "Requested time does not align with the doctor's slot schedule.",
    ):
        super().__init__(message)


class SlotUnavailable(ServiceError):
    code = "SLOT_UNAVAILABLE"
    http_status = 409

    def __init__(self, message: str = "The requested slot is already booked."):
        super().__init__(message)


class AppointmentNotFound(ServiceError):
    code = "APPOINTMENT_NOT_FOUND"
    http_status = 404

    def __init__(self, message: str = "Appointment not found."):
        super().__init__(message)


class InvalidAppointmentState(ServiceError):
    code = "INVALID_APPOINTMENT_STATE"
    http_status = 409

    def __init__(
        self,
        message: str = "Operation not allowed for the appointment's current state.",
    ):
        super().__init__(message)


class UnauthorizedAction(ServiceError):
    code = "UNAUTHORIZED"
    http_status = 403

    def __init__(self, message: str = "Caller lacks required permission for this action."):
        super().__init__(message)


class RepositoryFailure(ServiceError):
    code = "REPOSITORY_ERROR"
    http_status = 500

    def __init__(self, message: str = "Persistence operation failed."):
        super().__init__(message)


class ValidationFailure(ServiceError):
    code = "VALIDATION_ERROR"
    http_status = 400

    def __init__(self, message: str = "Invalid business input."):
        super().__init__(message)
