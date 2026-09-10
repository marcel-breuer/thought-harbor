"""Public API schemas shared by routes and generated OpenAPI clients."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class SearchResultResponse(BaseModel):
    """One source-grounded hybrid search result."""

    chunk_id: int
    text: str
    score: float
    semantic_score: float
    lexical_score: float
    source_file_id: int
    source_type: Literal["document", "transcript", "email", "audio"]
    source_title: str | None
    document_id: int | None
    meeting_id: int | None
    location: dict[str, object]
    source_offset_start: int | None
    source_offset_end: int | None
    source_start_ms: int | None
    source_end_ms: int | None


class SearchListResponse(BaseModel):
    """Paginated, provenance-preserving search results."""

    items: list[SearchResultResponse]
    page: PageMetadata


class AuthStatusResponse(BaseModel):
    """Describe whether the public first-user bootstrap is still available."""

    setup_required: bool


class BootstrapRequest(BaseModel):
    """Credentials for creating the first local administrator."""

    email: str = Field(max_length=320)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("provide a valid email address")
        return value

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name is required")
        return normalized


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


class ApiTokenCreateRequest(BaseModel):
    """Create an integration token; plaintext is returned only once."""

    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(min_length=1, max_length=10)
    expires_at: datetime | None = None


class ApiTokenResponse(BaseModel):
    """Safe token metadata; token plaintext is omitted after creation."""

    id: int
    name: str
    token_prefix: str
    scopes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    token: str | None = None


class ApiTokenListResponse(BaseModel):
    items: list[ApiTokenResponse]


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


class KnowledgeObjectOptionResponse(BaseModel):
    """Owner-scoped topic/project choice for a clarification."""

    id: int
    kind: Literal["topic", "project", "person", "organization", "custom"]
    title: str


class ClarificationResponse(BaseModel):
    """Pending or resolved classification proposal with source evidence."""

    id: int
    question: str
    status: Literal["open", "resolved"]
    classification_id: int
    label: str
    confidence: float = Field(ge=0, le=1)
    source_text: str
    source_location: dict[str, object]
    options: list[KnowledgeObjectOptionResponse]
    selected_knowledge_object_ids: list[int]
    created_at: datetime
    resolved_at: datetime | None


class ClarificationListResponse(BaseModel):
    """Paginated owner-scoped clarification collection."""

    items: list[ClarificationResponse]
    page: PageMetadata


class ClarificationResolutionRequest(BaseModel):
    """Auditable user action for one uncertain classification."""

    action: Literal["accept", "reject", "edit", "assign"]
    selected_knowledge_object_ids: list[int] = Field(default_factory=list, max_length=20)
    new_topic_title: str | None = Field(default=None, max_length=200)

    @field_validator("new_topic_title")
    @classmethod
    def normalize_new_topic_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ActionTopicResponse(BaseModel):
    """Topic or project associated with an action item's source evidence."""

    id: int
    kind: Literal["topic", "project", "person", "organization", "custom"]
    title: str


class ActionSourceResponse(BaseModel):
    """Exact source context supporting one action item."""

    id: int
    source_type: Literal["document", "transcript", "email", "audio"]
    title: str
    source_file_id: int | None
    chunk_id: int
    text: str
    location: dict[str, object]
    source_offset_start: int | None
    source_offset_end: int | None
    source_start_ms: int | None
    source_end_ms: int | None


class ActionStatusHistoryResponse(BaseModel):
    """One user-visible status transition for an action item."""

    status: str
    previous_status: str | None
    changed_at: datetime


class ActionItemResponse(BaseModel):
    """Canonical task, decision, or open question with provenance."""

    id: int
    type: Literal["task", "decision", "open_question"]
    title: str | None
    content: str
    status: str
    assignee: UserResponse | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    topics: list[ActionTopicResponse]
    sources: list[ActionSourceResponse]
    status_history: list[ActionStatusHistoryResponse]


class ActionItemSummaryResponse(BaseModel):
    """Compact counts for the action-knowledge page header."""

    open_tasks: int = Field(ge=0)
    recent_decisions: int = Field(ge=0)
    open_questions: int = Field(ge=0)


class ActionItemListResponse(BaseModel):
    """Paginated global action-knowledge collection."""

    items: list[ActionItemResponse]
    page: PageMetadata
    summary: ActionItemSummaryResponse


class ActionItemStatusRequest(BaseModel):
    """Validated user-owned status update for one action item."""

    status: str = Field(min_length=1, max_length=32)


class DashboardSourceResponse(BaseModel):
    """Recent source summary suitable for a dashboard card."""

    id: int
    title: str
    source_type: Literal["document", "transcript", "email", "audio"]
    ingestion_status: str
    created_at: datetime
    document_id: int | None
    meeting_id: int | None


class DashboardJobResponse(BaseModel):
    """Processing work that may need the owner's attention."""

    id: int
    job_type: str
    status: str
    subject_type: str | None
    subject_id: int | None
    updated_at: datetime


class DashboardClarificationResponse(BaseModel):
    """A compact pending clarification card."""

    id: int
    question: str
    label: str
    confidence: float = Field(ge=0, le=1)
    created_at: datetime


class DashboardActionResponse(BaseModel):
    """A compact action item card linking to the consolidated action view."""

    id: int
    type: Literal["task", "decision", "open_question"]
    title: str | None
    content: str
    status: str
    created_at: datetime


class DashboardInsightResponse(BaseModel):
    """An explicitly AI-derived suggestion, when asynchronous insights are enabled."""

    id: int
    title: str
    content: str
    source_artifact_id: int | None
    generated_at: datetime


class DashboardResponse(BaseModel):
    """Fast, owner-scoped dashboard read model with no synchronous AI generation."""

    recent_sources: list[DashboardSourceResponse]
    processing_attention: list[DashboardJobResponse]
    pending_clarifications: list[DashboardClarificationResponse]
    open_tasks: list[DashboardActionResponse]
    open_questions: list[DashboardActionResponse]
    recent_decisions: list[DashboardActionResponse]
    active_topics: list[KnowledgeObjectOptionResponse]
    insights: list[DashboardInsightResponse]


class RuntimeSettingsResponse(BaseModel):
    """Non-secret runtime configuration; provider keys are never returned."""

    chat_provider: str
    chat_model: str
    extraction_provider: str
    extraction_model: str
    embeddings_provider: str
    embeddings_model: str
    transcription_model: str
    transcription_device: str
    transcription_compute_type: str
    diarization_enabled: bool
    diarization_provider: str
    diarization_model: str
    max_upload_bytes: int
    external_provider_enabled: bool
