from typing import Any

import pytest

from thoughtharbor.auth.tokens import ApiTokenService


def test_created_token_is_random_and_stored_only_as_a_hash() -> None:
    session = FakeSession()

    created = ApiTokenService(session).create(
        7,
        name="Local assistant",
        scopes=["knowledge:read"],
        expires_at=None,
    )

    assert created.plaintext.startswith("th_")
    assert created.token.token_prefix == created.plaintext[:12]
    assert created.token.token_hash != created.plaintext
    assert created.token.scopes == ["knowledge:read"]


def test_unknown_token_scope_is_rejected_before_persistence() -> None:
    session = FakeSession()

    with pytest.raises(ValueError, match="Unsupported token scope"):
        ApiTokenService(session).create(7, name="Bad", scopes=["admin"], expires_at=None)

    assert session.commits == 0


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.item: Any = None

    def add(self, item: Any) -> None:
        self.item = item
        item.id = 1

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, item: Any) -> None:
        return None
