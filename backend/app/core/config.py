"""Application-level configuration.

Scope note (Phase 1 only): this module holds *application* settings only
(app metadata, host/port, log level, CORS). It intentionally does NOT hold
appointment/business configuration such as default slot duration or the
staff-approval policy — those values live in the Excel `Config` sheet and
will be read through a repository in a later phase, per the approved
Service Design Specification. Do not add business rules here.

Values are loaded from environment variables (optionally via a local .env
file during development). See .env.example for the supported variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the environment is parsed once per process rather than on
    every request/import.
    """
    return Settings()
