from types import SimpleNamespace

import pytest

from thoughtharbor.domain.models import User
from thoughtharbor.mcp import server


def test_mcp_source_mapping_preserves_exact_provenance() -> None:
    source = SimpleNamespace(
        id=12,
        text="Evidence",
        location={"page": 2},
        source_offset_start=4,
        source_offset_end=12,
        source_start_ms=None,
        source_end_ms=None,
    )

    assert server._source(source) == {
        "chunk_id": 12,
        "text": "Evidence",
        "location": {"page": 2},
        "source_offset_start": 4,
        "source_offset_end": 12,
        "source_start_ms": None,
        "source_end_ms": None,
    }


def test_mcp_write_authorization_requires_the_requested_scope(monkeypatch) -> None:
    def authenticate(_: object, token: str, scope: str) -> User | None:
        return User(id=7) if token == "scoped" and scope == "tasks:write" else None

    monkeypatch.setattr(server.ApiTokenService, "authenticate", authenticate)

    assert server._write_user("scoped", "tasks:write", object()) == 7
    with pytest.raises(ValueError, match="MCP_SCOPE_REQUIRED"):
        server._write_user("scoped", "knowledge:write", object())
