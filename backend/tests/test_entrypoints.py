import pytest
from fastapi.testclient import TestClient

from thoughtharbor.api.main import app
from thoughtharbor.mcp.server import _authenticate, mcp
from thoughtharbor.workers.celery_app import celery_app


def test_api_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_shared_runtime_entrypoints_import() -> None:
    assert app.title == "ThoughtHarbor API"
    assert celery_app.main == "thoughtharbor"
    assert "thoughtharbor.process_source_file" in celery_app.tasks
    assert mcp.name == "ThoughtHarbor"


def test_read_only_mcp_toolset_is_registered_and_token_scoped(monkeypatch) -> None:
    monkeypatch.setenv("MCP_API_TOKEN", "local-test-token")
    monkeypatch.setenv("MCP_OWNER_ID", "7")

    assert _authenticate("local-test-token") == 7
    assert set(mcp._tool_manager._tools) == {
        "search_knowledge",
        "ask_knowledge",
        "list_topics",
        "get_topic",
        "get_document",
        "get_meeting",
        "get_tasks",
        "get_open_questions",
        "get_decisions",
    }


def test_mcp_rejects_missing_or_invalid_token(monkeypatch) -> None:
    monkeypatch.setenv("MCP_API_TOKEN", "local-test-token")
    monkeypatch.setenv("MCP_OWNER_ID", "7")

    with pytest.raises(ValueError, match="MCP_AUTH_REQUIRED"):
        _authenticate("wrong-token")
