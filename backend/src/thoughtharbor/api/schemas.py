"""Public API schemas shared by routes and generated OpenAPI clients."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HealthResponse(BaseModel):
    """Response returned by the public health endpoints."""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})

    status: Literal["ok", "degraded", "unavailable"]


class DependencyHealthResponse(BaseModel):
    """Safe status for one readiness dependency."""

    name: str
    status: Literal["ok", "unavailable"]
    detail: str


class ReadinessResponse(BaseModel):
    """Aggregate dependency readiness for self-hosted operations."""

    status: Literal["ok", "unavailable"]
    checks: list[DependencyHealthResponse]


class ValidationErrorDetail(BaseModel):
    """A machine-readable validation problem location."""

    location: list[str | int] = Field(description="Path to the invalid request value.")
    message: str = Field(description="Human-readable validation message.")
    type: str = Field(description="Pydantic validation error type.")


class ErrorBody(BaseModel):
    """Stable error information nested inside the API error envelope."""

    code: str = Field(
        description="Stable machine-readable error code.",
        examples=["VALIDATION_ERROR", "HTTP_404", "INTERNAL_ERROR"],
    )
    message: str = Field(description="Human-readable error message.")
    details: list[ValidationErrorDetail] | None = Field(
        default=None,
        description="Optional field-level validation details.",
    )


class ErrorResponse(BaseModel):
    """Common error envelope returned by every API error handler."""

    error: ErrorBody
    request_id: str = Field(description="Correlation ID for this request.")


class PaginationParams(BaseModel):
    """Canonical pagination, filtering, and sorting query parameters."""

    page: int = Field(default=1, ge=1, description="One-based page number.")
    page_size: int = Field(default=25, ge=1, le=100, description="Items per page.")
    search: str | None = Field(default=None, min_length=1, max_length=200)
    sort_by: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")
    sort_order: Literal["asc", "desc"] = "asc"


def pagination_params(
    page: Annotated[int, Query(ge=1, description="One-based page number.")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page (maximum 100)."),
    ] = 25,
    search: Annotated[
        str | None,
        Query(min_length=1, max_length=200, description="Optional text filter."),
    ] = None,
    sort_by: Annotated[
        str | None,
        Query(
            pattern=r"^[a-z][a-z0-9_]*$",
            description="Public resource field used for sorting.",
        ),
    ] = None,
    sort_order: Annotated[
        Literal["asc", "desc"],
        Query(description="Sort direction."),
    ] = "asc",
) -> PaginationParams:
    """Build canonical list query parameters for resource routers."""

    return PaginationParams(
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


class PageMetadata(BaseModel):
    """Metadata returned with paginated collection responses."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class AuthStatusResponse(BaseModel):
    """Describe whether the public first-user bootstrap is still available."""

    setup_required: bool


class BootstrapRequest(BaseModel):
    """Credentials for creating the first local administrator."""

    email: str | None = Field(default=None, max_length=320)
    username: str | None = Field(default=None, min_length=3, max_length=64)
    display_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=12, max_length=256)

    @model_validator(mode="after")
    def require_identifier(self) -> "BootstrapRequest":
        if not self.email and not self.username:
            raise ValueError("email or username is required")
        return self

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is not None and ("@" not in value or value.startswith("@") or value.endswith("@")):
            raise ValueError("provide a valid email address")
        return value


class LoginRequest(BaseModel):
    """Email/username credentials for an existing local account."""

    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    """Safe public representation of an authenticated local user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None
    username: str | None
    display_name: str | None
    role: Literal["admin", "user"]


class AuthSessionResponse(BaseModel):
    """Response returned after bootstrap or login; the token is cookie-only."""

    user: UserResponse


class MessageResponse(BaseModel):
    """Small response for successful state-changing operations."""

    message: str


class IngestionStatusEvent(BaseModel):
    """One durable status transition shown in the inbox timeline."""

    status: Literal[
        "uploaded",
        "queued",
        "parsing",
        "transcribing",
        "analysing",
        "ready",
        "needs_input",
        "failed",
    ]
    at: datetime


class InboxItemResponse(BaseModel):
    """Safe owner-scoped source-file representation for the inbox."""

    id: int
    original_name: str
    media_type: str | None
    byte_size: int
    sha256: str
    source_type: Literal["document", "transcript", "email", "audio"]
    ingestion_status: Literal[
        "uploaded",
        "queued",
        "parsing",
        "transcribing",
        "analysing",
        "ready",
        "needs_input",
        "failed",
    ]
    status_timeline: list[IngestionStatusEvent]
    progress: float | None = Field(default=None, ge=0, le=1)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    document_id: int | None = None
    meeting_id: int | None = None


class InboxListResponse(BaseModel):
    """Paginated inbox response."""

    items: list[InboxItemResponse]
    page: PageMetadata


class SpeakerResponse(BaseModel):
    """Safe representation of an anonymous or user-renamed meeting speaker."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int | None
    label: str
    display_name: str | None


class SpeakerRenameRequest(BaseModel):
    """User-assigned speaker label; blank labels are rejected."""

    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("display_name must not be blank")
        return normalized
