"""LLM provider abstraction + a deterministic, no-external-call
placeholder implementation.

WHY THIS EXISTS (Phase 7 instruction 6 / 19):
No specification document names an LLM provider, and Master
Specification §25 lists "Final LLM/agent framework" as an explicit,
unresolved open decision. Rather than inventing a provider/credentials,
this module defines a small, framework-independent interface
(`LLMProvider`) that any future concrete provider (Claude, OpenAI, etc.)
can implement, and ships exactly one concrete implementation
(`RuleBasedIntentProvider`) that makes NO external calls at all — so the
application is importable and testable with zero API keys configured,
per Phase 7 instruction 6.

WHAT RuleBasedIntentProvider CAN AND CANNOT DO (flagged limitation, not
a hidden gap): it classifies intent via keyword matching and extracts
ONLY machine-readable, unambiguous tokens already present in the
message — appointment IDs ("APT-001"), doctor IDs ("DOC-001"), ISO
dates ("2026-08-16"), and 24-hour times ("17:00"). It does NOT parse
natural language date/time expressions ("Sunday at 5 PM") into
structured values — that requires a real LLM, which is exactly what the
Master Specification's open decision defers. When a required field
cannot be extracted, this provider asks for it explicitly rather than
guessing. `context` lets a caller (e.g. a future richer API, or a test)
pre-supply already-known structured fields, which take precedence over
message text.

SYSTEM_PROMPT is prepared for a future real-provider implementation
(Phase 7 instruction 9) — RuleBasedIntentProvider does not send it
anywhere today, since it makes no LLM calls, but a concrete provider
class built later would use it as-is.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Union

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

SYSTEM_PROMPT = """You are CareFlow-AI's appointment assistant.

1. You are CareFlow-AI's appointment assistant.
2. Use tools for all appointment operations — never answer from memory.
3. Never invent appointment availability.
4. Never claim an appointment was created unless the tool confirms success.
5. Never bypass the tools.
6. Never access or reason from Excel directly.
7. Ask for missing information when required by the tool schema.
8. Respect tool errors — report them accurately.
9. Do not invent doctors, slots, appointments, or statuses.
10. If a tool reports a slot unavailable, communicate that accurately and
    offer to look up alternative slots.
11. Never expose internal implementation details (file paths, stack
    traces, error internals) to the patient.
12. Do not claim success after a failed tool call.
"""


@dataclass
class ToolCallDecision:
    """The provider has enough information to call exactly one tool."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class NeedsInfoDecision:
    """An appointment intent was recognized, but required fields are
    missing from both the message and the supplied context."""

    missing_fields: list[str]
    message: str


@dataclass
class NotApplicableDecision:
    """No supported appointment intent was recognized."""

    message: str


AgentDecision = Union[ToolCallDecision, NeedsInfoDecision, NotApplicableDecision]


class LLMProvider(ABC):
    """Interface any concrete provider (rule-based today; a real LLM
    later) must implement. Swapping providers requires no change to
    AppointmentAgent/Supervisor."""

    @abstractmethod
    def decide(self, message: str, context: dict[str, Any] | None = None) -> AgentDecision:
        """Given a natural-language message and optional pre-known
        context, decide which tool (if any) to call and with what
        arguments — or that more information is needed."""


# Ordered (first match wins): keyword triggers, target tool, and the
# tool's required fields (per Tool Contract §5-12 input schemas).
# `update_appointment` only strictly requires appointment_id — its
# other fields are individually optional per Pydantic Schema Spec §5.
_INTENT_RULES: list[tuple[list[str], str, list[str]]] = [
    (["reject", "decline"], "reject_appointment", ["appointment_id", "reason"]),
    (["approve"], "approve_appointment", ["appointment_id"]),
    (["cancel"], "cancel_appointment", ["appointment_id"]),
    (
        ["reschedule", "move my appointment", "change the time", "move it to"],
        "update_appointment",
        ["appointment_id"],
    ),
    (
        ["status of", "look up appointment", "find my appointment", "check my appointment"],
        "get_appointment",
        ["appointment_id"],
    ),
    (
        ["another time", "alternative", "different time", "other slot", "other time"],
        "find_alternative_slots",
        ["doctor_id", "appointment_date", "appointment_time"],
    ),
    (
        ["book", "confirm that appointment", "create appointment", "schedule an appointment"],
        "create_appointment",
        [
            "patient_name",
            "patient_phone",
            "doctor_id",
            "doctor_name",
            "service",
            "appointment_date",
            "appointment_time",
        ],
    ),
    (
        ["free", "available", "availability", "is dr", "is doctor"],
        "check_availability",
        ["doctor_id", "appointment_date", "appointment_time"],
    ),
]

_APPOINTMENT_ID_RE = re.compile(r"\bAPT-[A-Za-z0-9]+\b")
_DOCTOR_ID_RE = re.compile(r"\bDOC-[A-Za-z0-9]+\b")
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b")


def _extract_from_message(message: str) -> dict[str, str]:
    """Only extracts unambiguous, machine-readable tokens — see module
    docstring for what this deliberately does NOT attempt."""
    extracted: dict[str, str] = {}
    if match := _APPOINTMENT_ID_RE.search(message):
        extracted["appointment_id"] = match.group(0)
    if match := _DOCTOR_ID_RE.search(message):
        extracted["doctor_id"] = match.group(0)
    if match := _DATE_RE.search(message):
        extracted["appointment_date"] = match.group(0)
    if match := _TIME_RE.search(message):
        extracted["appointment_time"] = match.group(0)
    return extracted


class RuleBasedIntentProvider(LLMProvider):
    """Deterministic, no-external-call placeholder. See module
    docstring for scope and limitations."""

    def decide(self, message: str, context: dict[str, Any] | None = None) -> AgentDecision:
        lowered = message.lower()

        matched_tool: str | None = None
        required_fields: list[str] = []
        for keywords, tool_name, fields in _INTENT_RULES:
            if any(keyword in lowered for keyword in keywords):
                matched_tool, required_fields = tool_name, fields
                break

        if matched_tool is None:
            return NotApplicableDecision(
                "I can help with checking availability, booking, viewing, "
                "rescheduling, or cancelling appointments, or with staff "
                "approval/rejection of pending requests. Could you clarify "
                "what you'd like to do?"
            )

        known: dict[str, Any] = {**_extract_from_message(message), **(context or {})}
        missing = [f for f in required_fields if not known.get(f)]

        if missing:
            return NeedsInfoDecision(
                missing_fields=missing,
                message=f"To do that, I still need: {', '.join(missing)}.",
            )

        # Forward any optional fields the tool accepts, when present in
        # context (never invented).
        optional_by_tool = {
            "check_availability": ["service"],
            "find_alternative_slots": ["service", "preferences"],
            "create_appointment": ["notes"],
            "update_appointment": [
                "doctor_id",
                "doctor_name",
                "service",
                "appointment_date",
                "appointment_time",
                "notes",
            ],
            "cancel_appointment": ["reason"],
            "approve_appointment": ["notes", "is_staff", "staff_id"],
            "reject_appointment": ["is_staff", "staff_id"],
        }
        arguments = {f: known[f] for f in required_fields}
        for optional_field in optional_by_tool.get(matched_tool, []):
            if optional_field in known:
                arguments[optional_field] = known[optional_field]

        return ToolCallDecision(tool_name=matched_tool, arguments=arguments)


# =====================================================================
# Phase 7.1 — real LLM-backed provider
#
# Everything below is ADDITIVE: the LLMProvider interface and
# RuleBasedIntentProvider above are unchanged. AppointmentAgent and
# Supervisor require no changes at all — they already depend only on
# the LLMProvider abstraction.
# =====================================================================

# The exact set of tools AppointmentTools actually exposes (Phase 5).
# A real model's output is validated against this allowlist below
# BEFORE anything downstream ever does getattr(tools, tool_name) — the
# model can never select or execute anything outside this set.
_APPROVED_TOOL_NAMES = {
    "check_availability",
    "find_alternative_slots",
    "create_appointment",
    "get_appointment",
    "update_appointment",
    "cancel_appointment",
    "approve_appointment",
    "reject_appointment",
}

# Describes the required envelope shape and each tool's argument names
# to the model. This is INPUT-SHAPE guidance only (mirrors the already-
# documented Tool Contract §5-12 input schemas) — no business rule,
# availability logic, or state-transition rule is described here.
_RESPONSE_FORMAT_INSTRUCTIONS = """
You must respond with a single JSON object and nothing else, matching
exactly one of these three shapes:

1) A tool call, when you have every required argument:
   {"status": "tool_call", "tool_name": "<one of the tool names below>",
    "arguments": {"<field>": "<value>", ...}}

2) Missing required information:
   {"status": "needs_information", "missing_fields": ["<field>", ...],
    "message": "<a short question asking for exactly those fields>"}

3) The request is not a supported appointment operation:
   {"status": "unsupported", "message": "<a short, honest explanation>"}

Approved tool names and their required arguments:
- check_availability: doctor_id, appointment_date (YYYY-MM-DD), appointment_time (HH:MM)
- find_alternative_slots: doctor_id, appointment_date (YYYY-MM-DD), appointment_time (HH:MM)
- create_appointment: patient_name, patient_phone, doctor_id, doctor_name, service, appointment_date (YYYY-MM-DD), appointment_time (HH:MM)
- get_appointment: appointment_id
- update_appointment: appointment_id
- cancel_appointment: appointment_id
- approve_appointment: appointment_id
- reject_appointment: appointment_id, reason

Never invent a doctor_id, appointment_id, date, or time that was not
given to you. If a value wasn't stated, that field is missing — use
status "needs_information" instead of guessing.
"""


class LLMDecisionEnvelope(BaseModel):
    """Validates the raw JSON a real LLM returns before it is ever
    trusted enough to select a tool. This is the ONLY place raw model
    output is parsed — AppointmentAgent never sees anything but the
    existing ToolCallDecision/NeedsInfoDecision/NotApplicableDecision
    dataclasses, unchanged from before Phase 7.1.
    """

    status: Literal["tool_call", "needs_information", "unsupported"]
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    message: str | None = None

    @field_validator("tool_name")
    @classmethod
    def _tool_name_must_be_approved(cls, value: str | None) -> str | None:
        if value is not None and value not in _APPROVED_TOOL_NAMES:
            raise ValueError(
                f"'{value}' is not an approved AppointmentTools method; "
                f"approved names are {sorted(_APPROVED_TOOL_NAMES)}"
            )
        return value

    @model_validator(mode="after")
    def _tool_call_requires_tool_name(self) -> "LLMDecisionEnvelope":
        if self.status == "tool_call" and not self.tool_name:
            raise ValueError("status='tool_call' requires a tool_name.")
        return self

    def to_agent_decision(self) -> AgentDecision:
        if self.status == "tool_call":
            return ToolCallDecision(tool_name=self.tool_name, arguments=self.arguments)
        if self.status == "needs_information":
            return NeedsInfoDecision(
                missing_fields=self.missing_fields or ["required information"],
                message=self.message or "Could you provide a few more details?",
            )
        return NotApplicableDecision(
            self.message
            or "I can help with checking availability, booking, viewing, "
            "rescheduling, or cancelling appointments, or with staff "
            "approval/rejection of pending requests."
        )


class GroqLLMProvider(LLMProvider):
    """Real LLM-backed provider using Groq's OpenAI-compatible chat
    completions REST API. See Phase 7.1 report for the provider
    comparison and why Groq was selected.

    Uses `httpx` directly (already a project dependency since Phase 6 —
    no new dependency was added for this). The HTTP call itself is
    injectable via `http_post`, defaulting to a real network call, so
    tests never need real credentials or network access.

    Malformed/unexpected model output is NEVER trusted enough to select
    or execute a tool: any parsing/validation failure falls back to a
    safe NotApplicableDecision instead of crashing or hallucinating a
    tool call.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
        base_url: str = "https://api.groq.com/openai/v1/chat/completions",
        http_post: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        timeout: float = 15.0,
    ):
        if not api_key:
            raise ValueError("GroqLLMProvider requires a non-empty api_key.")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._timeout = timeout
        # Injectable for testing; defaults to a real network call. This
        # is the ONLY place a network request is made anywhere in the
        # agents package.
        self._http_post = http_post or self._default_http_post

    def _default_http_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        response = httpx.post(
            self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()

    def _build_user_content(self, message: str, context: dict[str, Any] | None) -> str:
        if not context:
            return message
        return f"{message}\n\nAlready-known information: {json.dumps(context)}"

    def decide(self, message: str, context: dict[str, Any] | None = None) -> AgentDecision:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + "\n" + _RESPONSE_FORMAT_INSTRUCTIONS},
                {"role": "user", "content": self._build_user_content(message, context)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }

        try:
            raw = self._http_post(payload)
            content = raw["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            envelope = LLMDecisionEnvelope.model_validate(parsed)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError, ValidationError):
            # Covers: malformed JSON, unexpected response shape, an
            # unapproved tool_name, or any other validation failure.
            return NotApplicableDecision(
                "I had trouble understanding that request. Could you rephrase it?"
            )

        return envelope.to_agent_decision()
