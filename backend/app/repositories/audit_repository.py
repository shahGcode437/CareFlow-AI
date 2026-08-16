"""Excel-backed AuditRepository implementation — PARTIAL / FLAGGED.

UNRESOLVED SPECIFICATION CONFLICT (identified Phase 2, reconfirmed
Phase 3 by direct workbook inspection):

  Appointment Service Design Specification §21 ("Audit Event Design")
  describes an audit event conceptually as:
      audit_id, timestamp, actor_type, actor_id, action,
      appointment_id, summary, metadata

  The ACTUAL clinic_appointments_MVP_template.xlsx Audit_Log sheet
  (verified directly, Phase 3) has these columns instead:
      event_id, appointment_id, action, actor_type, actor_id,
      timestamp, old_status, new_status, reason

  The Pydantic Schema & Data Contract Specification v1.0 defines NO
  Audit Pydantic model at all — its §12 Excel<->Pydantic mapping table
  covers Appointments, Doctors, and Availability only.

DECISION MADE HERE (deliberately minimal, does not resolve the conflict):
  Service Design §17 documents exactly one AuditRepository method:
  `create(event)`. That method's job is purely mechanical (append a
  row) so it is implemented here — but ONLY using the real, verified
  Excel column names as the accepted dict keys. No AuditEvent/
  AuditCreate Pydantic schema is defined, and the business-level
  question of which fields a caller should populate (e.g. does
  `create_appointment` write `reason`? does `approve_appointment`
  populate `old_status`/`new_status`?) is explicitly NOT decided here.
  That decision belongs to whoever builds the Service layer's
  audit-writing calls (Phase 4) and should be confirmed with the human
  developer first, per the Phase 3 instructions.

No read/list method is implemented: Service Design §17 does not
document one for AuditRepository.
"""

from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.repositories import _workbook_access as wa
from app.repositories.interfaces import AuditRepository

SHEET_NAME = "Audit_Log"

# The real, verified Audit_Log column set. Any key passed to create()
# outside this set is rejected rather than silently written, so a
# caller cannot accidentally introduce an undocumented column.
KNOWN_COLUMNS = {
    "event_id",
    "appointment_id",
    "action",
    "actor_type",
    "actor_id",
    "timestamp",
    "old_status",
    "new_status",
    "reason",
}


class ExcelAuditRepository(AuditRepository):
    """Excel-backed implementation of AuditRepository.create() only.

    See the module docstring above for the unresolved specification
    conflict this partial implementation reflects.
    """

    def __init__(self, excel_path=None):
        self._path = excel_path or get_settings().resolved_excel_file_path

    def create(self, event: dict[str, Any]) -> None:
        unknown = set(event.keys()) - KNOWN_COLUMNS
        if unknown:
            raise ValueError(
                f"Unknown Audit_Log column(s) {sorted(unknown)}. "
                f"Known columns: {sorted(KNOWN_COLUMNS)}. This repository "
                "intentionally does not invent columns beyond the "
                "verified workbook structure — see this module's "
                "docstring for the flagged Audit_Log specification "
                "conflict."
            )
        row = {col: event.get(col) for col in KNOWN_COLUMNS}
        # timestamp formatting follows the same convention observed for
        # created_at/updated_at in the Appointments sheet, if a caller
        # passes a datetime object rather than a pre-formatted string.
        if isinstance(row.get("timestamp"), datetime):
            row["timestamp"] = row["timestamp"].strftime("%Y-%m-%d %H:%M")
        with wa.WRITE_LOCK:
            wa.append_row(self._path, SHEET_NAME, row)
