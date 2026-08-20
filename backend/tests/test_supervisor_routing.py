"""Phase 8.8.11 tests - Supervisor routing + two-stage fallback.

Fully offline: no LLM, no FastEmbed download, no Excel mutations. All
agents and the router are hand-rolled fakes so the Supervisor's
routing logic is tested in isolation.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.appointment_agent import AgentResponse
from app.agents.knowledge_agent import KNOWLEDGE_ANSWER_INTENT
from app.agents.router import AgentRoute, Router
from app.agents.supervisor import (
    Supervisor,
    UNSUPPORTED_INTENT,
    UNSUPPORTED_MESSAGE,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeRouter(Router):
    """Router that returns a scripted route and records the call."""

    def __init__(self, route: AgentRoute):
        self._route = route
        self.calls: list[str] = []

    def route(self, message: str) -> AgentRoute:
        self.calls.append(message)
        return self._route


class FakeAppointmentAgent:
    def __init__(self, response: AgentResponse):
        self._response = response
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def handle(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        self.calls.append((message, context))
        return self._response


class FakeKnowledgeAgent:
    def __init__(self, response: AgentResponse):
        self._response = response
        self.calls: list[str] = []

    def handle(
        self,
        message: str,
        _context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        self.calls.append(message)
        return self._response


class RaisingAgent:
    def handle(self, message, context=None):
        raise RuntimeError("simulated agent failure")


def _make(
    *,
    route: AgentRoute,
    appt: AgentResponse | None = None,
    know: AgentResponse | None = None,
):
    appt_resp = appt or AgentResponse(
        message="appointment ok",
        intent="get_appointment",
        data={"appointment_id": "APT-001"},
        requires_staff_review=False,
    )
    know_resp = know or AgentResponse(
        message="knowledge ok",
        intent=KNOWLEDGE_ANSWER_INTENT,
        data={"citations": [{"source": "doctor:DOC-001"}]},
        requires_staff_review=False,
    )
    return (
        Supervisor(
            router=FakeRouter(route),
            appointment_agent=FakeAppointmentAgent(appt_resp),
            knowledge_agent=FakeKnowledgeAgent(know_resp),
        ),
        appt_resp,
        know_resp,
    )


# ---------------------------------------------------------------------------
# 1-3: primary routing
# ---------------------------------------------------------------------------


def test_appointment_route_delegates_to_appointment_agent():
    sup, _, _ = _make(route=AgentRoute.APPOINTMENT)
    result = sup.handle_message("book an appointment")
    assert result["intent"] == "get_appointment"
    assert result["message"] == "appointment ok"
    assert result["data"] == {"appointment_id": "APT-001"}


def test_knowledge_route_delegates_to_knowledge_agent():
    sup, _, _ = _make(route=AgentRoute.KNOWLEDGE)
    result = sup.handle_message("who is Dr. Ahmed?")
    assert result["intent"] == KNOWLEDGE_ANSWER_INTENT
    assert result["message"] == "knowledge ok"
    assert result["data"]["citations"][0]["source"] == "doctor:DOC-001"


def test_unsupported_route_returns_supervisor_unsupported_response():
    sup, _, _ = _make(route=AgentRoute.UNSUPPORTED)
    result = sup.handle_message("what's the weather?")
    assert result["intent"] == UNSUPPORTED_INTENT
    assert result["message"] == UNSUPPORTED_MESSAGE
    assert result["data"] is None


def test_unsupported_route_does_not_call_either_agent():
    """A router-flagged unsupported request must not waste an
    appointment or knowledge call."""
    router = FakeRouter(AgentRoute.UNSUPPORTED)
    appt = FakeAppointmentAgent(
        AgentResponse(
            message="never", intent="get_appointment", data=None, requires_staff_review=False
        )
    )
    know = FakeKnowledgeAgent(
        AgentResponse(
            message="never", intent=KNOWLEDGE_ANSWER_INTENT, data=None, requires_staff_review=False
        )
    )
    sup = Supervisor(router=router, appointment_agent=appt, knowledge_agent=know)
    sup.handle_message("what's the weather?")
    assert appt.calls == []
    assert know.calls == []


# ---------------------------------------------------------------------------
# 4-5: two-stage fallback
# ---------------------------------------------------------------------------


def test_appointment_unsupported_falls_back_to_knowledge_when_grounded():
    """Router picked APPOINTMENT but the AppointmentAgent said
    'unsupported'. The Supervisor asks the KnowledgeAgent — if
    knowledge grounded an answer (has citations), that reply wins."""
    router = FakeRouter(AgentRoute.APPOINTMENT)
    appt = FakeAppointmentAgent(
        AgentResponse(
            message="I can't help with that.",
            intent=UNSUPPORTED_INTENT,
            data=None,
            requires_staff_review=False,
        )
    )
    know = FakeKnowledgeAgent(
        AgentResponse(
            message="Dr. Ahmed is a general physician.",
            intent=KNOWLEDGE_ANSWER_INTENT,
            data={
                "citations": [
                    {
                        "source": "doctor:DOC-001",
                        "document_type": "doctor",
                        "document_id": "DOC-001",
                        "title": "Dr. Ahmed - General Medicine",
                        "score": 0.9,
                    }
                ]
            },
            requires_staff_review=False,
        )
    )
    sup = Supervisor(router=router, appointment_agent=appt, knowledge_agent=know)
    result = sup.handle_message("who is Dr. Ahmed?")

    assert len(appt.calls) == 1  # appointment attempted first
    assert len(know.calls) == 1  # knowledge attempted second
    # Knowledge answer wins
    assert result["intent"] == KNOWLEDGE_ANSWER_INTENT
    assert result["message"] == "Dr. Ahmed is a general physician."
    assert result["data"]["citations"][0]["source"] == "doctor:DOC-001"


def test_appointment_unsupported_falls_back_to_supervisor_unsupported_when_knowledge_empty():
    """If BOTH agents can't answer, the Supervisor's own unsupported
    reply wins — not the appointment agent's narrower message, not
    the knowledge 'not in the knowledge base' message."""
    router = FakeRouter(AgentRoute.APPOINTMENT)
    appt = FakeAppointmentAgent(
        AgentResponse(
            message="appointment says no",
            intent=UNSUPPORTED_INTENT,
            data=None,
            requires_staff_review=False,
        )
    )
    know = FakeKnowledgeAgent(
        AgentResponse(
            message="I don't have that information in the clinic knowledge base.",
            intent=KNOWLEDGE_ANSWER_INTENT,
            data={"citations": []},
            requires_staff_review=False,
        )
    )
    sup = Supervisor(router=router, appointment_agent=appt, knowledge_agent=know)
    result = sup.handle_message("random thing neither can answer")

    assert len(appt.calls) == 1
    assert len(know.calls) == 1
    assert result["intent"] == UNSUPPORTED_INTENT
    assert result["message"] == UNSUPPORTED_MESSAGE


def test_successful_appointment_reply_does_not_call_knowledge_agent():
    """No fallback when the appointment side has a real answer."""
    router = FakeRouter(AgentRoute.APPOINTMENT)
    appt = FakeAppointmentAgent(
        AgentResponse(
            message="Appointment APT-001 is Pending.",
            intent="get_appointment",
            data={"appointment_id": "APT-001"},
            requires_staff_review=True,
        )
    )
    know = FakeKnowledgeAgent(
        AgentResponse(
            message="never called", intent=KNOWLEDGE_ANSWER_INTENT, data=None, requires_staff_review=False
        )
    )
    sup = Supervisor(router=router, appointment_agent=appt, knowledge_agent=know)
    result = sup.handle_message("look up appointment APT-001")

    assert len(appt.calls) == 1
    assert know.calls == []  # knowledge NOT called
    assert result["intent"] == "get_appointment"
    assert result["requires_staff_review"] is True


def test_appointment_needs_information_does_not_trigger_knowledge_fallback():
    """`needs_information` is not the same as `unsupported` — the
    appointment intent WAS recognized, we just need more fields."""
    router = FakeRouter(AgentRoute.APPOINTMENT)
    appt = FakeAppointmentAgent(
        AgentResponse(
            message="To do that, I still need: doctor_id.",
            intent="needs_information",
            data=None,
            requires_staff_review=False,
        )
    )
    know = FakeKnowledgeAgent(
        AgentResponse(
            message="grounded", intent=KNOWLEDGE_ANSWER_INTENT, data={"citations": [{}]}, requires_staff_review=False
        )
    )
    sup = Supervisor(router=router, appointment_agent=appt, knowledge_agent=know)
    result = sup.handle_message("book at 5 PM")

    assert know.calls == []  # NOT called
    assert result["intent"] == "needs_information"


# ---------------------------------------------------------------------------
# 6-7: knowledge response fidelity
# ---------------------------------------------------------------------------


def test_knowledge_response_preserves_intent():
    sup, _, _ = _make(route=AgentRoute.KNOWLEDGE)
    assert sup.handle_message("Q")["intent"] == KNOWLEDGE_ANSWER_INTENT


def test_knowledge_citations_and_data_survive_supervisor_composition():
    know = AgentResponse(
        message="Dr. Ahmed practises general medicine.",
        intent=KNOWLEDGE_ANSWER_INTENT,
        data={
            "citations": [
                {
                    "source": "doctor:DOC-001",
                    "document_type": "doctor",
                    "document_id": "DOC-001",
                    "title": "Dr. Ahmed - General Medicine",
                    "score": 0.87,
                }
            ]
        },
        requires_staff_review=False,
    )
    sup, _, _ = _make(route=AgentRoute.KNOWLEDGE, know=know)
    result = sup.handle_message("Q")
    assert result["data"] == {
        "citations": [
            {
                "source": "doctor:DOC-001",
                "document_type": "doctor",
                "document_id": "DOC-001",
                "title": "Dr. Ahmed - General Medicine",
                "score": 0.87,
            }
        ]
    }


# ---------------------------------------------------------------------------
# 8: agent failure surfaces via existing conventions (RuntimeError bubbles)
# ---------------------------------------------------------------------------


def test_appointment_agent_failure_bubbles_up():
    """Deliberate: agents' `handle()` is not expected to raise for
    normal operational errors — those become AgentResponse(
    intent='error'). If an agent DOES raise, it's a bug and the
    exception should bubble up so it hits the FastAPI middleware and
    gets logged with the request id (existing app.main convention).
    Supervisor MUST NOT swallow arbitrary exceptions silently."""
    router = FakeRouter(AgentRoute.APPOINTMENT)
    sup = Supervisor(
        router=router,
        appointment_agent=RaisingAgent(),
        knowledge_agent=FakeKnowledgeAgent(
            AgentResponse(message="x", intent=KNOWLEDGE_ANSWER_INTENT, data=None, requires_staff_review=False)
        ),
    )
    with pytest.raises(RuntimeError, match="simulated agent failure"):
        sup.handle_message("book something")


def test_knowledge_agent_failure_bubbles_up():
    router = FakeRouter(AgentRoute.KNOWLEDGE)
    sup = Supervisor(
        router=router,
        appointment_agent=FakeAppointmentAgent(
            AgentResponse(message="x", intent="get_appointment", data=None, requires_staff_review=False)
        ),
        knowledge_agent=RaisingAgent(),
    )
    with pytest.raises(RuntimeError, match="simulated agent failure"):
        sup.handle_message("what's the policy?")


# ---------------------------------------------------------------------------
# 9-10: session_id / patient_phone / request_id
# ---------------------------------------------------------------------------


def test_request_id_is_generated_per_call():
    """A fresh request_id on every handle_message so log correlation
    stays clean. Uses uuid4 - vanishingly small collision chance."""
    sup, _, _ = _make(route=AgentRoute.APPOINTMENT)
    a = sup.handle_message("m1")
    b = sup.handle_message("m2")
    assert a["request_id"]
    assert b["request_id"]
    assert a["request_id"] != b["request_id"]


def test_patient_phone_is_forwarded_as_context_to_appointment_agent():
    router = FakeRouter(AgentRoute.APPOINTMENT)
    appt = FakeAppointmentAgent(
        AgentResponse(
            message="ok", intent="get_appointment", data=None, requires_staff_review=False
        )
    )
    know = FakeKnowledgeAgent(
        AgentResponse(message="x", intent=KNOWLEDGE_ANSWER_INTENT, data=None, requires_staff_review=False)
    )
    sup = Supervisor(router=router, appointment_agent=appt, knowledge_agent=know)
    sup.handle_message("book something", patient_phone="03000000000")
    assert appt.calls == [("book something", {"patient_phone": "03000000000"})]


def test_no_patient_phone_means_no_context_passed():
    router = FakeRouter(AgentRoute.APPOINTMENT)
    appt = FakeAppointmentAgent(
        AgentResponse(message="ok", intent="get_appointment", data=None, requires_staff_review=False)
    )
    sup = Supervisor(
        router=router,
        appointment_agent=appt,
        knowledge_agent=FakeKnowledgeAgent(
            AgentResponse(message="x", intent=KNOWLEDGE_ANSWER_INTENT, data=None, requires_staff_review=False)
        ),
    )
    sup.handle_message("book something")
    assert appt.calls == [("book something", None)]


def test_session_id_is_accepted_and_ignored_matching_existing_behavior():
    """Session state is not persisted server-side (Phase 7 flagged
    decision). The Supervisor accepts the arg for forward-compat."""
    sup, _, _ = _make(route=AgentRoute.APPOINTMENT)
    # No error, response shape unchanged whether or not session_id is passed.
    a = sup.handle_message("m", session_id="sess-1")
    assert set(a.keys()) == {"message", "intent", "data", "requires_staff_review", "request_id"}


# ---------------------------------------------------------------------------
# 11: no infinite agent-routing loop
# ---------------------------------------------------------------------------


def test_two_stage_fallback_is_one_shot_no_loop():
    """Both agents are called at most once per user message,
    regardless of what either returns."""
    router = FakeRouter(AgentRoute.APPOINTMENT)
    appt = FakeAppointmentAgent(
        AgentResponse(message="x", intent=UNSUPPORTED_INTENT, data=None, requires_staff_review=False)
    )
    know = FakeKnowledgeAgent(
        AgentResponse(
            message="also can't help",
            intent=KNOWLEDGE_ANSWER_INTENT,
            data={"citations": []},
            requires_staff_review=False,
        )
    )
    sup = Supervisor(router=router, appointment_agent=appt, knowledge_agent=know)
    sup.handle_message("something weird")
    # Router called once, appointment called once, knowledge called once.
    assert len(router.calls) == 1
    assert len(appt.calls) == 1
    assert len(know.calls) == 1


def test_appointment_success_calls_router_and_appointment_exactly_once():
    router = FakeRouter(AgentRoute.APPOINTMENT)
    appt = FakeAppointmentAgent(
        AgentResponse(message="ok", intent="get_appointment", data=None, requires_staff_review=False)
    )
    know = FakeKnowledgeAgent(
        AgentResponse(message="x", intent=KNOWLEDGE_ANSWER_INTENT, data=None, requires_staff_review=False)
    )
    sup = Supervisor(router=router, appointment_agent=appt, knowledge_agent=know)
    sup.handle_message("Q")
    assert len(router.calls) == 1
    assert len(appt.calls) == 1
    assert len(know.calls) == 0


# ---------------------------------------------------------------------------
# 12: existing supervisor behavior remains compatible
# ---------------------------------------------------------------------------


def test_response_shape_unchanged_from_previous_phases():
    """Existing test_routes.py + test_llm_integration.py assumptions
    about the dict shape must still hold."""
    sup, _, _ = _make(route=AgentRoute.APPOINTMENT)
    result = sup.handle_message("m")
    assert set(result.keys()) == {
        "message",
        "intent",
        "data",
        "requires_staff_review",
        "request_id",
    }
    assert isinstance(result["message"], str)
    assert isinstance(result["intent"], str)
    assert isinstance(result["requires_staff_review"], bool)
    assert isinstance(result["request_id"], str)


def test_message_content_passed_to_router_verbatim():
    """The router receives the raw user message — Supervisor doesn't
    pre-clean it, so router heuristics see what the user actually typed."""
    router = FakeRouter(AgentRoute.UNSUPPORTED)
    sup = Supervisor(
        router=router,
        appointment_agent=FakeAppointmentAgent(
            AgentResponse(message="x", intent="get_appointment", data=None, requires_staff_review=False)
        ),
        knowledge_agent=FakeKnowledgeAgent(
            AgentResponse(message="x", intent=KNOWLEDGE_ANSWER_INTENT, data=None, requires_staff_review=False)
        ),
    )
    sup.handle_message("  MiXeD case with SpAcEs  ")
    assert router.calls == ["  MiXeD case with SpAcEs  "]


# ---------------------------------------------------------------------------
# Structural
# ---------------------------------------------------------------------------


def test_supervisor_source_does_not_touch_repositories_or_excel():
    from pathlib import Path
    src = (
        Path(__file__).resolve().parents[1] / "app" / "agents" / "supervisor.py"
    ).read_text(encoding="utf-8")
    for banned in ("openpyxl", "pandas", "repositor", ".xlsx", "AppointmentService", "AppointmentTools"):
        assert banned.lower() not in src.lower(), (
            f"supervisor.py must not touch appointment infrastructure; found {banned}"
        )
