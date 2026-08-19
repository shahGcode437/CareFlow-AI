"""Application-level configuration.

Scope note: this module holds *application* settings (app metadata,
host/port, log level, CORS, and — as of Phase 3 — the Excel workbook
path). It intentionally does NOT hold appointment/business configuration
such as default slot duration or the staff-approval policy — those
values live in the Excel `Config` sheet and are a Phase 4 (Service)
concern; no ConfigRepository is implemented in Phase 3 since it is not
among the documented repository interfaces. Do not add business rules
here.

Values are loaded from environment variables (optionally via a local .env
file during development). See .env.example for the supported variables.

Phase 3 addition — flagged assumption:
No specification document names an environment variable or config key
for the Excel workbook path. Per the Phase 3 instructions, this is
flagged rather than silently invented: the setting is named
`excel_file_path` (env var `EXCEL_FILE_PATH`) below. Please confirm or
rename it. The default value points at data/clinic_appointments_MVP_template.xlsx,
resolved relative to the backend project root (never an absolute,
machine-specific path), matching the `data/` folder location shown in
the Master Specification §19 recommended project structure.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] == backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment-driven application settings.

    All fields have safe local-development defaults so the app can start
    without a .env file being present. Production deployments should
    override these via real environment variables / secret manager, never
    by committing secrets to source control.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application metadata ---
    app_name: str = "CareFlow AI Backend"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | staging | production

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Logging ---
    log_level: str = "INFO"

    # --- CORS (permissive defaults for local dev only) ---
    cors_allow_origins: list[str] = ["*"]

    # --- Excel workbook path (Phase 3) ---
    # Flagged assumption — see module docstring. Relative paths are
    # resolved against the backend project root, never the process's
    # current working directory, so behavior is the same regardless of
    # where `uvicorn` is launched from.
    excel_file_path: str = "data/clinic_appointments_MVP_template.xlsx"

    # --- Staff-approval policy (Phase 6 wiring of a Phase 4 flagged gap) ---
    # AppointmentService (Phase 4) takes `require_staff_approval` as an
    # explicit constructor dependency because no ConfigRepository exists
    # to read the workbook's own Config sheet (`require_staff_approval`
    # value) — that gap was flagged, not resolved, in the Phase 4 report.
    # This setting is the smallest way to make that value configurable
    # for the running application without inventing a ConfigRepository or
    # having the Service touch Excel directly. Defaults to True, matching
    # the Service's own default and the value currently in the Config
    # sheet — but this is NOT read from the Config sheet automatically.
    require_staff_approval: bool = True

    # --- LLM provider (Phase 7.1) ---
    # Defaults to "rule_based" (RuleBasedIntentProvider, no external
    # calls) so the app is importable/testable with zero configuration.
    # Set LLM_PROVIDER=groq + LLM_API_KEY to enable the real provider —
    # see app/agents/llm_provider.py (GroqLLMProvider) and the Phase 7.1
    # report for why Groq was selected. Never hardcode a real key here.
    llm_provider: str = "rule_based"  # "rule_based" | "groq"
    llm_model: str = "llama-3.1-8b-instant"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def resolved_excel_file_path(self) -> Path:
        """Absolute path to the Excel workbook, without hardcoding any
        machine-specific location."""
        path = Path(self.excel_file_path)
        if path.is_absolute():
            return path
        return (_BACKEND_ROOT / path).resolve()


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the environment is parsed once per process rather than on
    every request/import.
    """
    return Settings()

