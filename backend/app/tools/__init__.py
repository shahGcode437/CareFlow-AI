"""Agent Tools layer — thin adapters over AppointmentService.

Implements the 8 tools documented in the Appointment Agent Tool
Contract Specification v1.0 (§3, §5-12). Per that spec's Core Principle:
"The agent receives controlled business tools; it never receives raw
Excel/file manipulation tools."

This package contains NO business logic, NO availability algorithm, NO
state-transition rules, and NO Excel/openpyxl/pandas access. Every tool
validates its input via the existing Phase 2 Pydantic schemas and then
calls exactly one AppointmentService method (Phase 4), converting the
result (or a documented ServiceError) into the structured tool result
shape from Tool Contract §16.

Framework-independent by design: no LangChain/LangGraph dependency.
Tool functions accept plain, JSON-friendly primitive arguments (str for
IDs/dates/times) so a future agent/function-calling framework (Phase 7)
can wrap them directly without any adaptation layer.

Module layout:
    tool_result.py       — ToolResult / ToolError (Tool Contract §16 shape)
    appointment_tools.py — AppointmentTools, exposing the 8 documented
                            tool names as methods
"""
