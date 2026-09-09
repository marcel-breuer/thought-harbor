"""Consistent public API error handling."""

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from thoughtharbor.api.schemas import ErrorBody, ErrorResponse, ValidationErrorDetail


class ApplicationError(Exception):
    """Expected application failure that can be exposed safely to callers."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: list[ValidationErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def _request_id(request: Request) -> str:
    """Read the correlation ID installed by RequestIdMiddleware."""

    return str(getattr(request.state, "request_id", "unknown"))


def _response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[ValidationErrorDetail] | None = None,
) -> JSONResponse:
    """Serialize one error using the stable public envelope."""

    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details),
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


async def application_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle expected application errors without leaking internals."""

    if not isinstance(exc, ApplicationError):
        return await unhandled_error_handler(request, exc)
    return _response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Normalize framework HTTP errors into the public envelope."""

    if not isinstance(exc, HTTPException):
        return await unhandled_error_handler(request, exc)
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return _response(
        request,
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=message,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return field-level details for invalid request parameters and bodies."""

    if not isinstance(exc, RequestValidationError):
        return await unhandled_error_handler(request, exc)
    details = [
        ValidationErrorDetail(
            location=[part for part in error.get("loc", []) if isinstance(part, (str, int))],
            message=str(error.get("msg", "Invalid value")),
            type=str(error.get("type", "value_error")),
        )
        for error in exc.errors()
    ]
    return _response(
        request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="The request could not be validated.",
        details=details,
    )


async def unhandled_error_handler(request: Request, _: Exception) -> JSONResponse:
    """Return a safe response for unexpected failures."""

    return _response(
        request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred.",
    )
