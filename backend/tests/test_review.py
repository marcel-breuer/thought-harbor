from datetime import UTC, datetime
from typing import Any

from thoughtharbor.domain.models import AnswerEvaluation, ConversationMessage, SavedSearch
from thoughtharbor.review import EvaluationService, SavedSearchService

NOW = datetime(2026, 9, 14, tzinfo=UTC)


def test_saved_search_create_keeps_filters_and_owner() -> None:
    session = MutationSession()

    item = SavedSearchService(session).create(
        7,
        name="Open questions",
        query="open question",
        filters={"source_type": "transcript"},
        enabled=True,
    )

    assert item.owner_id == 7
    assert item.name == "Open questions"
    assert item.filters_json == {"source_type": "transcript"}
    assert session.committed


def test_evaluation_rejects_foreign_or_non_assistant_messages() -> None:
    assert EvaluationService(ScalarSession([None])).submit(
        7, 10, rating="supported", notes=None
    ) is None
    assert EvaluationService(ScalarSession([None])).submit(
        7, 11, rating="supported", notes=None
    ) is None


def test_evaluation_updates_one_owner_scoped_message() -> None:
    message = ConversationMessage(
        id=10,
        conversation_id=20,
        owner_id=7,
        role="assistant",
        content="Grounded answer",
    )
    session = MutationSession(scalar_results=[message, None])

    result = EvaluationService(session).submit(
        7,
        10,
        rating="incomplete",
        notes="Needs a second source.",
    )

    assert result is not None
    assert result.rating == "incomplete"
    assert result.notes == "Needs a second source."
    assert result.conversation_id == 20
    assert session.committed


class MutationSession:
    def __init__(self, *, scalar_results: list[Any] | None = None) -> None:
        self.scalar_results = scalar_results or []
        self.added: list[Any] = []
        self.committed = False

    def add(self, item: Any) -> None:
        self.added.append(item)
        if isinstance(item, SavedSearch):
            item.id = 1
            item.created_at = NOW
            item.updated_at = NOW
        if isinstance(item, AnswerEvaluation):
            item.id = 2
            item.created_at = NOW
            item.updated_at = NOW

    def commit(self) -> None:
        self.committed = True

    def refresh(self, item: Any) -> None:
        return None

    def scalar(self, statement: Any) -> Any:
        return self.scalar_results.pop(0) if self.scalar_results else None


class ScalarSession:
    def __init__(self, results: list[Any]) -> None:
        self.results = results

    def scalar(self, statement: Any) -> Any:
        return self.results.pop(0) if self.results else None
