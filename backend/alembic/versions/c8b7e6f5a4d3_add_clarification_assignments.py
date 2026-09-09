"""add multiple selected knowledge objects to clarifications.

Revision ID: c8b7e6f5a4d3
Revises: 7d6c9ab4e1f2
Create Date: 2026-09-09 22:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8b7e6f5a4d3"
down_revision: str | None = "7d6c9ab4e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clarification_requests",
        sa.Column(
            "selected_knowledge_object_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("clarification_requests", "selected_knowledge_object_ids", server_default=None)


def downgrade() -> None:
    op.drop_column("clarification_requests", "selected_knowledge_object_ids")
