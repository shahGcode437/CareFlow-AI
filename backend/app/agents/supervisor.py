"""Supervisor — top-level routing entry point.

Implements Master Specification SYS-01 ("Understands high-level intent,
routes requests, coordinates specialized capabilities, and composes
responses").

FLAGGED SCOPE DECISION (see Phase 7 report for full detail): the Master
Specification's full design includes a Knowledge/RAG Agent (SYS-02) for
clinic-information questions (UC-01/UC-02). That capability is NOT
implemented here — no Clinic Knowledge Store (SYS-05) exists in any
prior phase, and Master Specification §25 lists "Final RAG/vector-store
implementation" as an explicit, unresolved open decision. Building it
now would mean inventing an architecture the specifications deliberately
leave open, rather than following a documented one.

Every message is currently routed to the AppointmentAgent. The
Supervisor still performs real intent triage: when the AppointmentAgent
reports no recognized appointment intent, the caller gets an honest
"not supported yet" response instead of a silently fabricated answer or
a misrouted appointment action.

Never accesses repositories, Excel, or AppointmentService directly —
only composes the AppointmentAgent's response into the documented
ChatResponse shape.
"""

import uuid
from typing import Any

from app.agents.appointment_agent import AppointmentAgent


class Supervisor:
    def __init__(self, appointment_agent: AppointmentAgent):
        self._appointment_agent = appointment_agent

    def handle_message(
        self,
        message: str,
        session_id: str | None = None,
        patient_phone: str | None = None,
    ) -> dict[str, Any]:
        """Returns a dict matching the documented ChatResponse shape
        (FastAPI API Contract Specification v1.0 §4.2): message, intent,
        data, requires_staff_review, request_id.

        `session_id` is accepted (matching the documented ChatRequest
        shape) but not used to persist any conversation state — no
        specification document defines conversation-state requirements
        beyond this optional identifier, so no memory subsystem is
        introduced here, per Phase 7 instruction 11.
        """
        context = {"patient_phone": patient_phone} if patient_phone else None
        response = self._appointment_agent.handle(message, context)
        return {
            "message": response.message,
            "intent": response.intent,
            "data": response.data,
            "requires_staff_review": response.requires_staff_review,
            "request_id": str(uuid.uuid4()),
        }
