"""Logging setup and request-ID foundation.

The Claude Implementation Master Guide (Phase 1) and FastAPI API Contract
Specification (route handler rules, error contract) both call for
traceable requests. This module provides:

  - a `configure_logging()` function to set up standard library logging
    with a consistent format that includes a request id field, and
  - a `request_id_ctx_var` ContextVar plus a small logging.Filter that
    injects the current request id into every log record.

The actual request-id *generation per HTTP request* is wired in
app/main.py via a lightweight ASGI middleware. No business logic lives
here.
"""

import logging
import sys
from contextvars import ContextVar

# Holds the current request's ID for the duration of that request.
# Defaults to "-" so logs emitted outside a request (e.g. at startup)
# still have a well-formed value instead of raising.
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdLogFilter(logging.Filter):
    """Injects the current request id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logging with a request-id-aware formatter.

    Safe to call once at application startup. Idempotent enough for local
    dev/reload use (clears existing handlers before adding ours).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Avoid duplicate handlers on reload.
    root_logger.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | request_id=%(request_id)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdLogFilter())

    root_logger.addHandler(handler)
