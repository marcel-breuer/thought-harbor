"""FastAPI application entrypoint."""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from thoughtharbor.api.errors import (
    ApplicationError,
    application_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from thoughtharbor.api.middleware import RequestIdMiddleware
from thoughtharbor.api.router import router as api_router
from thoughtharbor.api.schemas import HealthResponse
from thoughtharbor.auth.settings import AuthSettings

auth_settings = AuthSettings.from_environment()

app = FastAPI(
    title="ThoughtHarbor API",
    description="HTTP API for the self-hosted ThoughtHarbor second brain.",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "system",
            "description": "Availability and system-level API operations.",
        }
    ],
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(auth_settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["Retry-After", "X-Request-ID"],
)
app.add_exception_handler(ApplicationError, application_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
app.include_router(api_router)


@app.get("/health", response_model=HealthResponse, include_in_schema=False)
async def legacy_health() -> HealthResponse:
    """Keep the unversioned container health probe stable."""

    return HealthResponse(status="ok")
