"""CareFlow AI — FastAPI application entrypoint.

Phase 1 scope only: app factory, request-id middleware, logging setup, and
the health route. No appointment business logic, no Excel access, no
agent/tool wiring belongs in this file — those arrive in later phases per
the Claude Implementation Master Guide's phase plan.
"""

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging, request_id_ctx_var


def create_app() -> FastAPI:
    """Application factory.

    Using a factory (rather than a bare module-level `app`) keeps startup
    configuration explicit and makes future testing (e.g. overriding
    settings/dependencies) straightforward without import-time side effects.
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        """Assign a request id for traceability, per the FastAPI API
        Contract Specification's error/response conventions (§14, §20).

        The id is: read from an incoming X-Request-ID header if present
        (so callers/gateways can supply their own), otherwise generated.
        It is stored in a ContextVar for logging and echoed back on the
        response so a client can correlate a request with server logs.
        """
        incoming_id = request.headers.get("x-request-id")
        req_id = incoming_id or str(uuid.uuid4())
        token = request_id_ctx_var.set(req_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)
        response.headers["X-Request-ID"] = req_id
        return response

    app.include_router(health_router)

    return app


app = create_app()
