from fastapi.testclient import TestClient

from thoughtharbor.api.main import app
from thoughtharbor.mcp.server import mcp
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
