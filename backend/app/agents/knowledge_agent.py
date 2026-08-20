"""KnowledgeAgent — Master Spec SYS-02 (Phase 8.8.9).

Combines the Phase 8.8.3-8.8.7 RAG pipeline with the Phase 8.8.8
grounded-LLM interface to answer clinic-specific knowledge questions.

    user question
        -> KnowledgeRetriever.retrieve(question, top_k=default 4)
        -> RetrievalResult[]
        -> LLMProvider.answer_from_context(question, [chunk.text, ...])
        -> AnswerFromContext
        -> AgentResponse(intent="knowledge_answer", data={"citations": [...]})

Framework-independent, mirrors the existing AppointmentAgent pattern:
constructor-injected dependencies, reuses the shared `AgentResponse`
dataclass, never touches Excel or the appointment service layer.

Availability authority:
    Live "is this slot free?" questions are NEVER answered from RAG
    context. They are detected up front and deferred to the
    appointment side (Master Spec §11 and Phase 8.8.8 grounding rule
    #5). The doctor YAML's ``available_days_summary`` field remains
    informational only.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.appointment_agent import AgentResponse
from app.agents.llm_provider import (
    AnswerFromContext,
    LLMProvider,
    NOT_IN_KNOWLEDGE_BASE_MESSAGE,
)
from app.rag.retriever import KnowledgeRetriever, RetrievalResult


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------


KNOWLEDGE_ANSWER_INTENT = "knowledge_answer"

# Every user-facing failure message lives here so the KnowledgeAgent
# never accidentally coins a new one downstream.
KNOWLEDGE_UNAVAILABLE_MESSAGE = (
    "The clinic knowledge base is temporarily unavailable. Please try "
    "again shortly."
)
EMPTY_QUESTION_MESSAGE = (
    "Please ask a question about the clinic (doctors, services, "
    "policies, or FAQs)."
)
AVAILABILITY_DEFERRAL_MESSAGE = (
    "For live appointment availability, please use the availability "
    "checker or the appointment assistant — the clinic knowledge "
    "base only stores each doctor's general schedule summary."
)


# ---------------------------------------------------------------------------
# Availability heuristic
# ---------------------------------------------------------------------------


# Meta / process questions ("how do I ...", "what is ...") are ALWAYS
# knowledge questions — never deferred, even if they mention booking.
# The FAQ has to be answerable.
_META_QUESTION_RE = re.compile(
    r"\bhow (?:do|can|to)\b|"
    r"\bwhat (?:is|are|does|happens)\b|"
    r"\bwhy (?:does|is)\b|"
    r"\bwhen (?:does|is)\b|"
    r"\bwho (?:is|are)\b|"
    r"\bwhich\b",
    re.IGNORECASE,
)

# Explicit phrases that signal an action / live-availability query.
# Deliberately narrow: broader signals fire false positives on the
# rendered doctor / policy chunks (which describe scheduling in
# prose and rightly stay in the knowledge path).
_AVAILABILITY_PHRASES = (
    "can i book",
    "book with",
    "book me",
    "book an appointment",
    "book appointment",
    "reschedule",
    "cancel appointment",
    "cancel my appointment",
    "free at",
    "free on",
    "slot free",
    "any slot",
    "any slots",
    "any openings",
    "free slot",
    "open slot",
)

# The word "available" as a whole word (not "availability"), when it
# co-occurs with a specific day / clock time, is a strong live-check
# signal. `\bavailable\b` deliberately does NOT match "Availability"
# so the rendered doctor chunks (which contain "Availability Summary")
# don't get deferred by accident.
_AVAILABLE_WORD_RE = re.compile(r"\bavailable\b", re.IGNORECASE)
_DAY_NAME_RE = re.compile(
    r"\b(sunday|monday|tuesday|wednesday|thursday|friday|saturday|today|tomorrow)\b",
    re.IGNORECASE,
)
_CLOCK_TIME_RE = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", re.IGNORECASE)
_ISO_TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b")


def _looks_like_live_availability_question(message: str) -> bool:
    """Return True iff the message looks like a live-availability /
    booking request that should be handled by the appointment side."""
    # Meta / process questions are knowledge, full stop.
    if _META_QUESTION_RE.search(message):
        return False

    lowered = message.lower()
    if any(phrase in lowered for phrase in _AVAILABILITY_PHRASES):
        return True

    # "available" as a standalone word + a day-of-week or clock time.
    if _AVAILABLE_WORD_RE.search(message):
        if (
            _DAY_NAME_RE.search(message)
            or _CLOCK_TIME_RE.search(message)
            or _ISO_TIME_RE.search(message)
        ):
            return True

    return False


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class KnowledgeAgent:
    """Answers clinic knowledge questions with grounded citations."""

    def __init__(
        self,
        provider: LLMProvider,
        retriever: KnowledgeRetriever,
        *,
        top_k: int | None = None,
    ):
        self._provider = provider
        self._retriever = retriever
        if top_k is not None:
            if not isinstance(top_k, int) or isinstance(top_k, bool):
                raise ValueError("top_k must be an int.")
            if top_k <= 0:
                raise ValueError("top_k must be > 0.")
        self._top_k = top_k  # None -> use retriever's own default

    # -- public --------------------------------------------------------------

    def handle(
        self,
        message: str,
        _context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Return a knowledge-scoped answer, or a safe fallback.

        The ``context`` parameter mirrors AppointmentAgent's signature
        so the Supervisor can call both agents through one shape. It
        is currently unused here — knowledge questions don't depend on
        patient identity or session state.
        """
        cleaned = self._clean_message(message)
        if cleaned is None:
            return self._response(
                message=EMPTY_QUESTION_MESSAGE,
                citations=[],
            )

        # Live availability questions must not be answered from RAG.
        if _looks_like_live_availability_question(cleaned):
            return self._response(
                message=AVAILABILITY_DEFERRAL_MESSAGE,
                citations=[],
                extra={"deferred_to": "appointment_system"},
            )

        try:
            results = self._retrieve(cleaned)
        except Exception:
            # Retriever infrastructure failure — never a stack trace
            # to the user.
            return self._response(
                message=KNOWLEDGE_UNAVAILABLE_MESSAGE,
                citations=[],
            )

        if not results:
            # Skip the LLM call entirely — no context to ground on.
            return self._response(
                message=NOT_IN_KNOWLEDGE_BASE_MESSAGE,
                citations=[],
            )

        try:
            answer = self._provider.answer_from_context(
                question=cleaned,
                context_chunks=[r.chunk.text for r in results],
            )
        except Exception:
            return self._response(
                message=KNOWLEDGE_UNAVAILABLE_MESSAGE,
                citations=[],
            )

        if not answer.from_context:
            # LLM couldn't ground the answer — surface its safe reply
            # verbatim and DO NOT expose the retrieved snippets, so a
            # low-confidence hit can't accidentally look authoritative.
            return self._response(
                message=answer.answer or NOT_IN_KNOWLEDGE_BASE_MESSAGE,
                citations=[],
            )

        return self._response(
            message=answer.answer,
            citations=self._build_citations(results),
        )

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _clean_message(message: Any) -> str | None:
        if not isinstance(message, str):
            return None
        cleaned = message.strip()
        return cleaned if cleaned else None

    def _retrieve(self, question: str) -> list[RetrievalResult]:
        if self._top_k is not None:
            return self._retriever.retrieve(question, top_k=self._top_k)
        return self._retriever.retrieve(question)

    @staticmethod
    def _build_citations(results: list[RetrievalResult]) -> list[dict[str, Any]]:
        """Structured provenance for the frontend.

        Deduplicates by ``chunk_id`` (the strongest identifier), keeps
        the highest score seen for each id, and preserves the order in
        which distinct sources first appeared — matching the
        similarity-ranked order the retriever returned.
        """
        seen: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for hit in results:
            chunk = hit.chunk
            key = chunk.chunk_id
            existing = seen.get(key)
            if existing is None:
                seen[key] = {
                    "source": chunk.chunk_id,
                    "document_type": chunk.document_type,
                    "document_id": chunk.document_id,
                    "title": _derive_title(chunk),
                    "score": float(hit.score),
                }
                order.append(key)
            else:
                # Duplicate chunk_id (defensive — chunker guarantees
                # uniqueness today) — keep the highest similarity.
                if hit.score > existing["score"]:
                    existing["score"] = float(hit.score)
        return [seen[k] for k in order]

    @staticmethod
    def _response(
        *,
        message: str,
        citations: list[dict[str, Any]],
        extra: dict[str, Any] | None = None,
    ) -> AgentResponse:
        data: dict[str, Any] = {"citations": citations}
        if extra:
            data.update(extra)
        return AgentResponse(
            message=message,
            intent=KNOWLEDGE_ANSWER_INTENT,
            data=data,
            requires_staff_review=False,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _derive_title(chunk) -> str:  # KnowledgeChunk — no import needed at runtime
    """Human-readable label for a chunk's citation.

    Ordering of precedence:
      1. Doctor chunks: "<name> - <specialization>" (from loader metadata)
      2. Markdown chunks: the section title (chunker metadata)
      3. Fallback: chunk id
    """
    md = chunk.metadata or {}
    if chunk.document_type == "doctor":
        name = md.get("name")
        specialization = md.get("specialization")
        if isinstance(name, str) and isinstance(specialization, str):
            return f"{name} - {specialization}"
    section_title = md.get("section_title")
    if isinstance(section_title, str) and section_title:
        return section_title
    return chunk.chunk_id


class NullKnowledgeAgent:
    """Drop-in KnowledgeAgent that always reports the knowledge base
    is unavailable.

    Used by the composition layer (Phase 8.8.12) when the retriever /
    embedder cannot be initialised (missing knowledge dir, model
    download failure, etc.) — the appointment side must keep working
    even if RAG can't be built.

    Deliberately not a subclass of :class:`KnowledgeAgent`: the real
    agent's constructor requires a fitted retriever, and inheriting
    just to bypass that would be lying about what this object is.
    Duck-typed to match ``handle(message, context=None)``.
    """

    def handle(
        self,
        _message: str,
        _context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        return AgentResponse(
            message=KNOWLEDGE_UNAVAILABLE_MESSAGE,
            intent=KNOWLEDGE_ANSWER_INTENT,
            data={"citations": []},
            requires_staff_review=False,
        )


__all__ = [
    "AVAILABILITY_DEFERRAL_MESSAGE",
    "EMPTY_QUESTION_MESSAGE",
    "KNOWLEDGE_ANSWER_INTENT",
    "KNOWLEDGE_UNAVAILABLE_MESSAGE",
    "KnowledgeAgent",
    "NullKnowledgeAgent",
]
