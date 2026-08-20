"""Phase 8.8.10 tests - agent router.

Fully offline: no Groq API key needed, no network calls. Groq tests
use injected `http_post` per the project's existing pattern (Phase
7.1 / 8.8.8).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.agents.router import (
    AgentRoute,
    GroqRouter,
    RuleBasedRouter,
    Router,
    _ROUTER_SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _fake_groq_response(content_json: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": content_json}}]}


def _make_groq(
    http_post, *, fallback: Router | None = None
) -> GroqRouter:
    return GroqRouter(api_key="test-key-not-real", http_post=http_post, fallback=fallback)


# ---------------------------------------------------------------------------
# 1-4: appointment-side routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "book an appointment",
        "book Dr. Ahmed for Sunday at 5 PM",
        "book a slot with DOC-001",
        "please book me at 17:30",
        "I want to book DOC-002",
    ],
)
def test_booking_messages_route_to_appointment(message):
    assert RuleBasedRouter().route(message) == AgentRoute.APPOINTMENT


@pytest.mark.parametrize(
    "message",
    [
        "cancel appointment APT-001",
        "cancel my appointment",
        "please cancel APT-002",
    ],
)
def test_cancellation_messages_route_to_appointment(message):
    assert RuleBasedRouter().route(message) == AgentRoute.APPOINTMENT


@pytest.mark.parametrize(
    "message",
    [
        "reschedule my appointment to Friday",
        "reschedule APT-001",
        "please reschedule me to 18:30",
    ],
)
def test_reschedule_messages_route_to_appointment(message):
    assert RuleBasedRouter().route(message) == AgentRoute.APPOINTMENT


@pytest.mark.parametrize(
    "message",
    [
        "Is DOC-001 available on 2026-08-16 at 17:00?",
        "is Dr. Ahmed free on Sunday?",
        "check availability for DOC-002",
        "any slot on Sunday?",
    ],
)
def test_availability_messages_route_to_appointment(message):
    assert RuleBasedRouter().route(message) == AgentRoute.APPOINTMENT


# ---------------------------------------------------------------------------
# 5-8: knowledge-side routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "who is Dr. Ahmed?",
        "tell me about Dr. Sara",
        "who is DOC-004?",
    ],
)
def test_doctor_information_routes_to_knowledge(message):
    assert RuleBasedRouter().route(message) == AgentRoute.KNOWLEDGE


@pytest.mark.parametrize(
    "message",
    [
        "what is Dr. Ahmed's specialization?",
        "what specialty does Dr. Sara have?",
        "which dermatologist do you have?",
        "who does cardiology?",
    ],
)
def test_specialization_questions_route_to_knowledge(message):
    assert RuleBasedRouter().route(message) == AgentRoute.KNOWLEDGE


@pytest.mark.parametrize(
    "message",
    [
        "what is the cancellation policy?",
        "what is the walk-in policy?",
        "what are the clinic hours?",
        "how do I book an appointment?",
        "how does rescheduling work?",
    ],
)
def test_clinic_policy_questions_route_to_knowledge(message):
    assert RuleBasedRouter().route(message) == AgentRoute.KNOWLEDGE


@pytest.mark.parametrize(
    "message",
    [
        "what services does Dr. Sara provide?",
        "what languages does Dr. Ahmed speak?",
        "what is Dr. Ahmed's consultation fee?",
        "what qualifications does Dr. Sara have?",
    ],
)
def test_faq_style_questions_route_to_knowledge(message):
    assert RuleBasedRouter().route(message) == AgentRoute.KNOWLEDGE


# ---------------------------------------------------------------------------
# 9: unsupported
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "what's the weather in Karachi?",
        "tell me a joke",
        "who won the cricket match?",
        "please add 2 + 2",
        "random unrelated request",
    ],
)
def test_unrelated_messages_route_to_unsupported(message):
    assert RuleBasedRouter().route(message) == AgentRoute.UNSUPPORTED


def test_empty_message_routes_to_unsupported():
    assert RuleBasedRouter().route("") == AgentRoute.UNSUPPORTED
    assert RuleBasedRouter().route("   \n\t") == AgentRoute.UNSUPPORTED


def test_non_string_message_routes_to_unsupported():
    assert RuleBasedRouter().route(None) == AgentRoute.UNSUPPORTED  # type: ignore[arg-type]
    assert RuleBasedRouter().route(42) == AgentRoute.UNSUPPORTED  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 10: mixed booking request → APPOINTMENT
# ---------------------------------------------------------------------------


def test_mixed_booking_request_prefers_appointment():
    """From the brief: 'I want to book Dr. Ahmed for Sunday at 5 PM'
    → APPOINTMENT even though it names a doctor."""
    r = RuleBasedRouter()
    assert (
        r.route("I want to book Dr. Ahmed for Sunday at 5 PM")
        == AgentRoute.APPOINTMENT
    )


def test_meta_book_question_still_routes_to_knowledge():
    """'How do I book' asks ABOUT booking — knowledge, not action."""
    r = RuleBasedRouter()
    assert r.route("how do I book an appointment?") == AgentRoute.KNOWLEDGE


def test_meta_cancellation_policy_still_routes_to_knowledge():
    """'Cancellation policy' contains 'cancel' — but it's a knowledge
    question about the policy, not a cancel action."""
    r = RuleBasedRouter()
    assert r.route("what is the cancellation policy?") == AgentRoute.KNOWLEDGE


def test_meta_availability_stays_appointment():
    """A meta wrapper around availability still routes to appointment
    because only the appointment system can answer definitively."""
    r = RuleBasedRouter()
    # "which doctor is available Sunday at 5?" — meta + availability
    # signal → appointment.
    assert (
        r.route("which doctor is available Sunday at 5?")
        == AgentRoute.APPOINTMENT
    )


# ---------------------------------------------------------------------------
# 11-12: Groq router — malformed / invalid safe fallback
# ---------------------------------------------------------------------------


def test_groq_valid_response_is_parsed_into_route():
    fake = MagicMock(return_value=_fake_groq_response('{"agent": "knowledge"}'))
    router = _make_groq(fake)
    assert router.route("who is Dr. Ahmed?") == AgentRoute.KNOWLEDGE
    assert fake.call_count == 1


def test_groq_sends_router_system_prompt_and_user_message():
    fake = MagicMock(return_value=_fake_groq_response('{"agent": "appointment"}'))
    router = _make_groq(fake)
    router.route("book Dr. Ahmed for Sunday")

    payload = fake.call_args.args[0]
    system = next(m["content"] for m in payload["messages"] if m["role"] == "system")
    user = next(m["content"] for m in payload["messages"] if m["role"] == "user")
    assert system == _ROUTER_SYSTEM_PROMPT
    assert user == "book Dr. Ahmed for Sunday"


def test_groq_malformed_json_falls_back_to_rule_based():
    fake = MagicMock(return_value=_fake_groq_response("not valid json"))
    # A knowledge-style message should be classified by the fallback
    # RuleBasedRouter as KNOWLEDGE.
    router = _make_groq(fake)
    assert router.route("who is Dr. Ahmed?") == AgentRoute.KNOWLEDGE


def test_groq_invalid_agent_value_falls_back_to_rule_based():
    fake = MagicMock(return_value=_fake_groq_response('{"agent": "spaghetti"}'))
    router = _make_groq(fake)
    # A booking message must still land on APPOINTMENT via the fallback.
    assert router.route("book an appointment") == AgentRoute.APPOINTMENT


def test_groq_missing_agent_key_falls_back_to_rule_based():
    fake = MagicMock(return_value=_fake_groq_response('{"other": "knowledge"}'))
    router = _make_groq(fake)
    assert router.route("who is Dr. Ahmed?") == AgentRoute.KNOWLEDGE


def test_groq_http_failure_falls_back_to_rule_based():
    def _raising(payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("simulated network failure")

    router = _make_groq(_raising)
    assert router.route("cancel APT-001") == AgentRoute.APPOINTMENT


def test_groq_unexpected_choices_shape_falls_back():
    fake = MagicMock(return_value={"choices": []})
    router = _make_groq(fake)
    assert router.route("book an appointment") == AgentRoute.APPOINTMENT


def test_groq_uses_supplied_custom_fallback():
    """A caller can inject a stub fallback to prove the plumbing."""
    stub_calls: list[str] = []

    class StubFallback(Router):
        def route(self, message: str) -> AgentRoute:
            stub_calls.append(message)
            return AgentRoute.UNSUPPORTED

    fake = MagicMock(return_value=_fake_groq_response("not valid json"))
    router = _make_groq(fake, fallback=StubFallback())
    assert router.route("anything") == AgentRoute.UNSUPPORTED
    assert stub_calls == ["anything"]


def test_groq_rejects_empty_api_key():
    with pytest.raises(ValueError, match="non-empty"):
        GroqRouter(api_key="")


def test_groq_empty_message_short_circuits_without_http_call():
    fake = MagicMock()
    router = _make_groq(fake)
    assert router.route("") == AgentRoute.UNSUPPORTED
    assert router.route("   ") == AgentRoute.UNSUPPORTED
    assert fake.call_count == 0


# ---------------------------------------------------------------------------
# 13: rule-based determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message,expected",
    [
        ("book an appointment", AgentRoute.APPOINTMENT),
        ("who is Dr. Ahmed?", AgentRoute.KNOWLEDGE),
        ("what's the weather?", AgentRoute.UNSUPPORTED),
    ],
)
def test_rule_based_router_is_deterministic(message, expected):
    r = RuleBasedRouter()
    first = r.route(message)
    second = r.route(message)
    third = r.route(message)
    assert first == second == third == expected


def test_rule_based_router_returns_enum_values():
    """Prevents an accidental refactor from returning bare strings."""
    r = RuleBasedRouter()
    assert isinstance(r.route("book an appointment"), AgentRoute)
    assert isinstance(r.route("who is Dr. Ahmed?"), AgentRoute)
    assert isinstance(r.route("what's the weather?"), AgentRoute)


# ---------------------------------------------------------------------------
# Structural / safety
# ---------------------------------------------------------------------------


def test_router_source_does_not_touch_appointment_infrastructure():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "app" / "agents" / "router.py").read_text(
        encoding="utf-8"
    )
    for banned in (
        "openpyxl",
        "pandas",
        "repositor",
        ".xlsx",
        "AppointmentService",
        "AppointmentTools",
    ):
        assert banned.lower() not in src.lower(), (
            f"router.py must not touch appointment infrastructure; found {banned}"
        )


def test_agent_route_enum_values():
    """Regression pin for the frontend / API contract if we ever
    surface the route name as data."""
    assert AgentRoute.APPOINTMENT.value == "appointment"
    assert AgentRoute.KNOWLEDGE.value == "knowledge"
    assert AgentRoute.UNSUPPORTED.value == "unsupported"


def test_rule_based_is_a_router():
    assert isinstance(RuleBasedRouter(), Router)


def test_groq_is_a_router():
    assert isinstance(_make_groq(MagicMock()), Router)
