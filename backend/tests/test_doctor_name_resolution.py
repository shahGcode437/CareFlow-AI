"""Phase 9.6 tests — patient-facing doctor name resolution.

The patient-facing assistant should never require internal
"DOC-XXX" identifiers. This module verifies:

  * natural-language doctor references ("Dr. Ahmed", "Ahmed",
    "Dr Ahmed") resolve to the correct internal doctor_id
  * explicit "DOC-XXX" ids continue to work unchanged (zero
    regression) and always take priority over name matching
  * ambiguous / unknown doctor names produce an honest clarification
    request rather than a guess
  * the resolved doctor_id flows into the existing appointment tools
    unchanged (no new appointment system, no duplicated availability
    logic)
  * patient-facing responses prefer the doctor's name over the raw id

All tests are offline (no network, no Excel mutation) and follow this
project's existing testing conventions (see test_llm_integration.py).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agents.appointment_agent import AppointmentAgent
from app.agents.doctor_resolver import (
    DoctorNameResolution,
    doctor_name_for_id,
    resolve_doctor_by_name,
)
from app.agents.llm_provider import (
    NeedsInfoDecision,
    RuleBasedIntentProvider,
    ToolCallDecision,
)
from app.rag.entity_filter import CLINIC_DOCTORS, DoctorEntity
from app.tools.appointment_tools import AppointmentTools
from app.tools.tool_result import ToolResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_tools() -> MagicMock:
    return MagicMock(spec=AppointmentTools)


def _availability_result(doctor_id: str = "DOC-001", available: bool = True) -> ToolResult:
    return ToolResult.ok(
        {
            "available": available,
            "doctor_id": doctor_id,
            "appointment_date": "2026-08-16",
            "appointment_time": "17:30:00",
            "message": "The requested slot is available."
            if available
            else "The requested slot is already booked.",
        }
    )


# ---------------------------------------------------------------------------
# 1-3: natural-language doctor phrasing variants -> resolved to DOC-001
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "Is Dr. Ahmed available on 2026-08-16 at 17:30?",
        "Is Ahmed available on 2026-08-16 at 17:30?",
        "Is Dr Ahmed available on 2026-08-16 at 17:30?",
        "Is doctor Ahmed available on 2026-08-16 at 17:30?",
    ],
)
def test_doctor_name_phrasing_variants_resolve_to_doc_001(message):
    provider = RuleBasedIntentProvider()
    decision = provider.decide(message)
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "check_availability"
    assert decision.arguments["doctor_id"] == "DOC-001"


# ---------------------------------------------------------------------------
# 4: existing "DOC-001" queries continue working unchanged
# ---------------------------------------------------------------------------


def test_explicit_doctor_id_query_still_works_unchanged():
    provider = RuleBasedIntentProvider()
    decision = provider.decide("Is DOC-001 available on 2026-08-16 at 17:30?")
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "check_availability"
    assert decision.arguments["doctor_id"] == "DOC-001"
    assert decision.arguments["appointment_date"] == "2026-08-16"
    assert decision.arguments["appointment_time"] == "17:30"


def test_explicit_doctor_id_always_wins_over_a_conflicting_name_mention():
    """If a message somehow contains both an explicit id and a name,
    the literal id must never be second-guessed by name matching."""
    provider = RuleBasedIntentProvider()
    decision = provider.decide(
        "Book with Dr. Ahmed (DOC-002) for General Consultation on "
        "2026-08-16 at 17:30",
        context={
            "patient_name": "Zara Khan",
            "patient_phone": "03001234567",
            "service": "General Consultation",
        },
    )
    assert isinstance(decision, ToolCallDecision)
    # The explicit "DOC-002" token wins even though "Dr. Ahmed" (DOC-001)
    # also appears in the same sentence.
    assert decision.arguments["doctor_id"] == "DOC-002"


# ---------------------------------------------------------------------------
# 5: booking using a doctor name
# ---------------------------------------------------------------------------


def test_booking_by_doctor_name_resolves_id_and_name(mock_tools):
    mock_tools.create_appointment.return_value = ToolResult.ok(
        {
            "appointment_id": "APT-NEW01",
            "patient_name": "Zara Khan",
            "patient_phone": "03001234567",
            "doctor_id": "DOC-001",
            "doctor_name": "Dr. Ahmed",
            "service": "General Consultation",
            "appointment_date": "2026-08-16",
            "appointment_time": "17:30:00",
            "status": "Pending",
            "created_at": "2026-08-16T10:00:00",
            "updated_at": "2026-08-16T10:00:00",
            "notes": None,
        }
    )
    agent = AppointmentAgent(RuleBasedIntentProvider(), mock_tools)
    response = agent.handle(
        "Book an appointment with Dr. Ahmed on 2026-08-16 at 17:30",
        context={
            "patient_name": "Zara Khan",
            "patient_phone": "03001234567",
            "service": "General Consultation",
        },
    )
    assert response.intent == "create_appointment"
    mock_tools.create_appointment.assert_called_once()
    call_kwargs = mock_tools.create_appointment.call_args.kwargs
    assert call_kwargs["doctor_id"] == "DOC-001"
    assert call_kwargs["doctor_name"] == "Dr. Ahmed"


def test_explicit_doctor_id_booking_now_backfills_doctor_name(mock_tools):
    """Previously, booking via a literal 'DOC-001' still failed with
    'missing: doctor_name' because nothing populated it. Phase 9.6
    backfills doctor_name from the registry whenever doctor_id is
    already known — this is a genuine fix, not just a name-matching
    addition."""
    mock_tools.create_appointment.return_value = ToolResult.ok(
        {
            "appointment_id": "APT-NEW02",
            "patient_name": "Zara Khan",
            "patient_phone": "03001234567",
            "doctor_id": "DOC-001",
            "doctor_name": "Dr. Ahmed",
            "service": "General Consultation",
            "appointment_date": "2026-08-16",
            "appointment_time": "17:30:00",
            "status": "Pending",
            "created_at": "2026-08-16T10:00:00",
            "updated_at": "2026-08-16T10:00:00",
            "notes": None,
        }
    )
    agent = AppointmentAgent(RuleBasedIntentProvider(), mock_tools)
    response = agent.handle(
        "Book an appointment with DOC-001 on 2026-08-16 at 17:30",
        context={
            "patient_name": "Zara Khan",
            "patient_phone": "03001234567",
            "service": "General Consultation",
        },
    )
    assert response.intent == "create_appointment"
    call_kwargs = mock_tools.create_appointment.call_args.kwargs
    assert call_kwargs["doctor_id"] == "DOC-001"
    assert call_kwargs["doctor_name"] == "Dr. Ahmed"


# ---------------------------------------------------------------------------
# 6: alternative-slot query using a doctor name
# ---------------------------------------------------------------------------


def test_alternative_slots_query_by_doctor_name(mock_tools):
    mock_tools.find_alternative_slots.return_value = ToolResult.ok(
        {
            "requested_slot_available": False,
            "alternatives": [
                {
                    "doctor_id": "DOC-001",
                    "doctor_name": "Dr. Ahmed",
                    "appointment_date": "2026-08-16",
                    "appointment_time": "18:00:00",
                }
            ],
        }
    )
    agent = AppointmentAgent(RuleBasedIntentProvider(), mock_tools)
    response = agent.handle(
        "Find alternative slots with Dr. Ahmed on 2026-08-16 at 17:00"
    )
    assert response.intent == "find_alternative_slots"
    mock_tools.find_alternative_slots.assert_called_once()
    call_kwargs = mock_tools.find_alternative_slots.call_args.kwargs
    assert call_kwargs["doctor_id"] == "DOC-001"


# ---------------------------------------------------------------------------
# 7: unknown doctor name
# ---------------------------------------------------------------------------


def test_unknown_doctor_name_asks_for_clarification_not_a_guess():
    provider = RuleBasedIntentProvider()
    decision = provider.decide("Is Dr. Watson available on 2026-08-16 at 17:30?")
    assert isinstance(decision, NeedsInfoDecision)
    assert decision.missing_fields == ["doctor_id"]
    assert "Watson" in decision.message
    assert "couldn't find" in decision.message.lower()


def test_unknown_doctor_name_message_does_not_swallow_trailing_words():
    """Regression pin: the name-extraction regex can capture up to two
    words after 'Dr.'; a sentence-continuation word ('available',
    'today', ...) must not be folded into the displayed name."""
    provider = RuleBasedIntentProvider()
    decision = provider.decide("Is Dr. Watson available today?")
    assert isinstance(decision, NeedsInfoDecision)
    assert "Watson" in decision.message
    assert "available" not in decision.message.split("named")[-1].split(".")[0].lower()


# ---------------------------------------------------------------------------
# 8: ambiguous doctor name
# ---------------------------------------------------------------------------


_AMBIGUOUS_REGISTRY: tuple[DoctorEntity, ...] = (
    DoctorEntity(doctor_id="DOC-101", name="Dr. Ahmed Khan", tokens=("ahmed khan", "ahmed")),
    DoctorEntity(doctor_id="DOC-102", name="Dr. Ahmed Malik", tokens=("ahmed malik", "ahmed")),
)


def test_ambiguous_doctor_name_asks_for_clarification():
    provider = RuleBasedIntentProvider(doctor_registry=_AMBIGUOUS_REGISTRY)
    decision = provider.decide("Is Dr. Ahmed available on 2026-08-16 at 17:30?")
    assert isinstance(decision, NeedsInfoDecision)
    assert decision.missing_fields == ["doctor_id"]
    assert "more than one doctor" in decision.message.lower()
    assert "Dr. Ahmed Khan" in decision.message
    assert "Dr. Ahmed Malik" in decision.message


def test_resolve_doctor_by_name_ambiguous_result_shape():
    resolution = resolve_doctor_by_name(
        "Is Dr. Ahmed available?", registry=_AMBIGUOUS_REGISTRY
    )
    assert resolution.is_ambiguous
    assert not resolution.is_resolved
    assert not resolution.is_unknown
    assert resolution.ambiguous_candidates == ("Dr. Ahmed Khan", "Dr. Ahmed Malik")


def test_ambiguous_doctor_name_on_optional_field_does_not_block_reschedule():
    """update_appointment's doctor_id is OPTIONAL — an ambiguous
    incidental doctor mention must not block a reschedule that doesn't
    strictly require a doctor to be identified."""
    provider = RuleBasedIntentProvider(doctor_registry=_AMBIGUOUS_REGISTRY)
    decision = provider.decide(
        "reschedule APT-001 to 2026-08-20 at 17:00, mentioning Dr. Ahmed"
    )
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "update_appointment"
    assert "doctor_id" not in decision.arguments


# ---------------------------------------------------------------------------
# 9: patient-facing response should not unnecessarily expose DOC-001
# ---------------------------------------------------------------------------


def test_check_availability_response_names_the_doctor_not_the_id(mock_tools):
    mock_tools.check_availability.return_value = _availability_result(
        doctor_id="DOC-001", available=True
    )
    agent = AppointmentAgent(RuleBasedIntentProvider(), mock_tools)
    response = agent.handle("Is Dr. Ahmed available on 2026-08-16 at 17:30?")
    assert "Dr. Ahmed" in response.message
    assert "DOC-001" not in response.message


def test_check_availability_response_via_explicit_id_also_names_the_doctor(mock_tools):
    """Even when the PATIENT typed the raw id, the assistant's reply
    should still speak in terms of the doctor's name."""
    mock_tools.check_availability.return_value = _availability_result(
        doctor_id="DOC-001", available=False
    )
    agent = AppointmentAgent(RuleBasedIntentProvider(), mock_tools)
    response = agent.handle("Is DOC-001 available on 2026-08-16 at 17:30?")
    assert "Dr. Ahmed" in response.message
    assert "DOC-001" not in response.message


# ---------------------------------------------------------------------------
# doctor_resolver unit tests
# ---------------------------------------------------------------------------


def test_resolve_doctor_by_name_returns_none_when_no_doctor_mentioned():
    resolution = resolve_doctor_by_name("What time does the clinic open?")
    assert resolution == DoctorNameResolution()
    assert not resolution.is_resolved
    assert not resolution.is_ambiguous
    assert not resolution.is_unknown


def test_resolve_doctor_by_name_is_case_insensitive():
    for text in ("dr. ahmed", "DR AHMED", "Doctor Ahmed", "AHMED"):
        resolution = resolve_doctor_by_name(f"Is {text} available?")
        assert resolution.is_resolved, f"failed for: {text!r}"
        assert resolution.doctor_id == "DOC-001"
        assert resolution.doctor_name == "Dr. Ahmed"


def test_resolve_doctor_by_name_sara_resolves_to_doc_002():
    resolution = resolve_doctor_by_name("Is Dr. Sara available on Sunday?")
    assert resolution.doctor_id == "DOC-002"
    assert resolution.doctor_name == "Dr. Sara"


def test_doctor_name_for_id_known_and_unknown():
    assert doctor_name_for_id("DOC-001") == "Dr. Ahmed"
    assert doctor_name_for_id("DOC-002") == "Dr. Sara"
    assert doctor_name_for_id("DOC-999") is None


def test_all_twelve_clinic_doctors_resolve_by_bare_surname():
    """Every doctor in the shared registry (not just the two
    Excel-backed ones) should resolve — the resolver's job is name ->
    id mapping; whether the id is actually bookable is the
    AppointmentService's job downstream."""
    for doctor in CLINIC_DOCTORS:
        surname_token = doctor.tokens[-1]
        resolution = resolve_doctor_by_name(f"Tell me about Dr. {surname_token}")
        assert resolution.doctor_id == doctor.doctor_id, (
            f"expected {doctor.doctor_id} for token {surname_token!r}, "
            f"got {resolution.doctor_id!r}"
        )


def test_demo_only_doctor_name_resolves_but_service_layer_remains_authoritative(
    mock_tools,
):
    """DOC-003 is a demo-only doctor (not in the Excel workbook). Name
    resolution must still succeed (we don't invent a doctor, we just
    map the name the registry already knows) — but the actual
    DOCTOR_NOT_FOUND rejection is the AppointmentService's call, not
    something this feature second-guesses."""
    mock_tools.check_availability.return_value = ToolResult.fail(
        "DOCTOR_NOT_FOUND", "Doctor not found."
    )
    agent = AppointmentAgent(RuleBasedIntentProvider(), mock_tools)
    response = agent.handle(
        "Is Dr. Bilal Iqbal available on 2026-08-16 at 17:30?"
    )
    mock_tools.check_availability.assert_called_once()
    call_kwargs = mock_tools.check_availability.call_args.kwargs
    assert call_kwargs["doctor_id"] == "DOC-003"
    # The service's own honest rejection is surfaced unchanged.
    assert "couldn't find that doctor" in response.message.lower()


# ---------------------------------------------------------------------------
# Architectural guard: no new dependency, no duplicated appointment system
# ---------------------------------------------------------------------------


def test_doctor_resolver_module_does_not_touch_excel_or_service_layer():
    import inspect

    import app.agents.doctor_resolver as module

    import_lines = [
        line.strip()
        for line in inspect.getsource(module).splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    forbidden = ["openpyxl", "pandas", "app.repositories", "app.services"]
    for token in forbidden:
        offending = [line for line in import_lines if token in line]
        assert not offending, f"doctor_resolver.py must not import '{token}': {offending}"
