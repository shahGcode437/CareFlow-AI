"""Phase 9.7 tests — natural-language booking field extraction.

Before this phase, RuleBasedIntentProvider could only pull
appointment_id/doctor_id/date/time out of free text (see the
"WHAT RuleBasedIntentProvider CAN AND CANNOT DO" note in
app/agents/llm_provider.py's module docstring). A complete,
conversational booking message that also stated the patient's name,
phone, and requested service in prose was therefore always rejected
with a missing-fields prompt, even though a human reading the same
sentence could plainly see all the information was there.

This module verifies the new patient_name/patient_phone/service
extraction: it should resolve clearly-anchored natural-language
phrasing (see llm_provider._PATIENT_NAME_RE / _PHONE_RE / _SERVICE_RE
for the exact patterns), while leaving genuinely ambiguous or absent
information to the existing missing-fields flow unchanged.
"""

from __future__ import annotations

from app.agents.llm_provider import (
    NeedsInfoDecision,
    RuleBasedIntentProvider,
    ToolCallDecision,
    _extract_from_message,
)


# ---------------------------------------------------------------------------
# The exact reported bug, end to end
# ---------------------------------------------------------------------------


def test_complete_natural_language_booking_message_creates_appointment():
    """The exact bug report. All seven fields must resolve from one
    message and the provider must proceed straight to
    create_appointment — no missing-fields prompt at all."""
    provider = RuleBasedIntentProvider()
    message = (
        "I want to book an appointment with Dr. Ahmed on 2026-08-16 at "
        "17:30. My name is Ali Khan, my phone number is 03001234567, "
        "and I need a General Consultation."
    )
    decision = provider.decide(message)
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "create_appointment"
    assert decision.arguments == {
        "patient_name": "Ali Khan",
        "patient_phone": "03001234567",
        "doctor_id": "DOC-001",
        "doctor_name": "Dr. Ahmed",
        "service": "General Consultation",
        "appointment_date": "2026-08-16",
        "appointment_time": "17:30",
    }


# ---------------------------------------------------------------------------
# Field-level extraction — each supported phrasing
# ---------------------------------------------------------------------------


def test_patient_name_phrasing_variants():
    assert _extract_from_message("My name is Ali Khan")["patient_name"] == "Ali Khan"
    assert _extract_from_message("I'm Ali Khan")["patient_name"] == "Ali Khan"
    assert _extract_from_message("I am Ali Khan")["patient_name"] == "Ali Khan"
    assert (
        _extract_from_message("patient name is Ali Khan")["patient_name"] == "Ali Khan"
    )
    assert (
        _extract_from_message("book an appointment for Ali Khan")["patient_name"]
        == "Ali Khan"
    )


def test_patient_phone_phrasing_variants():
    assert (
        _extract_from_message("my phone number is 03001234567")["patient_phone"]
        == "03001234567"
    )
    assert (
        _extract_from_message("my number is 03001234567")["patient_phone"]
        == "03001234567"
    )
    assert _extract_from_message("phone: 03001234567")["patient_phone"] == "03001234567"


def test_service_phrasing_variants():
    assert (
        _extract_from_message("I need a General Consultation")["service"]
        == "General Consultation"
    )
    assert (
        _extract_from_message("I'd like a Dermatology Consultation")["service"]
        == "Dermatology Consultation"
    )
    assert (
        _extract_from_message("service is Cardiology Consultation")["service"]
        == "Cardiology Consultation"
    )


def test_service_extraction_does_not_bleed_into_trailing_sentence_text():
    """Regression pin for the "avoid accidentally extracting trailing
    sentence text" requirement: the service must stop at the sentence
    boundary, not swallow what comes after it."""
    extracted = _extract_from_message(
        "I need a General Consultation and I also have a question about parking."
    )
    assert extracted["service"] == "General Consultation"


def test_patient_name_extraction_does_not_bleed_into_trailing_sentence_text():
    extracted = _extract_from_message(
        "My name is Ali Khan and I need a General Consultation."
    )
    assert extracted["patient_name"] == "Ali Khan"


# ---------------------------------------------------------------------------
# "for <X>" fallback must not misread a doctor reference as the
# patient's name
# ---------------------------------------------------------------------------


def test_for_fallback_does_not_capture_a_doctor_reference_as_patient_name():
    assert "patient_name" not in _extract_from_message("book an appointment for Dr. Ahmed")
    assert "patient_name" not in _extract_from_message("book an appointment for Ahmed")
    assert "patient_name" not in _extract_from_message(
        "book an appointment for Doctor Ahmed"
    )
    assert "patient_name" not in _extract_from_message(
        "book an appointment for Hassan Ali"
    )


def test_for_fallback_still_captures_a_real_patient_name():
    extracted = _extract_from_message(
        "book an appointment for Sana Malik with Dr. Sara"
    )
    assert extracted["patient_name"] == "Sana Malik"


def test_stronger_name_pattern_takes_priority_over_for_fallback():
    """When both an explicit "my name is" phrase and an unrelated
    "for" phrase are present, the explicit phrase wins."""
    extracted = _extract_from_message(
        "My name is Ali Khan, book this for Dr. Ahmed"
    )
    assert extracted["patient_name"] == "Ali Khan"


# ---------------------------------------------------------------------------
# Explicit context / identifiers still take priority — no regression
# ---------------------------------------------------------------------------


def test_explicit_context_patient_fields_override_extraction():
    """Per the existing decide() contract, `context` always wins over
    anything extracted from the message text."""
    provider = RuleBasedIntentProvider()
    message = (
        "I want to book an appointment with Dr. Ahmed on 2026-08-16 at "
        "17:30. My name is Ali Khan, my phone number is 03001234567, "
        "and I need a General Consultation."
    )
    decision = provider.decide(
        message,
        context={"patient_name": "Zara Khan", "patient_phone": "03009998888"},
    )
    assert isinstance(decision, ToolCallDecision)
    assert decision.arguments["patient_name"] == "Zara Khan"
    assert decision.arguments["patient_phone"] == "03009998888"
    assert decision.arguments["service"] == "General Consultation"


def test_explicit_doctor_id_still_wins_with_natural_language_patient_fields():
    """Explicit DOC-XXX must never be second-guessed, even when the
    same message also contains a natural-language doctor mention and
    fully-extractable patient fields."""
    provider = RuleBasedIntentProvider()
    decision = provider.decide(
        "Book DOC-002 (not Dr. Ahmed) on 2026-08-16 at 17:30. My name is "
        "Ali Khan, my phone number is 03001234567, and I need a General "
        "Consultation."
    )
    assert isinstance(decision, ToolCallDecision)
    assert decision.arguments["doctor_id"] == "DOC-002"


# ---------------------------------------------------------------------------
# Unrelated flows must be completely unaffected
# ---------------------------------------------------------------------------


def test_availability_request_is_unaffected_by_new_extraction():
    provider = RuleBasedIntentProvider()
    decision = provider.decide("Is Dr. Ahmed available on 2026-08-16 at 17:30?")
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "check_availability"
    assert "patient_name" not in decision.arguments
    assert "patient_phone" not in decision.arguments


def test_missing_fields_still_reported_when_genuinely_absent():
    """No name/phone/service anchor anywhere in the message — the
    existing missing-fields prompt must still fire exactly as before."""
    provider = RuleBasedIntentProvider()
    decision = provider.decide(
        "book an appointment with Dr. Ahmed on 2026-08-16 at 17:30"
    )
    assert isinstance(decision, NeedsInfoDecision)
    assert set(decision.missing_fields) == {"patient_name", "patient_phone", "service"}


def test_partial_natural_language_still_reports_only_the_truly_missing_fields():
    provider = RuleBasedIntentProvider()
    decision = provider.decide(
        "book an appointment with Dr. Ahmed on 2026-08-16 at 17:30, my "
        "name is Ali Khan"
    )
    assert isinstance(decision, NeedsInfoDecision)
    assert set(decision.missing_fields) == {"patient_phone", "service"}
