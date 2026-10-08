"""One error shape for every endpoint:

    {"error": {"code": "not_found", "message": "service 'x' not found", "details": {...}}}

with a status code that matches the problem (400/403/404/409/422/500).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("aiops.api")

CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed",
         409: "conflict", 422: "validation_failed", 500: "internal_error", 503: "unavailable"}


class ApiError(Exception):
    def __init__(self, status: int, message: str, code: str | None = None, details: dict | None = None):
        self.status, self.message, self.code, self.details = status, message, code or CODES.get(status, "error"), details


def not_found(what: str, key) -> ApiError:
    return ApiError(404, f"{what} '{key}' not found")


def body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def install(app: FastAPI):
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError):
        return JSONResponse(body(e.code, e.message, e.details), status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        fields = [{"field": ".".join(str(x) for x in err["loc"][1:]), "problem": err["msg"]} for err in e.errors()]
        return JSONResponse(body("validation_failed", "request body or parameters are invalid", {"fields": fields}),
                            status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        return JSONResponse(body(CODES.get(e.status_code, "error"), str(e.detail)), status_code=e.status_code)

    @app.exception_handler(Exception)
    async def _crash(_: Request, e: Exception):
        log.exception("unhandled error")
        return JSONResponse(body("internal_error", f"{type(e).__name__}: {e}"), status_code=500)
