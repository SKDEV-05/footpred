"""Error envelope and exception handlers.

One shape for every failure. Internal detail (stack traces, SQL, provider messages,
file paths) never reaches a client.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError, NotFoundError
from app.core.logging import request_id_var
from app.schemas.common import ErrorDetail, ErrorEnvelope

logger = logging.getLogger(__name__)


def _envelope(
    *, code: str, message: str, details: object = None, status_code: int
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
            request_id=request_id_var.get() or str(uuid4()),
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return _envelope(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            status_code=exc.http_status,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ())[1:]),
                "message": error.get("msg", "invalid value"),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return _envelope(
            code="validation_error",
            message="Request validation failed.",
            details=details,
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        mapping = {
            404: ("not_found", "Resource does not exist."),
            405: ("method_not_allowed", "Method not allowed for this resource."),
            406: ("not_acceptable", "Requested representation is not available."),
        }
        code, message = mapping.get(
            exc.status_code, ("http_error", "The request could not be completed.")
        )
        return _envelope(
            code=code,
            message=message,
            details=exc.detail if exc.status_code < 500 else None,
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled API error",
            extra={"event": "api.unhandled_error", "component": "api"},
        )
        return _envelope(
            code="internal_error",
            message="An internal error occurred.",
            status_code=500,
        )


__all__ = ["install_error_handlers", "NotFoundError"]
