"""Internal helper: Excel string <-> Python date/time/datetime conversion.

The real workbook (verified directly, Phase 3 inspection) stores every
date/time/datetime value as a plain string, never a native Excel date
cell. The exact formats are documented in the workbook's own `Config`
sheet:
    date_format = "YYYY-MM-DD"
    time_format = "HH:MM"
`created_at`/`updated_at` combine both with a single space, as observed
directly in the Appointments sheet's demo rows (e.g. "2026-08-15 20:00").

This module is a private implementation detail of the repository layer
(underscore-prefixed, not part of the documented repository contract)
and contains no business logic — only serialization.
"""

from datetime import date, datetime, time

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def parse_date(value: str) -> date:
    return datetime.strptime(value, DATE_FORMAT).date()


def parse_time(value: str) -> time:
    return datetime.strptime(value, TIME_FORMAT).time()


def parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, DATETIME_FORMAT)


def format_date(value: date) -> str:
    return value.strftime(DATE_FORMAT)


def format_time(value: time) -> str:
    # time.strftime works directly on datetime.time objects.
    return value.strftime(TIME_FORMAT)


def format_datetime(value: datetime) -> str:
    return value.strftime(DATETIME_FORMAT)
