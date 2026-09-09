"""Public API schemas shared by routes and generated OpenAPI clients."""

from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Response returned by the public health endpoints."""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})

    status: Literal["ok"]


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
