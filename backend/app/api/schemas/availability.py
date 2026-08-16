"""Availability and alternative-slot schemas.

Implements Pydantic Schema & Data Contract Specification v1.0 §7-8
exactly. No availability/conflict business logic lives here — that is
computed by the Appointment Service (Phase 4) per spec §19.
"""

from datetime import date, time

from pydantic import BaseModel


class AvailabilityRequest(BaseModel):
    """Spec §7.1 — AvailabilityRequest."""

    doctor_id: str
    appointment_date: date
    appointment_time: time
    service: str | None = None


class AvailabilityResponse(BaseModel):
    """Spec §7.2 — AvailabilityResponse."""

    available: bool
    doctor_id: str
    appointment_date: date
    appointment_time: time
    message: str


class AlternativeSlot(BaseModel):
    """Spec §8.1 — AlternativeSlot."""

    doctor_id: str
    doctor_name: str
    appointment_date: date
    appointment_time: time


class AlternativeSlotsResponse(BaseModel):
    """Spec §8.2 — AlternativeSlotsResponse."""

    requested_slot_available: bool
    alternatives: list[AlternativeSlot]
