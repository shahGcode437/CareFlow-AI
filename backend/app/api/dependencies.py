"""FastAPI dependency wiring for the appointment + knowledge domains.

Constructs the concrete Excel-backed repositories, the AppointmentService
(Phase 4), the AppointmentTools (Phase 5), the AppointmentAgent (Phase
7), and — as of Phase 8.8.11 — the Router + KnowledgeAgent + KnowledgeRetriever
so the Supervisor can route to either specialized agent.

Phase 8.8.12 upgrades:
  * FastEmbed is now the production embedder (was HashingFallbackEmbedder
    in the 8.8.11 placeholder).
  * All RAG constants (data dir, top_k, embedding model) come from
    ``config.Settings`` — no more inline path literals.
  * The knowledge stack initialises with a graceful-degradation
    fallback: if the retriever cannot be built (missing knowledge
    dir, model download failure, corrupted YAML, ONNX runtime error),
    a :class:`NullKnowledgeAgent` is injected instead. The appointment
    side keeps working; knowledge questions return a controlled
    "temporarily unavailable" message.

Cached with lru_cache (the same pattern already used by
app.core.config.get_settings()) so these are constructed once per
process rather than once per request. Route tests override
get_appointment_tools / get_supervisor via FastAPI's
dependency_overrides mechanism to inject a mock, so this caching does
not affect testability.
"""

import logging
from functools import lru_cache

from app.agents.appointment_agent import AppointmentAgent
from app.agents.knowledge_agent import KnowledgeAgent, NullKnowledgeAgent
from app.agents.llm_provider import GroqLLMProvider, LLMProvider, RuleBasedIntentProvider
from app.agents.router import GroqRouter, Router, RuleBasedRouter
from app.agents.supervisor import Supervisor
from app.core.config import get_settings
from app.rag.documents import DocumentLoader
from app.rag.embedder import Embedder, FastEmbedEmbedder, HashingFallbackEmbedder
from app.rag.retriever import KnowledgeRetriever
from app.repositories.appointment_repository import ExcelAppointmentRepository
from app.repositories.availability_repository import ExcelAvailabilityRepository
from app.repositories.doctor_repository import ExcelDoctorRepository
from app.services.appointment_service import AppointmentService
from app.tools.appointment_tools import AppointmentTools

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Appointment side (unchanged — Phase 7.1 wiring)
# ---------------------------------------------------------------------------


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


def get_llm_provider() -> LLMProvider:
    """Build a fresh provider matching current settings.

    Deliberately NOT lru_cached: existing tests clear
    ``get_appointment_agent.cache_clear()`` after flipping
    ``LLM_PROVIDER`` env vars and expect the freshly-constructed
    agent to see the new provider. Caching here would defeat that.
    Construction is cheap — both providers are stateless
    request-per-request.
    """
    settings = get_settings()
    if settings.llm_provider == "groq" and settings.llm_api_key:
        return GroqLLMProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
    return RuleBasedIntentProvider()


@lru_cache
def get_appointment_agent() -> AppointmentAgent:
    """Config-driven provider selection — RuleBasedIntentProvider by
    default, GroqLLMProvider when LLM_PROVIDER=groq + LLM_API_KEY set.
    """
    return AppointmentAgent(get_llm_provider(), get_appointment_tools())


# ---------------------------------------------------------------------------
# Knowledge side (Phase 8.8.11 wiring, Phase 8.8.12 FastEmbed swap)
# ---------------------------------------------------------------------------


@lru_cache
def get_knowledge_embedder() -> Embedder:
    """FastEmbed with a deterministic fallback.

    Phase 8.8.12 swap point: production embeddings via FastEmbed (ONNX
    MiniLM by default, 384-dim, no API key). If FastEmbed can't be
    constructed for any reason — corrupt cache, missing ONNX runtime,
    incompatible platform — fall back to the deterministic
    HashingFallbackEmbedder so the app still boots. Retrieval quality
    degrades in that case, but nothing crashes.
    """
    settings = get_settings()
    try:
        return FastEmbedEmbedder(model_name=settings.rag_embedding_model)
    except Exception as exc:  # pragma: no cover - defensive
        _logger.warning(
            "FastEmbedEmbedder construction failed (%s); falling back to "
            "HashingFallbackEmbedder. Knowledge retrieval quality will be "
            "degraded until the underlying issue is resolved.",
            exc,
        )
        return HashingFallbackEmbedder(dimension=384)


@lru_cache
def get_knowledge_retriever() -> KnowledgeRetriever | None:
    """Build the retriever ONCE at first-request time.

    Returns ``None`` if any part of the RAG stack fails to initialise
    (missing knowledge dir, YAML validation failure, embedder crash,
    model download failure). Callers must handle the ``None`` case —
    see :func:`get_knowledge_agent`.
    """
    settings = get_settings()
    try:
        documents = DocumentLoader(settings.resolved_knowledge_data_dir).load()
        return KnowledgeRetriever.build(
            documents,
            get_knowledge_embedder(),
            default_top_k=settings.rag_top_k,
            default_min_similarity=settings.rag_min_similarity,
        )
    except Exception as exc:
        _logger.warning(
            "KnowledgeRetriever initialisation failed (%s). The Knowledge "
            "Agent will run in degraded mode until the underlying issue is "
            "resolved.",
            exc,
        )
        return None


@lru_cache
def get_knowledge_agent() -> KnowledgeAgent | NullKnowledgeAgent:
    """Return a real :class:`KnowledgeAgent` when the retriever is
    healthy; a :class:`NullKnowledgeAgent` otherwise. Supervisor
    duck-types both — it only calls ``.handle(message, context=None)``.
    """
    retriever = get_knowledge_retriever()
    if retriever is None:
        return NullKnowledgeAgent()
    settings = get_settings()
    return KnowledgeAgent(
        get_llm_provider(),
        retriever,
        top_k=settings.rag_top_k,
    )


# ---------------------------------------------------------------------------
# Router (Phase 8.8.10)
# ---------------------------------------------------------------------------


@lru_cache
def get_router() -> Router:
    """Groq-backed router when configured, deterministic rule-based
    otherwise. Groq router falls back to the rule-based one on any
    parsing / HTTP failure, so misclassifications are always safe.
    """
    settings = get_settings()
    fallback = RuleBasedRouter()
    if settings.llm_provider == "groq" and settings.llm_api_key:
        return GroqRouter(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            fallback=fallback,
        )
    return fallback


# ---------------------------------------------------------------------------
# Supervisor — top-level orchestrator (Phase 8.8.11)
# ---------------------------------------------------------------------------


@lru_cache
def get_supervisor() -> Supervisor:
    return Supervisor(
        router=get_router(),
        appointment_agent=get_appointment_agent(),
        knowledge_agent=get_knowledge_agent(),
    )
