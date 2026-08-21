"""Phase 9.8 tests — natural-language find_alternative_slots intent.

CareFlow already had the find_alternative_slots tool and an
find_alternative_slots entry in RuleBasedIntentProvider._INTENT_RULES,
but two natural-language phrasings still failed to reach it:

  1. RuleBasedRouter had no signal at all for "alternative" — messages
     like "Find alternative slots for Dr. Ahmed..." were classified
     AgentRoute.UNSUPPORTED before ever reaching AppointmentAgent /
     RuleBasedIntentProvider, which would have handled them correctly.
  2. _INTENT_RULES' "another time" keyword required a contiguous
     substring match, so "another available time" (with "available"
     inserted) fell through to check_availability's "available"
     keyword instead of find_alternative_slots.

This module pins both fixes and the five natural-language variants
from the bug report, plus a regression check that every other route
(availability, create, update, cancel, approve/reject, get_appointment,
knowledge, unsupported) is unaffected.
"""

from __future__ import annotations

from app.agents.llm_provider import NeedsInfoDecision, RuleBasedIntentProvider, ToolCallDecision
from app.agents.router import AgentRoute, RuleBasedRouter


# ---------------------------------------------------------------------------
# The exact reported bug, end to end (router + intent provider)
# ---------------------------------------------------------------------------


def test_find_alternative_slots_message_is_routed_to_appointment():
    router = RuleBasedRouter()
    assert (
        router.route("Find alternative slots for Dr. Ahmed on 2026-08-16 at 17:30.")
        == AgentRoute.APPOINTMENT
    )


def test_find_alternative_slots_message_resolves_to_the_tool():
    provider = RuleBasedIntentProvider()
    decision = provider.decide(
        "Find alternative slots for Dr. Ahmed on 2026-08-16 at 17:30."
    )
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "find_alternative_slots"
    assert decision.arguments == {
        "doctor_id": "DOC-001",
        "appointment_date": "2026-08-16",
        "appointment_time": "17:30",
    }


# ---------------------------------------------------------------------------
# The five required natural-language variants — router must not block
# them, and when the tool has everything it needs it must be
# find_alternative_slots (never check_availability, never unsupported).
# ---------------------------------------------------------------------------

_VARIANTS_WITH_DATE_TIME = [
    "Find alternative slots for Dr. Ahmed on 2026-08-16 at 17:30.",
    "Please find alternative slots for Dr. Ahmed on 2026-08-16 at 17:30.",
    "Look for alternative times for Dr. Ahmed on 2026-08-16 at 17:30.",
    "Can you find another available time for Dr. Ahmed on 2026-08-16 at 17:30?",
    "What other slots are available for Dr. Ahmed on 2026-08-16 at 17:30?",
]


def test_all_five_variants_route_to_appointment():
    router = RuleBasedRouter()
    for message in _VARIANTS_WITH_DATE_TIME:
        assert router.route(message) == AgentRoute.APPOINTMENT, message


def test_all_five_variants_resolve_to_find_alternative_slots():
    provider = RuleBasedIntentProvider()
    for message in _VARIANTS_WITH_DATE_TIME:
        decision = provider.decide(message)
        assert isinstance(decision, ToolCallDecision), message
        assert decision.tool_name == "find_alternative_slots", message
        assert decision.arguments["doctor_id"] == "DOC-001", message


def test_variants_without_date_or_time_ask_for_exactly_what_is_missing():
    """The originally-reported variants that omit date/time (no
    conversation memory required by this fix) must still correctly
    identify find_alternative_slots as the intent and ask only for the
    genuinely missing fields — not be misrouted or rejected outright."""
    provider = RuleBasedIntentProvider()

    decision = provider.decide("Look for alternative times for Dr. Ahmed.")
    assert isinstance(decision, NeedsInfoDecision)
    assert set(decision.missing_fields) == {"appointment_date", "appointment_time"}

    decision = provider.decide("Please find alternative slots for Dr. Ahmed around 17:30.")
    assert isinstance(decision, NeedsInfoDecision)
    assert set(decision.missing_fields) == {"appointment_date"}


# ---------------------------------------------------------------------------
# Regression pin: "another available time" must not be misread as
# check_availability just because "available" also appears there.
# ---------------------------------------------------------------------------


def test_another_available_time_is_not_misclassified_as_check_availability():
    provider = RuleBasedIntentProvider()
    decision = provider.decide(
        "Can you find another available time for Dr. Ahmed on 2026-08-16 at 17:30?"
    )
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "find_alternative_slots"


# ---------------------------------------------------------------------------
# No regression: every other route and intent stays exactly as before.
# ---------------------------------------------------------------------------


def test_plain_availability_request_is_unaffected():
    router = RuleBasedRouter()
    provider = RuleBasedIntentProvider()
    message = "Is Dr. Ahmed available on 2026-08-16 at 17:30?"
    assert router.route(message) == AgentRoute.APPOINTMENT
    decision = provider.decide(message)
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "check_availability"


def test_create_appointment_is_unaffected():
    provider = RuleBasedIntentProvider()
    message = (
        "book an appointment with Dr. Ahmed on 2026-08-16 at 17:30, my name "
        "is Ali Khan, my phone number is 03001234567, and I need a General "
        "Consultation."
    )
    decision = provider.decide(message)
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "create_appointment"


def test_update_reschedule_is_unaffected():
    provider = RuleBasedIntentProvider()
    decision = provider.decide("reschedule APT-001 to 2026-08-20 at 17:00")
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "update_appointment"


def test_cancel_is_unaffected():
    provider = RuleBasedIntentProvider()
    decision = provider.decide("cancel APT-001")
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "cancel_appointment"


def test_get_appointment_is_unaffected():
    provider = RuleBasedIntentProvider()
    decision = provider.decide("check my appointment APT-001")
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "get_appointment"


def test_knowledge_questions_still_route_to_knowledge():
    router = RuleBasedRouter()
    assert router.route("What is the cancellation policy?") == AgentRoute.KNOWLEDGE
    assert router.route("Which dermatologist do you have?") == AgentRoute.KNOWLEDGE


def test_genuinely_unsupported_requests_still_unsupported():
    router = RuleBasedRouter()
    assert router.route("What is the weather today?") == AgentRoute.UNSUPPORTED
    assert router.route("tell me a joke") == AgentRoute.UNSUPPORTED
