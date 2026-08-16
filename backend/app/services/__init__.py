"""Deterministic business-logic layer.

Implements the Appointment Service Design Specification v1.0. This
package is the single business-rule boundary shared by future FastAPI
routes and Agent Tools (Phase 5/6) — neither of those layers should
duplicate the rules implemented here.

This package must NEVER import openpyxl/pandas or touch the Excel
workbook directly; all persistence goes through the repository
interfaces from app.repositories.interfaces.

Module layout (per Service Design §28 / Implementation Guide §12):
    appointment_service.py — AppointmentService
    exceptions.py            — deterministic service error model (§22)
"""
