"""FastAPI dependency wiring for the appointment domain.

Constructs the concrete Excel-backed repositories, the AppointmentService
(Phase 4), the AppointmentTools (Phase 5), and — as of Phase 7 — the
AppointmentAgent/Supervisor that routes depend on. This is the smallest
wiring layer needed to connect routes to the existing architecture —
pure composition, no business logic.

Cached with lru_cache (the same pattern already used by
app.core.config.get_settings()) so these are constructed once per
process rather than once per request. Route tests override
get_appointment_tools / get_supervisor via FastAPI's
dependency_overrides mechanism to inject a mock, so this caching does
not affect testability.
"""

from functools import lru_cache

from app.agents.appointment_agent import AppointmentAgent
from app.agents.llm_provider import RuleBasedIntentProvider
from app.agents.supervisor import Supervisor
from app.core.config import get_settings
from app.repositories.appointment_repository import ExcelAppointmentRepository
from app.repositories.availability_repository import ExcelAvailabilityRepository
from app.repositories.doctor_repository import ExcelDoctorRepository
from app.services.appointment_service import AppointmentService
from app.tools.appointment_tools import AppointmentTools


@lru_cache
def get_appointment_service() -> AppointmentService:
    settings = get_settings()
    return AppointmentService(
        appointment_repo=ExcelAppointmentRepository(),
        doctor_repo=ExcelDoctorRepository(),
        availability_repo=ExcelAvailabilityRepository(),
        require_staff_approval=settings.require_staff_approval,
    )


@lru_cache
def get_appointment_tools() -> AppointmentTools:
    return AppointmentTools(get_appointment_service())


@lru_cache
def get_appointment_agent() -> AppointmentAgent:
    """No specification names an LLM provider (Master Spec §25, open
    decision), so RuleBasedIntentProvider — the deterministic,
    no-external-call placeholder documented in app.agents.llm_provider —
    is wired in here. Swapping in a real provider later only requires
    changing this one line.
    """
    return AppointmentAgent(RuleBasedIntentProvider(), get_appointment_tools())


@lru_cache
def get_supervisor() -> Supervisor:
    return Supervisor(get_appointment_agent())

