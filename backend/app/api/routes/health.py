"""Health check route.

This is the only route implemented in Phase 1. Appointment, chat, and
staff routes are added in Phase 6 per the approved FastAPI API Contract
Specification and are intentionally out of scope here.
"""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict:
    """Basic liveness/readiness signal for local dev, CI, and Docker healthchecks."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
