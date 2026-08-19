"""AppointmentAgent — interprets appointment-related natural language
and calls the approved Phase 5 tools.

Implements Master Specification SYS-03 ("Coordinates appointment
workflows and selects approved appointment tools"). This agent NEVER
imports AppointmentService, repositories, or openpyxl/pandas — it only
calls methods on the injected AppointmentTools (Phase 5), and only
communicates the ToolResult it gets back. It performs NO availability,
conflict, or state-transition reasoning itself; that all already
happened inside AppointmentService by the time a ToolResult comes back.
"""

from dataclasses import dataclass
from typing import Any

from app.agents.llm_provider import LLMProvider, NeedsInfoDecision, NotApplicableDecision, ToolCallDecision
from app.tools.appointment_tools import AppointmentTools
from app.tools.tool_result import ToolResult


@dataclass
class AgentResponse:
    message: str
    intent: str
    data: dict[str, Any] | None
    requires_staff_review: bool


# Human-readable phrasing per documented tool/service error code
# (Service Design §22 / Tool Contract §16), per Phase 7 instruction 12.
_ERROR_MESSAGES: dict[str, str] = {
    "DOCTOR_NOT_FOUND": "I couldn't find that doctor. Could you double-check the doctor ID?",
    "DOCTOR_INACTIVE": "That doctor isn't currently accepting appointments.",
    "OUTSIDE_AVAILABILITY": "That time is outside the doctor's available hours.",
    "INVALID_SLOT_TIME": "That time doesn't align with the doctor's appointment schedule.",
    "SLOT_UNAVAILABLE": "That slot is already booked. Would you like me to look for an alternative time?",
    "APPOINTMENT_NOT_FOUND": "I couldn't find an appointment with that ID.",
    "INVALID_APPOINTMENT_STATE": "That action isn't allowed for the appointment's current status.",
    "UNAUTHORIZED": "That action requires staff authorization.",
    "REPOSITORY_ERROR": "Something went wrong while saving that. Please try again.",
    "VALIDATION_ERROR": "That request wasn't valid — please check the details and try again.",
}


class AppointmentAgent:
    def __init__(self, provider: LLMProvider, tools: AppointmentTools):
        self._provider = provider
        self._tools = tools

    def handle(self, message: str, context: dict[str, Any] | None = None) -> AgentResponse:
        decision = self._provider.decide(message, context)

        if isinstance(decision, NotApplicableDecision):
            return AgentResponse(
                message=decision.message, intent="unsupported", data=None, requires_staff_review=False
            )

        if isinstance(decision, NeedsInfoDecision):
            return AgentResponse(
                message=decision.message,
                intent="needs_information",
                data=None,
                requires_staff_review=False,
            )

        assert isinstance(decision, ToolCallDecision)
        tool_method = getattr(self._tools, decision.tool_name, None)
        if tool_method is None:
            # Defensive only: the provider named something outside the
            # approved tool set. Never fabricate a result for it.
            return AgentResponse(
                message="I wasn't able to process that request.",
                intent="error",
                data=None,
                requires_staff_review=False,
            )

        try:
            result: ToolResult = tool_method(**decision.arguments)
        except TypeError:
            # Phase 7.1 discovery: decision.arguments comes from an
            # untrusted provider (a real LLM's structured output) and
            # AppointmentTools method parameters have no Python-level
            # defaults, so an incomplete arguments dict raises a raw
            # TypeError before the tool's own Pydantic validation ever
            # runs. Treated the same as any other invalid tool input —
            # never allowed to crash the request.
            return AgentResponse(
                message="That request wasn't valid — please check the details and try again.",
                intent=decision.tool_name,
                data=None,
                requires_staff_review=False,
            )

        if not result.success:
            message = _ERROR_MESSAGES.get(result.error.code, result.error.message)
            return AgentResponse(
                message=message, intent=decision.tool_name, data=None, requires_staff_review=False
            )

        # Per Master Spec §11/Service Design §6: "Pending" means the
        # request is awaiting configured staff review. Reading the
        # already-returned status, not deciding policy.
        requires_review = bool(result.data and result.data.get("status") == "Pending")
        return AgentResponse(
            message=self._success_message(decision.tool_name, result.data),
            intent=decision.tool_name,
            data=result.data,
            requires_staff_review=requires_review,
        )

    @staticmethod
    def _success_message(tool_name: str, data: dict[str, Any] | None) -> str:
        if tool_name == "check_availability" and data:
            return data.get("message", "Availability checked.")
        if tool_name == "find_alternative_slots":
            if data and data.get("alternatives"):
                return "Here are some alternative times I found."
            return "No alternative slots were found."
        if tool_name == "create_appointment" and data:
            return f"Your appointment request ({data.get('appointment_id')}) is {data.get('status')}."
        if tool_name == "get_appointment" and data:
            return f"Appointment {data.get('appointment_id')} is {data.get('status')}."
        if tool_name == "update_appointment" and data:
            return f"Appointment {data.get('appointment_id')} has been updated."
        if tool_name == "cancel_appointment" and data:
            return f"Appointment {data.get('appointment_id')} has been cancelled."
        if tool_name == "approve_appointment" and data:
            return f"Appointment {data.get('appointment_id')} has been approved."
        if tool_name == "reject_appointment" and data:
            return f"Appointment {data.get('appointment_id')} has been rejected."
        return "Done."
