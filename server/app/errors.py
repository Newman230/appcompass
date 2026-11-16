"""Errors in the contract's shape: {"code", "message", "details"?} (spec/openapi.yaml#Error)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []


def _body(code: str, message: str, details: list[str] | None = None) -> dict:
    body: dict = {"code": code, "message": message}
    if details:
        body["details"] = details
    return body


_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "bad_request",
    409: "conflict",
    422: "validation_error",
    501: "not_implemented",
}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            f"{'.'.join(str(p) for p in err.get('loc', []))}: {err.get('msg', '')}" for err in exc.errors()
        ]
        return JSONResponse(status_code=422, content=_body("validation_error", "Request body is invalid", details))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "internal")
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)))
