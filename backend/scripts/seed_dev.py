"""Create a small local knowledge graph for development and manual testing."""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thoughtharbor.domain.models import (  # noqa: E402
    ArtifactSource,
    ContentChunk,
    DerivedArtifact,
    Document,
    SourceFile,
    User,
)


def main() -> None:
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://thoughtharbor:thoughtharbor@localhost:5432/thoughtharbor",
    )
    engine = create_engine(database_url)

    with Session(engine) as session:
        user = User(email="dev@example.local", display_name="Development User")
        session.add(user)
        session.flush()

        source_file = SourceFile(
            owner_id=user.id,
            storage_key="dev/architecture-notes.txt",
            original_name="architecture-notes.txt",
            media_type="text/plain",
            byte_size=128,
            sha256="0" * 64,
            ingestion_status="complete",
        )
        session.add(source_file)
        session.flush()

        document = Document(
            owner_id=user.id,
            source_file_id=source_file.id,
            title="Architecture notes",
            extracted_text="ThoughtHarbor keeps derived knowledge traceable to source content.",
        )
        session.add(document)
        session.flush()

        chunk = ContentChunk(
            owner_id=user.id,
            document_id=document.id,
            sequence=0,
            text="ThoughtHarbor keeps derived knowledge traceable to source content.",
            source_offset_start=0,
            source_offset_end=69,
            location={"page": 1},
        )
        session.add(chunk)
        session.flush()

        artifact = DerivedArtifact(
            owner_id=user.id,
            kind="summary",
            title="Traceability principle",
            content="Derived knowledge retains a link to its supporting source chunk.",
        )
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactSource(
                artifact_id=artifact.id,
                content_chunk_id=chunk.id,
                source_role="supporting",
                supporting_excerpt=chunk.text,
            )
        )
        session.commit()
        print(f"Seeded development graph for user {user.id} at {datetime.now(UTC).isoformat()}")


if __name__ == "__main__":
    main()
