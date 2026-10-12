"""Consistent error model for the API.

Every error response has the shape::

    {"error": {"code": "ROUTE_NOT_FOUND", "message": "...", "details": {...}}}
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class SkyForceError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if code:
            self.code = code


class NotFoundError(SkyForceError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationFailed(SkyForceError):
    status_code = 422
    code = "VALIDATION_FAILED"


class ModelUnavailableError(SkyForceError):
    status_code = 503
    code = "MODEL_UNAVAILABLE"


class ExternalSourceError(SkyForceError):
    status_code = 502
    code = "EXTERNAL_SOURCE_ERROR"


class RateLimitedError(SkyForceError):
    status_code = 429
    code = "RATE_LIMITED"


def _body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SkyForceError)
    async def _sf(_: Request, exc: SkyForceError):  # noqa: ANN202
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _val(_: Request, exc: RequestValidationError):  # noqa: ANN202
        errors = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content=_body("VALIDATION_FAILED", "Request validation failed", {"errors": errors}))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):  # noqa: ANN202
        logger.exception("Unhandled error: %s", exc)
        # Safe message: never leak internals/stack traces to clients.
        return JSONResponse(status_code=500, content=_body("INTERNAL_ERROR", "An unexpected server error occurred."))
