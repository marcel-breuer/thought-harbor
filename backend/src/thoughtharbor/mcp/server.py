"""Authenticated, read-only MCP adapter for shared ThoughtHarbor services."""

import hmac
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from thoughtharbor.auth.tokens import ApiTokenService
from thoughtharbor.chat.service import RAGService
from thoughtharbor.db.session import SessionFactory
from thoughtharbor.knowledge.action_items import ActionItemService
from thoughtharbor.knowledge.clarifications import ClarificationService
from thoughtharbor.knowledge.views import KnowledgeViewService
from thoughtharbor.search.service import SearchService

mcp = FastMCP("ThoughtHarbor")


def _authenticate(token: str) -> int:
    """Resolve the configured local MCP identity without persisting a token."""

    expected = os.environ.get("MCP_API_TOKEN", "")
    owner_value = os.environ.get("MCP_OWNER_ID", "")
    if not expected or not owner_value or not hmac.compare_digest(token, expected):
        raise ValueError("MCP_AUTH_REQUIRED: provide the configured MCP token")
    try:
        return int(owner_value)
    except ValueError as error:
        raise ValueError("MCP_CONFIGURATION_INVALID: MCP_OWNER_ID must be an integer") from error


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _source(chunk: Any) -> dict[str, Any]:
    return {
        "chunk_id": chunk.id,
        "text": chunk.text,
        "location": chunk.location,
        "source_offset_start": chunk.source_offset_start,
        "source_offset_end": chunk.source_offset_end,
        "source_start_ms": chunk.source_start_ms,
        "source_end_ms": chunk.source_end_ms,
    }


@mcp.tool(description="Search owner-scoped knowledge and return exact source provenance.")
async def search_knowledge(
    token: str, query: str, page: int = 1, page_size: int = 10
) -> dict[str, Any]:
    """Search indexed knowledge using the same service as the HTTP API."""

    owner_id = _authenticate(token)
    if not query.strip() or page < 1 or not 1 <= page_size <= 100:
        raise ValueError("MCP_INVALID_ARGUMENT: query and pagination are invalid")
    with SessionFactory() as session:
        hits, total = await SearchService(session).search(
            owner_id, query, page=page, page_size=page_size
        )
    return {
        "items": [
            {
                "chunk_id": hit.candidate.chunk_id,
                "text": hit.candidate.text,
                "score": hit.candidate.score,
                "source_file_id": hit.source_file_id,
                "source_type": hit.source_type,
                "source_title": hit.source_title,
                "document_id": hit.document_id,
                "meeting_id": hit.meeting_id,
                "location": hit.location,
                "source_offset_start": hit.source_offset_start,
                "source_offset_end": hit.source_offset_end,
                "source_start_ms": hit.source_start_ms,
                "source_end_ms": hit.source_end_ms,
            }
            for hit in hits
        ],
        "page": {"page": page, "page_size": page_size, "total": total},
    }


@mcp.tool(description="Ask the grounded assistant; answers include server-derived citations.")
async def ask_knowledge(
    token: str, question: str, conversation_id: int | None = None
) -> dict[str, Any]:
    """Ask the shared RAG application service without exposing transport internals."""

    owner_id = _authenticate(token)
    if not question.strip():
        raise ValueError("MCP_INVALID_ARGUMENT: question must not be blank")
    with SessionFactory() as session:
        answer = await RAGService(session).ask(owner_id, question, conversation_id=conversation_id)
    return {
        "conversation_id": answer.conversation_id,
        "message_id": answer.message_id,
        "answer": answer.answer,
        "evidence_sufficient": answer.evidence_sufficient,
        "citations": [citation.as_dict() for citation in answer.citations],
    }


@mcp.tool(description="List owner-scoped topics and projects.")
def list_topics(token: str, page: int = 1, page_size: int = 25) -> dict[str, Any]:
    """List topics and projects through the knowledge view service."""

    owner_id = _authenticate(token)
    if page < 1 or not 1 <= page_size <= 100:
        raise ValueError("MCP_INVALID_ARGUMENT: pagination is invalid")
    with SessionFactory() as session:
        items, total = KnowledgeViewService(session).list_objects(
            owner_id, kind=None, page=page, page_size=page_size
        )
    items = tuple(item for item in items if item.kind in {"topic", "project"})
    return {
        "items": [
            {"id": item.id, "kind": item.kind, "title": item.title, "description": item.description}
            for item in items
        ],
        "page": {"page": page, "page_size": page_size, "total": total},
    }


@mcp.tool(description="Get one owner-scoped topic or project with related derived evidence.")
def get_topic(token: str, topic_id: int) -> dict[str, Any]:
    """Return one knowledge object through the shared source-grounded view service."""

    owner_id = _authenticate(token)
    with SessionFactory() as session:
        view = KnowledgeViewService(session).object(owner_id, topic_id)
    if view is None or view.item.kind not in {"topic", "project"}:
        raise ValueError("MCP_NOT_FOUND: topic does not exist")
    return {
        "item": {
            "id": view.item.id,
            "kind": view.item.kind,
            "title": view.item.title,
            "description": view.item.description,
            "metadata": view.item.metadata_json,
        },
        "related": [
            {"id": item.id, "kind": item.kind, "title": item.title} for item in view.related
        ],
        "artifacts": [
            {
                "id": item.artifact.id,
                "kind": item.artifact.kind,
                "title": item.artifact.title,
                "content": item.artifact.content,
                "sources": [_source(chunk) for chunk in item.sources],
            }
            for item in view.artifacts
        ],
    }


@mcp.tool(description="Get one owner-scoped document and its original content and chunks.")
def get_document(token: str, document_id: int) -> dict[str, Any]:
    """Return a document view with provenance through the shared service."""

    owner_id = _authenticate(token)
    with SessionFactory() as session:
        view = KnowledgeViewService(session).document(owner_id, document_id)
    if view is None:
        raise ValueError("MCP_NOT_FOUND: document does not exist")
    return {
        "id": view.document.id,
        "title": view.document.title,
        "original_name": view.source.original_name,
        "media_type": view.source.media_type,
        "extracted_text": view.document.extracted_text,
        "chunks": [_source(chunk) for chunk in view.chunks],
        "artifacts": [
            {
                "id": item.artifact.id,
                "kind": item.artifact.kind,
                "title": item.artifact.title,
                "content": item.artifact.content,
                "sources": [_source(chunk) for chunk in item.sources],
            }
            for item in view.artifacts
        ],
    }


@mcp.tool(description="Get one owner-scoped meeting transcript and derived evidence.")
def get_meeting(token: str, meeting_id: int) -> dict[str, Any]:
    """Return a meeting view with speaker and timestamp provenance."""

    owner_id = _authenticate(token)
    with SessionFactory() as session:
        view = KnowledgeViewService(session).meeting(owner_id, meeting_id)
    if view is None:
        raise ValueError("MCP_NOT_FOUND: meeting does not exist")
    return {
        "id": view.meeting.id,
        "title": view.meeting.title,
        "started_at": _iso(view.meeting.started_at),
        "ended_at": _iso(view.meeting.ended_at),
        "segments": [
            {
                "id": item.segment.id,
                "sequence": item.segment.sequence,
                "text": item.segment.text,
                "start_ms": item.segment.start_ms,
                "end_ms": item.segment.end_ms,
                "speaker_label": item.speaker.label if item.speaker else None,
                "speaker_name": item.speaker.display_name if item.speaker else None,
            }
            for item in view.segments
        ],
        "artifacts": [
            {
                "id": item.artifact.id,
                "kind": item.artifact.kind,
                "title": item.artifact.title,
                "content": item.artifact.content,
                "sources": [_source(chunk) for chunk in item.sources],
            }
            for item in view.artifacts
        ],
    }


def _actions(token: str, item_type: str, status: str | None = None) -> dict[str, Any]:
    owner_id = _authenticate(token)
    with SessionFactory() as session:
        items, total = ActionItemService(session).list(
            owner_id,
            item_type=item_type,  # type: ignore[arg-type]
            status=status,
            topic_id=None,
            project_id=None,
            source_type=None,
            assignee_user_id=None,
            date_from=None,
            date_to=None,
            page=1,
            page_size=100,
        )
    return {
        "items": [
            {
                "id": item.artifact.id,
                "type": item.item_type,
                "title": item.artifact.title,
                "content": item.artifact.content,
                "status": item.status,
                "created_at": _iso(item.artifact.created_at),
                "sources": [
                    {
                        "id": source.id,
                        "source_type": source.source_type,
                        "title": source.title,
                        **_source(source.chunk),
                    }
                    for source in item.sources
                ],
            }
            for item in items
        ],
        "page": {"page": 1, "page_size": 100, "total": total},
    }


@mcp.tool(description="List owner-scoped open tasks.")
def get_tasks(token: str) -> dict[str, Any]:
    return _actions(token, "task", status=None)


@mcp.tool(description="List owner-scoped open questions.")
def get_open_questions(token: str) -> dict[str, Any]:
    return _actions(token, "open_question", status="open")


@mcp.tool(description="List owner-scoped active decisions.")
def get_decisions(token: str) -> dict[str, Any]:
    return _actions(token, "decision", status="active")


def _write_user(token: str, scope: str, session: Any) -> int:
    """Authorize an opt-in write with a persisted scoped token."""

    user = ApiTokenService(session).authenticate(token, scope)
    if user is None:
        raise ValueError("MCP_SCOPE_REQUIRED: token is missing or lacks the requested scope")
    return user.id


if os.environ.get("MCP_WRITE_ENABLED", "false").casefold() in {"1", "true", "yes", "on"}:

    @mcp.tool(description="Update one task status; requires an opted-in tasks:write token.")
    def update_task_status(token: str, artifact_id: int, status: str) -> dict[str, Any]:
        """Call the same owner-scoped task service as the HTTP action view."""

        with SessionFactory() as session:
            owner_id = _write_user(token, "tasks:write", session)
            item = ActionItemService(session).update_status(owner_id, artifact_id, status)
        return {"id": item.artifact.id, "type": item.item_type, "status": item.status}

    @mcp.tool(description="Resolve a clarification; requires an opted-in knowledge:write token.")
    def resolve_clarification(
        token: str,
        clarification_id: int,
        action: str,
        selected_knowledge_object_ids: list[int] | None = None,
        new_topic_title: str | None = None,
    ) -> dict[str, Any]:
        """Call the same auditable clarification service as the HTTP workflow."""

        if action not in {"accept", "reject", "edit", "assign"}:
            raise ValueError("MCP_INVALID_ARGUMENT: unsupported clarification action")
        with SessionFactory() as session:
            owner_id = _write_user(token, "knowledge:write", session)
            item = ClarificationService(session).resolve(
                owner_id,
                clarification_id,
                action=action,  # type: ignore[arg-type]
                selected_knowledge_object_ids=selected_knowledge_object_ids or [],
                new_topic_title=new_topic_title,
            )
        return {"id": item.request.id, "status": item.request.status}


def main() -> None:
    """Run the MCP server using the SDK's default transport."""

    mcp.run()


if __name__ == "__main__":
    main()
