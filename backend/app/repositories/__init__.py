"""Repository layer — the only part of the application allowed to touch
Excel/openpyxl.

Implements the persistence boundary described in the Master Specification
(§12-13), the Appointment Service Design Specification (§16-19), and the
Claude Implementation Master Guide (Phase 3). Nothing above this package
(Service, Agents, FastAPI routes) may import openpyxl/pandas directly or
receive a worksheet/workbook object — repositories return plain domain
data (Phase 2 Pydantic schemas, or — for the flagged Audit_Log case —
plain dicts).

This package deliberately contains NO business logic: no appointment
state-transition rules, no approval/rejection rules, no availability
decision algorithm, no alternative-slot ranking. Those belong to the
Appointment Service (Phase 4).

Module layout (per Service Design §28 / Implementation Guide §11):
    interfaces.py            — abstract repository interfaces
    appointment_repository.py — ExcelAppointmentRepository
    doctor_repository.py      — ExcelDoctorRepository
    availability_repository.py — ExcelAvailabilityRepository
    audit_repository.py       — ExcelAuditRepository (partial — see its
                                 module docstring for the flagged
                                 Audit_Log specification conflict)

Two internal (underscore-prefixed) helper modules are also present:
    _excel_types.py     — string <-> date/time/datetime conversion,
                           matching the Config sheet's documented
                           date_format/time_format
    _workbook_access.py — generic, sheet-agnostic row read/append/update
                           helpers plus the shared write lock

These two are implementation details of this package, not part of the
documented repository contract, and are not imported outside it.
"""
