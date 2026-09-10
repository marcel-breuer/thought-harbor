"""Owner-scoped API token lifecycle and scope enforcement."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from thoughtharbor.domain.models import ApiToken, User

TOKEN_SCOPES = frozenset({"knowledge:read", "knowledge:write", "tasks:write", "uploads:write"})


@dataclass(frozen=True, slots=True)
class CreatedApiToken:
    token: ApiToken
    plaintext: str


class ApiTokenService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, owner_id: int, *, name: str, scopes: list[str], expires_at: datetime | None
    ) -> CreatedApiToken:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Token name must not be blank")
        normalized_scopes = list(dict.fromkeys(scopes))
        invalid = sorted(set(normalized_scopes) - TOKEN_SCOPES)
        if invalid:
            raise ValueError(f"Unsupported token scope: {', '.join(invalid)}")
        plaintext = f"th_{secrets.token_urlsafe(32)}"
        token = ApiToken(
            owner_id=owner_id,
            name=normalized_name,
            token_prefix=plaintext[:12],
            token_hash=_hash(plaintext),
            scopes=normalized_scopes,
            expires_at=expires_at,
        )
        self.session.add(token)
        self.session.commit()
        self.session.refresh(token)
        return CreatedApiToken(token, plaintext)

    def list(self, owner_id: int) -> tuple[ApiToken, ...]:
        return tuple(
            self.session.scalars(
                select(ApiToken)
                .where(ApiToken.owner_id == owner_id, ApiToken.deleted_at.is_(None))
                .order_by(ApiToken.created_at.desc())
            )
        )

    def revoke(self, owner_id: int, token_id: int) -> bool:
        token = self.session.scalar(
            select(ApiToken).where(
                ApiToken.id == token_id,
                ApiToken.owner_id == owner_id,
                ApiToken.deleted_at.is_(None),
            )
        )
        if token is None:
            return False
        token.deleted_at = datetime.now(UTC)
        self.session.commit()
        return True

    def authenticate(self, plaintext: str, required_scope: str) -> User | None:
        now = datetime.now(UTC)
        row = self.session.execute(
            select(ApiToken, User)
            .join(User, User.id == ApiToken.owner_id)
            .where(
                ApiToken.token_hash == _hash(plaintext),
                ApiToken.deleted_at.is_(None),
                User.deleted_at.is_(None),
                (ApiToken.expires_at.is_(None) | (ApiToken.expires_at > now)),
            )
        ).first()
        if row is None:
            return None
        token, user = row
        if required_scope not in token.scopes:
            return None
        token.last_used_at = now
        self.session.commit()
        return cast(User, user)


def _hash(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
