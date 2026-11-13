"""FastAPI application factory.

Read-only in Phase 3: there is no POST, PUT, PATCH, or DELETE endpoint. The API serves
stored data and never contacts a provider during a request.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request

from app.api.errors import install_error_handlers
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, request_id_var

logger = logging.getLogger(__name__)

API_VERSION = "0.1.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    docs_enabled = resolved.api_docs_enabled
    app = FastAPI(
        title=resolved.app_name,
        version=API_VERSION,
        description=(
            "Read-only football data API. Provider payloads and credentials are never "
            "exposed. Missing data is reported as missing, never as zero."
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    @app.middleware("http")
    async def _request_id(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming if incoming and len(incoming) <= 128 else str(uuid4())
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response

    install_error_handlers(app)

    @app.get("/health", include_in_schema=False)
    def liveness() -> dict[str, str]:
        """Process liveness only: no database or provider dependency is checked."""

        return {"status": "ok"}

    app.include_router(api_router)

    logger.info(
        "API application created",
        extra={"event": "api.created", "component": "api"},
    )
    return app


app = create_app()
