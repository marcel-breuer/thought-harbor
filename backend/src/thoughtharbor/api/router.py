"""Versioned REST API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from thoughtharbor.api.schemas import (
    DependencyHealthResponse,
    ErrorResponse,
    HealthResponse,
    PaginationParams,
    ReadinessResponse,
    pagination_params,
)
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.auth.router import router as auth_router
from thoughtharbor.chat.router import router as chat_router
from thoughtharbor.documents.router import router as inbox_router
from thoughtharbor.domain.models import User
from thoughtharbor.domain.system import SystemService
from thoughtharbor.knowledge.action_items_router import router as action_items_router
from thoughtharbor.knowledge.router import router as clarifications_router
from thoughtharbor.knowledge.views_router import router as knowledge_views_router
from thoughtharbor.meetings.router import router as meetings_router
from thoughtharbor.operations.health import HealthService
from thoughtharbor.search.router import router as search_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(inbox_router)
router.include_router(meetings_router)
router.include_router(clarifications_router)
router.include_router(search_router)
router.include_router(chat_router)
router.include_router(knowledge_views_router)
router.include_router(action_items_router)


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
    "/ready",
    response_model=ReadinessResponse,
    tags=["system"],
    summary="Check service readiness",
    responses={
        503: {
            "model": ReadinessResponse,
            "description": "One or more local dependencies are unavailable.",
        },
    },
)
def readiness(response: Response) -> ReadinessResponse:
    """Report local dependency health without exposing connection details."""

    current_status, checks = HealthService().readiness()
    if current_status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status=current_status,
        checks=[
            DependencyHealthResponse(name=check.name, status=check.status, detail=check.detail)
            for check in checks
        ],
    )


@router.get(
    "/settings/diagnostics",
    response_model=ReadinessResponse,
    tags=["system"],
    summary="Show authenticated service diagnostics",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication is required."},
        503: {
            "model": ReadinessResponse,
            "description": "One or more local dependencies are unavailable.",
        },
    },
)
def diagnostics(
    response: Response,
    _: Annotated[User, Depends(get_current_user)],
) -> ReadinessResponse:
    """Expose the same safe checks in the local settings surface."""

    return readiness(response)


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
