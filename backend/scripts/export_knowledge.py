"""Export one owner's knowledge and original files without cloud dependencies."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from thoughtharbor.db.session import SessionFactory
from thoughtharbor.domain.models import (
    AIClassification,
    ArtifactSource,
    ClarificationRequest,
    Decision,
    DerivedArtifact,
    Document,
    KnowledgeObject,
    KnowledgeRelation,
    Meeting,
    OpenQuestion,
    SourceFile,
    Task,
    Transcript,
    TranscriptSegment,
)
from thoughtharbor.storage.service import LocalFileStorage

EXPORT_VERSION = 1
MODELS = {
    "source_files": SourceFile,
    "documents": Document,
    "meetings": Meeting,
    "transcripts": Transcript,
    "transcript_segments": TranscriptSegment,
    "knowledge_objects": KnowledgeObject,
    "knowledge_relations": KnowledgeRelation,
    "derived_artifacts": DerivedArtifact,
    "artifact_sources": ArtifactSource,
    "tasks": Task,
    "decisions": Decision,
    "open_questions": OpenQuestion,
    "ai_classifications": AIClassification,
    "clarification_requests": ClarificationRequest,
}
DERIVED_OWNER_MODELS = {"artifact_sources", "tasks", "decisions", "open_questions"}


def _value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _row(item: Any) -> dict[str, Any]:
    return {
        column.name: _value(getattr(item, column.name))
        for column in item.__table__.columns
        if column.name not in {"password_hash", "token_hash"}
    }


def _safe_filename(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "source"
    return stem[:180]


def export(owner_id: int, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    original_directory = output / "original-files"
    original_directory.mkdir()
    records: dict[str, list[dict[str, Any]]] = {}
    with SessionFactory() as session:
        for name, model in MODELS.items():
            if name == "transcript_segments":
                statement = (
                    select(model)
                    .join(Transcript, model.transcript_id == Transcript.id)
                    .where(Transcript.owner_id == owner_id)
                )
            elif name in DERIVED_OWNER_MODELS:
                statement = (
                    select(model)
                    .join(DerivedArtifact, model.artifact_id == DerivedArtifact.id)
                    .where(DerivedArtifact.owner_id == owner_id)
                )
            else:
                statement = select(model).where(model.owner_id == owner_id)
            records[name] = [_row(item) for item in session.scalars(statement)]

    storage = LocalFileStorage.from_environment()
    copied_files: list[dict[str, Any]] = []
    for source in records["source_files"]:
        storage_key = source.get("storage_key")
        if not isinstance(storage_key, str):
            continue
        source_path = (
            original_directory / f"{source['id']}-{_safe_filename(source['original_name'])}"
        )
        try:
            with (
                storage.open_read(storage_key) as input_file,
                source_path.open("wb") as output_file,
            ):
                shutil.copyfileobj(input_file, output_file)
        except (FileNotFoundError, OSError):
            continue
        copied_files.append(
            {"source_file_id": source["id"], "path": str(source_path.relative_to(output))}
        )

    manifest = {
        "format": "thoughtharbor-knowledge-export",
        "version": EXPORT_VERSION,
        "owner_id": owner_id,
        "generated_at": datetime.now().astimezone().isoformat(),
        "record_counts": {name: len(items) for name, items in records.items()},
        "original_files": copied_files,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (output / "knowledge.json").write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
    lines = ["# ThoughtHarbor knowledge export", "", f"Owner: `{owner_id}`", ""]
    lines.append("## Original sources")
    lines.extend(
        f"- **{item['original_name']}** — {item.get('ingestion_status', 'unknown')}"
        for item in records["source_files"]
    )
    lines.append("\n## Knowledge objects")
    lines.extend(
        f"- **{item['title']}** ({item['kind']})"
        f"{(': ' + item['description']) if item.get('description') else ''}"
        for item in records["knowledge_objects"]
    )
    lines.append("\n## Derived artifacts")
    lines.extend(
        f"- **{item.get('title') or 'Untitled'}** ({item['kind']}): {item['content']}"
        for item in records["derived_artifacts"]
    )
    (output / "knowledge.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-id", type=int, required=True)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export(args.owner_id, args.output)


if __name__ == "__main__":
    main()
