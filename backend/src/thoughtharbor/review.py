"""Application services for saved searches and grounded-answer review."""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thoughtharbor.domain.models import AnswerEvaluation, ConversationMessage, SavedSearch

EvaluationRating = Literal["supported", "incomplete", "incorrect"]


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    total: int
    supported: int
    incomplete: int
    incorrect: int


class SavedSearchService:
    """Manage reusable owner-scoped search definitions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, owner_id: int) -> tuple[SavedSearch, ...]:
        return tuple(
            self.session.scalars(
                select(SavedSearch)
                .where(SavedSearch.owner_id == owner_id, SavedSearch.deleted_at.is_(None))
                .order_by(SavedSearch.enabled.desc(), SavedSearch.name)
            )
        )

    def create(
        self,
        owner_id: int,
        *,
        name: str,
        query: str,
        filters: dict[str, object],
        enabled: bool,
    ) -> SavedSearch:
        item = SavedSearch(
            owner_id=owner_id,
            name=name,
            query=query,
            filters_json=filters,
            enabled=enabled,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def update(self, owner_id: int, search_id: int, **changes: object) -> SavedSearch | None:
        item = self._get(owner_id, search_id)
        if item is None:
            return None
        if "filters" in changes:
            item.filters_json = changes.pop("filters")  # type: ignore[assignment]
        for key, value in changes.items():
            if value is not None:
                setattr(item, key, value)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, owner_id: int, search_id: int) -> bool:
        item = self._get(owner_id, search_id)
        if item is None:
            return False
        item.deleted_at = func.now()
        self.session.commit()
        return True

    def _get(self, owner_id: int, search_id: int) -> SavedSearch | None:
        return self.session.scalar(
            select(SavedSearch).where(
                SavedSearch.id == search_id,
                SavedSearch.owner_id == owner_id,
                SavedSearch.deleted_at.is_(None),
            )
        )


class EvaluationService:
    """Persist and summarize owner feedback for grounded assistant answers."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def submit(
        self,
        owner_id: int,
        message_id: int,
        *,
        rating: EvaluationRating,
        notes: str | None,
    ) -> AnswerEvaluation | None:
        message = self.session.scalar(
            select(ConversationMessage).where(
                ConversationMessage.id == message_id,
                ConversationMessage.owner_id == owner_id,
                ConversationMessage.role == "assistant",
                ConversationMessage.deleted_at.is_(None),
            )
        )
        if message is None:
            return None
        evaluation = self.session.scalar(
            select(AnswerEvaluation).where(
                AnswerEvaluation.owner_id == owner_id,
                AnswerEvaluation.message_id == message_id,
            )
        )
        if evaluation is None:
            evaluation = AnswerEvaluation(
                owner_id=owner_id,
                conversation_id=message.conversation_id,
                message_id=message.id,
                rating=rating,
                notes=notes.strip() if notes else None,
            )
            self.session.add(evaluation)
        else:
            evaluation.rating = rating
            evaluation.notes = notes.strip() if notes else None
        self.session.commit()
        self.session.refresh(evaluation)
        return evaluation

    def list(
        self, owner_id: int, *, page: int, page_size: int
    ) -> tuple[tuple[AnswerEvaluation, ...], int]:
        statement = select(AnswerEvaluation).where(AnswerEvaluation.owner_id == owner_id)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        items = tuple(
            self.session.scalars(
                statement.order_by(AnswerEvaluation.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, int(total)

    def summary(self, owner_id: int) -> EvaluationSummary:
        rows = self.session.execute(
            select(AnswerEvaluation.rating, func.count())
            .where(AnswerEvaluation.owner_id == owner_id)
            .group_by(AnswerEvaluation.rating)
        )
        counts = {rating: count for rating, count in rows}
        return EvaluationSummary(
            total=sum(counts.values()),
            supported=int(counts.get("supported", 0)),
            incomplete=int(counts.get("incomplete", 0)),
            incorrect=int(counts.get("incorrect", 0)),
        )
