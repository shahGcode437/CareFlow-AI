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
from app.agents.llm_provider import GroqLLMProvider, LLMProvider, RuleBasedIntentProvider
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
    """Phase 7.1: selects a real LLM-backed provider only when
    LLM_PROVIDER=groq AND LLM_API_KEY is actually set. Otherwise falls
    back to RuleBasedIntentProvider — the deterministic, no-external-call
    placeholder — so the app remains importable and testable with zero
    LLM configuration. Swapping providers is entirely config-driven; no
    change to AppointmentAgent/Supervisor is ever required.
    """
    settings = get_settings()
    provider: LLMProvider
    if settings.llm_provider == "groq" and settings.llm_api_key:
        provider = GroqLLMProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
    else:
        provider = RuleBasedIntentProvider()
    return AppointmentAgent(provider, get_appointment_tools())


@lru_cache
def get_supervisor() -> Supervisor:
    return Supervisor(get_appointment_agent())

