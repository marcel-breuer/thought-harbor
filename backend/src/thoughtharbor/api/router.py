"""Versioned REST API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from thoughtharbor.api.schemas import (
    ErrorResponse,
    HealthResponse,
    PaginationParams,
    pagination_params,
)
from thoughtharbor.domain.system import SystemService

router = APIRouter(prefix="/api/v1")


def get_system_service() -> SystemService:
    """Provide the application service used by system routes."""

    return SystemService()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Check API availability",
    description="Returns the availability of the ThoughtHarbor API process.",
    responses={
        422: {"model": ErrorResponse, "description": "Request validation failed."},
        500: {"model": ErrorResponse, "description": "Unexpected server error."},
    },
)
async def health(service: Annotated[SystemService, Depends(get_system_service)]) -> HealthResponse:
    """Return API health through the application service layer."""

    status = service.health().status
    if status != "ok":
        raise RuntimeError("Unexpected health status")
    return HealthResponse(status="ok")


@router.get(
    "/_contract/pagination",
    response_model=PaginationParams,
    include_in_schema=False,
)
async def pagination_contract(
    params: Annotated[PaginationParams, Depends(pagination_params)],
) -> PaginationParams:
    """Keep pagination conventions available to future resource routers."""

    return params
