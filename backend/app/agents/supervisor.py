"""Supervisor — top-level routing entry point (Phase 8.8.11 update).

Master Specification SYS-01: "Understands high-level intent, routes
requests, coordinates specialized capabilities, and composes
responses."

Architecture as of Phase 8.8.11:

                              -> AppointmentAgent
    user message -> Router -> Supervisor
                              -> KnowledgeAgent

The Supervisor:
  1. Asks the injected :class:`Router` to classify the message
     (:class:`AgentRoute.APPOINTMENT` / .KNOWLEDGE / .UNSUPPORTED).
  2. Delegates to the corresponding agent (constructor-injected — no
     hidden globals).
  3. Applies a one-shot fallback: if the router picked
     APPOINTMENT and the AppointmentAgent replied ``unsupported``,
     the Supervisor tries the KnowledgeAgent once before giving up.
     This handles the "the router misjudged an ambiguous message"
     case without ever looping.
  4. Composes the agent's :class:`AgentResponse` into the documented
     :class:`ChatResponse` shape (FastAPI API Contract §4.2).

Never touches the workbook or the appointment service layer
directly. Session-state / patient_phone handling is unchanged from
Phase 7.1.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.agents.appointment_agent import AgentResponse, AppointmentAgent
from app.agents.knowledge_agent import KNOWLEDGE_ANSWER_INTENT, KnowledgeAgent
from app.agents.router import AgentRoute, Router


# Fixed unsupported reply — broader than the AppointmentAgent's own
# "unsupported" message because we now cover knowledge questions too.
UNSUPPORTED_INTENT = "unsupported"
UNSUPPORTED_MESSAGE = (
    "I can help with clinic knowledge questions (doctors, services, "
    "clinic policies, FAQs) and with appointment operations "
    "(availability, booking, rescheduling, cancellation, staff "
    "approval). Could you clarify what you'd like to know or do?"
)


class Supervisor:
    def __init__(
        self,
        router: Router,
        appointment_agent: AppointmentAgent,
        knowledge_agent: KnowledgeAgent,
    ):
        self._router = router
        self._appointment_agent = appointment_agent
        self._knowledge_agent = knowledge_agent

    # -- public --------------------------------------------------------------

    def handle_message(
        self,
        message: str,
        session_id: str | None = None,
        patient_phone: str | None = None,
    ) -> dict[str, Any]:
        """Returns a dict matching the documented ChatResponse shape
        (FastAPI API Contract Specification v1.0 §4.2): message, intent,
        data, requires_staff_review, request_id.

        ``session_id`` is accepted (matching the documented ChatRequest
        shape) but not persisted server-side — no specification
        document defines conversation-state requirements beyond this
        optional identifier, unchanged from Phase 7.
        """
        context = {"patient_phone": patient_phone} if patient_phone else None

        route = self._router.route(message)

        if route == AgentRoute.APPOINTMENT:
            response = self._appointment_agent.handle(message, context)
            # Two-stage fallback: the router thought this was an
            # appointment operation but the AppointmentAgent didn't
            # recognize it. Try knowledge before returning unsupported.
            if response.intent == UNSUPPORTED_INTENT:
                fallback = self._try_knowledge(message)
                if fallback is not None:
                    response = fallback
                else:
                    response = self._unsupported_response()
        elif route == AgentRoute.KNOWLEDGE:
            response = self._knowledge_agent.handle(message)
        else:
            # AgentRoute.UNSUPPORTED — do not spend a knowledge call
            # on requests the router already flagged as outside our
            # scope (avoids wasted retrieval + LLM traffic).
            response = self._unsupported_response()

        return self._compose(response)

    # -- internals -----------------------------------------------------------

    def _try_knowledge(self, message: str) -> AgentResponse | None:
        """Ask the KnowledgeAgent. Return its response only when it
        actually grounded an answer (non-empty citations). If it
        couldn't ground either, return ``None`` so the caller can fall
        through to the Supervisor's own unsupported message."""
        knowledge_response = self._knowledge_agent.handle(message)
        if knowledge_response.intent != KNOWLEDGE_ANSWER_INTENT:
            return None
        citations = (knowledge_response.data or {}).get("citations")
        if not isinstance(citations, list) or len(citations) == 0:
            return None
        return knowledge_response

    def _unsupported_response(self) -> AgentResponse:
        return AgentResponse(
            message=UNSUPPORTED_MESSAGE,
            intent=UNSUPPORTED_INTENT,
            data=None,
            requires_staff_review=False,
        )

    @staticmethod
    def _compose(response: AgentResponse) -> dict[str, Any]:
        return {
            "message": response.message,
            "intent": response.intent,
            "data": response.data,
            "requires_staff_review": response.requires_staff_review,
            "request_id": str(uuid.uuid4()),
        }
