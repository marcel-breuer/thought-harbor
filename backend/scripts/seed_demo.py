"""Idempotently import a safe, local demo dataset and test user."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thoughtharbor.auth.security import hash_password  # noqa: E402
from thoughtharbor.domain.models import (  # noqa: E402
    ArtifactSource,
    ContentChunk,
    DerivedArtifact,
    Document,
    Meeting,
    SourceFile,
    Speaker,
    Transcript,
    TranscriptSegment,
    User,
)


@dataclass(frozen=True, slots=True)
class SeedSummary:
    """Report the stable identifiers created or reused by the import."""

    user_id: int
    document_id: int
    meeting_id: int


def seed_demo(
    session: Session,
    *,
    email: str = "demo@example.local",
    password: str = "demo-password-change-me",
) -> SeedSummary:
    """Create or reuse the demo account and representative source records."""

    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            display_name="Demo User",
            password_hash=hash_password(password),
            role="user",
        )
        session.add(user)
        session.flush()

    document_source = _get_or_create(
        session,
        SourceFile,
        {"storage_key": "demo/architecture-notes.txt"},
        owner_id=user.id,
        original_name="architecture-notes.txt",
        media_type="text/plain",
        byte_size=128,
        sha256="1" * 64,
        ingestion_status="complete",
    )
    document = _get_or_create(
        session,
        Document,
        {"source_file_id": document_source.id},
        owner_id=user.id,
        title="Architecture notes",
        extracted_text="ThoughtHarbor keeps derived knowledge traceable to source content.",
    )
    document_chunk = _get_or_create(
        session,
        ContentChunk,
        {"document_id": document.id, "sequence": 0},
        owner_id=user.id,
        text="ThoughtHarbor keeps derived knowledge traceable to source content.",
        source_offset_start=0,
        source_offset_end=69,
        location={"page": 1},
    )
    summary = _get_or_create(
        session,
        DerivedArtifact,
        {"owner_id": user.id, "kind": "summary", "title": "Traceability principle"},
        content="Derived knowledge retains a link to its supporting source chunk.",
    )
    _get_or_create(
        session,
        ArtifactSource,
        {"artifact_id": summary.id, "content_chunk_id": document_chunk.id},
        source_role="supporting",
        supporting_excerpt=document_chunk.text,
    )

    meeting_source = _get_or_create(
        session,
        SourceFile,
        {"storage_key": "demo/product-planning.txt"},
        owner_id=user.id,
        original_name="product-planning.txt",
        media_type="text/plain",
        byte_size=192,
        sha256="2" * 64,
        ingestion_status="complete",
    )
    meeting = _get_or_create(
        session,
        Meeting,
        {"owner_id": user.id, "title": "Product planning demo"},
        source_file_id=meeting_source.id,
        started_at=datetime(2026, 1, 15, 10, tzinfo=UTC),
        ended_at=datetime(2026, 1, 15, 11, tzinfo=UTC),
    )
    speaker = _get_or_create(
        session,
        Speaker,
        {"meeting_id": meeting.id, "label": "SPEAKER_00"},
        owner_id=user.id,
        display_name="Demo User",
    )
    transcript = _get_or_create(
        session,
        Transcript,
        {"meeting_id": meeting.id},
        owner_id=user.id,
        language="en",
        provider="demo",
        model="fixture",
    )
    segment = _get_or_create(
        session,
        TranscriptSegment,
        {"transcript_id": transcript.id, "sequence": 0},
        speaker_id=speaker.id,
        text="We will keep every decision linked to the meeting evidence.",
        start_ms=0,
        end_ms=4200,
        source_offset_start=0,
        source_offset_end=62,
    )
    meeting_chunk = _get_or_create(
        session,
        ContentChunk,
        {"transcript_segment_id": segment.id, "sequence": 0},
        owner_id=user.id,
        text=segment.text,
        source_start_ms=segment.start_ms,
        source_end_ms=segment.end_ms,
        location={"meeting_id": meeting.id},
    )
    decision = _get_or_create(
        session,
        DerivedArtifact,
        {"owner_id": user.id, "kind": "decision", "title": "Keep evidence links"},
        content="Decisions should retain a link to the meeting evidence.",
    )
    _get_or_create(
        session,
        ArtifactSource,
        {"artifact_id": decision.id, "content_chunk_id": meeting_chunk.id},
        source_role="supporting",
        supporting_excerpt=meeting_chunk.text,
    )

    session.commit()
    return SeedSummary(user_id=user.id, document_id=document.id, meeting_id=meeting.id)


def _get_or_create[ModelT](
    session: Session,
    model: type[ModelT],
    identity: dict[str, Any],
    **values: Any,
) -> ModelT:
    """Find a fixture by its stable identity or insert it once."""

    clauses = [getattr(model, key) == value for key, value in identity.items()]
    existing = session.scalar(select(model).where(*clauses))
    if existing is not None:
        return existing
    created = model(**identity, **values)  # type: ignore[call-arg]
    session.add(created)
    session.flush()
    return created


def main() -> None:
    """Run the fixture import from the configured local database."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--email", default="demo@example.local")
    parser.add_argument("--password", default="demo-password-change-me")
    args = parser.parse_args()
    if os.environ.get("TH_ENVIRONMENT", "development").lower() == "production":
        raise SystemExit("Demo data import is disabled when TH_ENVIRONMENT=production")

    database_url = args.database_url or (
        "postgresql+psycopg://thoughtharbor:thoughtharbor@localhost:5432/thoughtharbor"
    )
    engine = create_engine(database_url)
    with Session(engine) as session:
        summary = seed_demo(session, email=args.email, password=args.password)
    print(
        "Demo data ready for the configured local database "
        f"(user_id={summary.user_id}, document_id={summary.document_id}, "
        f"meeting_id={summary.meeting_id}, finished={datetime.now(UTC).isoformat()})"
    )


if __name__ == "__main__":
    main()
