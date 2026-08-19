"""Phase 7.1 tests — real LLM provider integration.

The HTTP call inside GroqLLMProvider is fully injectable (`http_post`),
so every test here supplies a fake function returning canned JSON —
no network access and no real API key is used or required anywhere in
this file.
"""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.agents.appointment_agent import AppointmentAgent
from app.agents.llm_provider import (
    GroqLLMProvider,
    LLMDecisionEnvelope,
    NeedsInfoDecision,
    NotApplicableDecision,
    RuleBasedIntentProvider,
    ToolCallDecision,
)
from app.tools.appointment_tools import AppointmentTools
from app.tools.tool_result import ToolResult


def _fake_groq_response(content_json: str) -> dict:
    """Shape of a real Groq/OpenAI-compatible chat completion response."""
    return {"choices": [{"message": {"content": content_json}}]}


def _make_provider(http_post) -> GroqLLMProvider:
    return GroqLLMProvider(api_key="test-key-not-real", http_post=http_post)


# --- 1. Valid model response -> expected structured decision --------------------

def test_valid_tool_call_response_transforms_correctly():
    fake_post = MagicMock(
        return_value=_fake_groq_response(
            '{"status": "tool_call", "tool_name": "check_availability", '
            '"arguments": {"doctor_id": "DOC-001", "appointment_date": "2026-08-16", '
            '"appointment_time": "17:00"}}'
        )
    )
    provider = _make_provider(fake_post)

    decision = provider.decide("Is DOC-001 free on 2026-08-16 at 17:00?")

    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "check_availability"
    assert decision.arguments == {
        "doctor_id": "DOC-001",
        "appointment_date": "2026-08-16",
        "appointment_time": "17:00",
    }
    fake_post.assert_called_once()


def test_valid_needs_information_response_transforms_correctly():
    fake_post = MagicMock(
        return_value=_fake_groq_response(
            '{"status": "needs_information", "missing_fields": ["doctor_id"], '
            '"message": "Which doctor did you mean?"}'
        )
    )
    provider = _make_provider(fake_post)

    decision = provider.decide("Is the doctor free?")

    assert isinstance(decision, NeedsInfoDecision)
    assert decision.missing_fields == ["doctor_id"]
    assert decision.message == "Which doctor did you mean?"


def test_valid_unsupported_response_transforms_correctly():
    fake_post = MagicMock(
        return_value=_fake_groq_response('{"status": "unsupported", "message": "I can only help with appointments."}')
    )
    provider = _make_provider(fake_post)

    decision = provider.decide("What's the weather today?")

    assert isinstance(decision, NotApplicableDecision)
    assert decision.message == "I can only help with appointments."


# --- 2. Malformed LLM output is rejected safely -----------------------------------

def test_non_json_content_falls_back_safely():
    fake_post = MagicMock(return_value=_fake_groq_response("this is not json at all"))
    provider = _make_provider(fake_post)

    decision = provider.decide("Book an appointment")

    assert isinstance(decision, NotApplicableDecision)


def test_missing_required_envelope_field_falls_back_safely():
    # No "status" field at all — invalid envelope.
    fake_post = MagicMock(
        return_value=_fake_groq_response('{"tool_name": "check_availability", "arguments": {}}')
    )
    provider = _make_provider(fake_post)

    decision = provider.decide("Is the doctor free?")

    assert isinstance(decision, NotApplicableDecision)


def test_unexpected_http_response_shape_falls_back_safely():
    fake_post = MagicMock(return_value={"unexpected": "shape"})
    provider = _make_provider(fake_post)

    decision = provider.decide("Book an appointment")

    assert isinstance(decision, NotApplicableDecision)


def test_tool_call_without_tool_name_falls_back_safely():
    fake_post = MagicMock(return_value=_fake_groq_response('{"status": "tool_call"}'))
    provider = _make_provider(fake_post)

    decision = provider.decide("Book an appointment")

    assert isinstance(decision, NotApplicableDecision)


# --- 3. Unknown tool names cannot execute arbitrary methods -----------------------

def test_envelope_rejects_unapproved_tool_name_directly():
    with pytest.raises(ValidationError):
        LLMDecisionEnvelope.model_validate(
            {"status": "tool_call", "tool_name": "delete_all_appointments", "arguments": {}}
        )


def test_unapproved_tool_name_in_response_falls_back_safely_end_to_end():
    fake_post = MagicMock(
        return_value=_fake_groq_response(
            '{"status": "tool_call", "tool_name": "drop_excel_workbook", "arguments": {}}'
        )
    )
    provider = _make_provider(fake_post)

    decision = provider.decide("Please wipe the database")

    # Never trusted enough to reach AppointmentAgent as a tool call.
    assert isinstance(decision, NotApplicableDecision)


def test_agent_never_calls_getattr_for_unapproved_tool_name():
    """End-to-end: even if somehow a ToolCallDecision with a bogus name
    were produced, AppointmentAgent must not blow up or fabricate a
    result — this exercises that existing defensive path together with
    the real provider's own allowlist rejection."""
    mock_tools = MagicMock(spec=AppointmentTools)
    fake_post = MagicMock(
        return_value=_fake_groq_response(
            '{"status": "tool_call", "tool_name": "not_a_real_tool", "arguments": {}}'
        )
    )
    provider = _make_provider(fake_post)
    agent = AppointmentAgent(provider, mock_tools)

    response = agent.handle("do something malicious")

    assert response.data is None
    assert mock_tools.mock_calls == []  # no tool method was ever invoked


# --- 4. Unsupported intent handled safely -----------------------------------------

def test_agent_handles_unsupported_intent_from_real_provider():
    mock_tools = MagicMock(spec=AppointmentTools)
    fake_post = MagicMock(
        return_value=_fake_groq_response('{"status": "unsupported", "message": "Not an appointment request."}')
    )
    provider = _make_provider(fake_post)
    agent = AppointmentAgent(provider, mock_tools)

    response = agent.handle("Tell me a joke")

    assert response.intent == "unsupported"
    assert response.data is None
    assert mock_tools.mock_calls == []


# --- 5. Missing required arguments handled safely (via existing tool validation) ----

def test_incomplete_tool_call_arguments_handled_safely_end_to_end():
    """AppointmentTools methods have no Python-level defaults for their
    required parameters (Phase 5 contract, unchanged), so an incomplete
    LLM-supplied arguments dict raises a TypeError at the call site —
    AppointmentAgent now catches this (Phase 7.1 fix, discovered while
    writing this exact test) and returns the same safe, non-crashing
    error response used for any other invalid tool input.
    """
    from app.services.appointment_service import AppointmentService

    fake_post = MagicMock(
        return_value=_fake_groq_response(
            '{"status": "tool_call", "tool_name": "check_availability", '
            '"arguments": {"doctor_id": "DOC-001"}}'  # missing date/time
        )
    )
    provider = _make_provider(fake_post)
    real_tools = AppointmentTools(MagicMock(spec=AppointmentService))
    agent = AppointmentAgent(provider, real_tools)

    response = agent.handle("Is DOC-001 free?")

    assert response.data is None
    assert response.intent == "check_availability"
    assert "valid" in response.message.lower()  # safe, non-crashing error message


def test_agent_never_crashes_on_typeerror_from_tool_call():
    """Direct, minimal reproduction of the Phase 7.1 discovery: calling
    a real tool method with missing required Python arguments must
    never propagate a raw TypeError out of AppointmentAgent.handle()."""
    from app.services.appointment_service import AppointmentService

    real_tools = AppointmentTools(MagicMock(spec=AppointmentService))

    class _FixedDecisionProvider:
        def decide(self, message, context=None):
            return ToolCallDecision(tool_name="check_availability", arguments={"doctor_id": "DOC-001"})

    agent = AppointmentAgent(_FixedDecisionProvider(), real_tools)

    response = agent.handle("irrelevant")  # must not raise

    assert response.data is None
    assert response.intent == "check_availability"


# --- 6. Existing RuleBasedIntentProvider still works --------------------------------

def test_rule_based_provider_still_works_unchanged():
    provider = RuleBasedIntentProvider()
    decision = provider.decide("Is DOC-001 available on 2026-08-16 at 17:00?")
    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "check_availability"


# --- 7. AppointmentAgent still depends only on the LLMProvider abstraction ------------

def test_agent_works_identically_regardless_of_concrete_provider():
    mock_tools = MagicMock(spec=AppointmentTools)
    mock_tools.check_availability.return_value = ToolResult.ok(
        {
            "available": True,
            "doctor_id": "DOC-001",
            "appointment_date": "2026-08-16",
            "appointment_time": "17:00:00",
            "message": "The requested slot is available.",
        }
    )
    fake_post = MagicMock(
        return_value=_fake_groq_response(
            '{"status": "tool_call", "tool_name": "check_availability", '
            '"arguments": {"doctor_id": "DOC-001", "appointment_date": "2026-08-16", '
            '"appointment_time": "17:00"}}'
        )
    )
    real_provider_agent = AppointmentAgent(_make_provider(fake_post), mock_tools)
    rule_based_agent = AppointmentAgent(RuleBasedIntentProvider(), mock_tools)

    resp_a = real_provider_agent.handle("Is DOC-001 free on 2026-08-16 at 17:00?")
    resp_b = rule_based_agent.handle("Is DOC-001 available on 2026-08-16 at 17:00?")

    assert resp_a.intent == resp_b.intent == "check_availability"
    assert resp_a.data == resp_b.data


# --- 8. /chat still works; provider selection is config-driven and safe -------------

def test_dependency_wiring_falls_back_to_rule_based_without_api_key(monkeypatch):
    from app.api.dependencies import get_appointment_agent
    from app.agents.llm_provider import RuleBasedIntentProvider as RBIP
    from app.core.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    get_appointment_agent.cache_clear()

    agent = get_appointment_agent()
    assert isinstance(agent._provider, RBIP)  # no key -> safe fallback, no crash

    get_settings.cache_clear()
    get_appointment_agent.cache_clear()
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


def test_dependency_wiring_selects_groq_when_configured(monkeypatch):
    from app.api.dependencies import get_appointment_agent
    from app.core.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_API_KEY", "test-key-not-real")
    get_settings.cache_clear()
    get_appointment_agent.cache_clear()

    agent = get_appointment_agent()
    assert isinstance(agent._provider, GroqLLMProvider)  # constructed, no network call made

    get_settings.cache_clear()
    get_appointment_agent.cache_clear()
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)


def test_chat_route_still_works_with_default_configuration(monkeypatch):
    """No LLM_* env vars set at all — confirms /chat still works end to
    end through the default RuleBasedIntentProvider wiring."""
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_appointment_agent, get_supervisor
    from app.core.config import get_settings
    from app.main import app

    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    get_appointment_agent.cache_clear()
    get_supervisor.cache_clear()

    with TestClient(app) as client:
        resp = client.post("/chat", json={"message": "What's the weather today?"})

    assert resp.status_code == 200
    assert resp.json()["intent"] == "unsupported"

    get_settings.cache_clear()
    get_appointment_agent.cache_clear()
    get_supervisor.cache_clear()


# --- 9. No agent code imports repositories/openpyxl/pandas ---------------------------

def test_llm_provider_module_does_not_import_excel_or_repositories():
    import inspect

    import app.agents.llm_provider as llm_provider_module

    import_lines = [
        line.strip()
        for line in inspect.getsource(llm_provider_module).splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    forbidden = ["openpyxl", "pandas", "app.repositories", "app.services"]
    for token in forbidden:
        offending = [line for line in import_lines if token in line]
        assert not offending, f"llm_provider.py must not import '{token}': {offending}"


# --- 10. No API key required for the test suite --------------------------------------

def test_module_import_and_construction_require_no_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    # Importing the module and constructing the deterministic provider
    # must never require any credential.
    provider = RuleBasedIntentProvider()
    assert provider.decide("Cancel my appointment", context={"appointment_id": "APT-001"})


def test_groq_provider_requires_explicit_key_not_silently_invented():
    with pytest.raises(ValueError):
        GroqLLMProvider(api_key="")
