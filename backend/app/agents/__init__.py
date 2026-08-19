"""Agent Orchestration layer.

Implements Master Specification SYS-01 (Supervisor Agent) and SYS-03
(Appointment Agent). This package performs UNDERSTANDING + REASONING +
TOOL SELECTION only — it never implements business rules, availability
algorithms, state transitions, or persistence, and it never imports
openpyxl, pandas, app.repositories, or app.services. Every appointment
operation goes through app.tools.appointment_tools.AppointmentTools
(Phase 5), which itself goes through AppointmentService (Phase 4).

Scope note (flagged, see Phase 7 report): no Knowledge/RAG Agent
(Master Spec SYS-02) is implemented here — no Clinic Knowledge Store
exists in any prior phase, and the Master Specification lists the
RAG/vector-store implementation as an unresolved open decision (§25).

Module layout:
    llm_provider.py     — LLMProvider interface + decision types, plus
                           RuleBasedIntentProvider (a deterministic,
                           no-external-call placeholder — see its
                           module docstring for exactly what it can and
                           cannot extract from a message)
    appointment_agent.py — AppointmentAgent: turns an LLMProvider
                           decision into a Phase 5 tool call and a
                           user-facing response
    supervisor.py         — Supervisor: top-level entry point, composes
                           the documented ChatResponse shape
"""
