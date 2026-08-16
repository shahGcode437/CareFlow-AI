"""Pydantic data-contract schemas.

Implements the Pydantic Schema & Data Contract Specification v1.0 exactly.
This package defines validation/data contracts only — no Excel/pandas
access, no business rules, no repository or service logic. Those belong
to later phases per the Claude Implementation Master Guide's phase plan.

Module layout (per spec §20):
    appointment.py  — AppointmentStatus enum + Create/Update/Response/
                       Cancel/Approval/Rejection schemas
    availability.py — Availability + Alternative Slot schemas
    doctor.py        — Doctor + DoctorAvailability schemas
    common.py         — Shared/error schemas + the /chat request/response
                       contracts documented in the FastAPI API Contract
                       Specification (no dedicated module was named for
                       these in either spec's file layout, so they are
                       grouped here as shared/API-level contracts)

Note: an Audit_Log Pydantic model is intentionally NOT included in this
phase. See the Phase 2 report for the specification ambiguity that was
found and flagged instead of guessed at.
"""
