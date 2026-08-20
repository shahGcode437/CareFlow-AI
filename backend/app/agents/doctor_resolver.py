"""Doctor name -> doctor_id resolution (Phase 9.6).

Patient-facing conversational boundary between natural-language doctor
references ("Dr. Ahmed", "Ahmed", "doctor Ahmed") and the stable
internal ``doctor_id`` the appointment tools/service require.

Reuses the canonical doctor identity registry already established for
RAG entity-aware retrieval (``app.rag.entity_filter.CLINIC_DOCTORS``)
rather than maintaining a second doctor list — that registry is the
single source of truth for doctor id <-> name mapping across both the
Knowledge Agent and the Appointment Agent. Nothing here duplicates or
re-derives doctor identity data.

This module does NOT determine appointment availability, booking
eligibility, or any business rule — it only maps a name to an id (or
reports that the mapping is ambiguous/unknown). The resolved
``doctor_id`` is handed to the EXISTING AppointmentTools /
AppointmentService unchanged; that layer remains the sole authority
for whether the doctor is actually bookable. A resolved id for a
demo-only doctor (DOC-003..DOC-012, not present in the Excel workbook)
correctly surfaces DOCTOR_NOT_FOUND from the service — exactly as it
would today for a literal "DOC-003" the patient might type. Nothing
here invents bookability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.rag.entity_filter import (
    CLINIC_DOCTORS,
    DoctorEntity,
    detect_doctor_entities,
    extract_dr_title_name,
)


@dataclass(frozen=True)
class DoctorNameResolution:
    """Outcome of resolving a natural-language doctor reference.

    At most one of the following is true at a time:
      * ``is_resolved``  — ``doctor_id``/``doctor_name`` are set.
      * ``is_ambiguous`` — ``ambiguous_candidates`` lists the matching
        doctor names; the caller should ask the patient to clarify.
      * ``is_unknown``   — the patient named a doctor ("Dr. <name>")
        that matches nobody in the registry.

    If none of the three are true, no doctor reference was detected in
    the message at all — the caller's existing missing-field handling
    applies unchanged.
    """

    doctor_id: str | None = None
    doctor_name: str | None = None
    ambiguous_candidates: tuple[str, ...] = ()
    unknown_name: str | None = None

    @property
    def is_resolved(self) -> bool:
        return self.doctor_id is not None

    @property
    def is_ambiguous(self) -> bool:
        return len(self.ambiguous_candidates) > 0

    @property
    def is_unknown(self) -> bool:
        return self.unknown_name is not None


def resolve_doctor_by_name(
    message: str,
    registry: Sequence[DoctorEntity] = CLINIC_DOCTORS,
) -> DoctorNameResolution:
    """Resolve a natural-language doctor reference in ``message``.

    Explicit ``DOC-XXX`` identifiers are also matched (via the shared
    ``detect_doctor_entities`` detector), so a caller that hasn't
    already extracted an explicit id can rely on this function alone.
    Callers that already extracted an explicit id (e.g.
    ``RuleBasedIntentProvider``, which checks first) should skip
    calling this — explicit ids always take priority and are never
    second-guessed by name matching.
    """
    matched_ids, is_unknown = detect_doctor_entities(message, registry=registry)

    if len(matched_ids) == 1:
        doctor_id = next(iter(matched_ids))
        doctor = next((d for d in registry if d.doctor_id == doctor_id), None)
        if doctor is not None:
            return DoctorNameResolution(doctor_id=doctor.doctor_id, doctor_name=doctor.name)
        return DoctorNameResolution()

    if len(matched_ids) > 1:
        names = tuple(sorted(d.name for d in registry if d.doctor_id in matched_ids))
        return DoctorNameResolution(ambiguous_candidates=names)

    if is_unknown:
        raw_name = extract_dr_title_name(message) or "that doctor"
        return DoctorNameResolution(unknown_name=raw_name)

    return DoctorNameResolution()


def doctor_name_for_id(
    doctor_id: str,
    registry: Sequence[DoctorEntity] = CLINIC_DOCTORS,
) -> str | None:
    """Look up a doctor's display name from a known ``doctor_id`` —
    used to backfill ``doctor_name`` when the patient typed an
    explicit id, and to phrase patient-facing responses without
    exposing the raw id unnecessarily."""
    for d in registry:
        if d.doctor_id == doctor_id:
            return d.name
    return None


__all__ = [
    "DoctorNameResolution",
    "doctor_name_for_id",
    "resolve_doctor_by_name",
]
