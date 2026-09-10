from fastapi.testclient import TestClient

from thoughtharbor.api.main import app

client = TestClient(app)


def test_versioned_health_and_request_id() -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request-123"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"] == "test-request-123"


def test_validation_errors_use_public_envelope() -> None:
    response = client.get("/api/v1/_contract/pagination?page=0")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["details"][0]["location"] == ["query", "page"]
    assert payload["request_id"] == response.headers["x-request-id"]


def test_private_auth_resource_requires_a_session() -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_openapi_has_versioned_contract_metadata() -> None:
    response = client.get("/openapi.json")
    document = response.json()

    assert response.status_code == 200
    assert document["info"]["title"] == "ThoughtHarbor API"
    assert "/api/v1/health" in document["paths"]
    assert "/api/v1/ready" in document["paths"]
    assert "/api/v1/settings/diagnostics" in document["paths"]
    assert "/api/v1/settings/configuration" in document["paths"]
    assert "/api/v1/clarifications" in document["paths"]
    assert "/api/v1/clarifications/{clarification_id}/resolve" in document["paths"]
    assert "/api/v1/search" in document["paths"]
    assert "/api/v1/chat" in document["paths"]
    assert "/api/v1/knowledge/objects" in document["paths"]
    assert "/api/v1/knowledge/objects/{object_id}" in document["paths"]
    assert "/api/v1/knowledge/documents/{document_id}" in document["paths"]
    assert "/api/v1/knowledge/meetings/{meeting_id}" in document["paths"]
    assert "/api/v1/knowledge/action-items" in document["paths"]
    assert "/api/v1/knowledge/action-items/{artifact_id}" in document["paths"]
    assert "/api/v1/dashboard" in document["paths"]
    assert "/api/v1/inbox" in document["paths"]
    assert "/api/v1/inbox/upload" in document["paths"]
    assert "/api/v1/meetings/{meeting_id}/speakers" in document["paths"]
    assert "/api/v1/meetings/{meeting_id}/speakers/{speaker_id}" in document["paths"]
    assert "/health" not in document["paths"]
