"""Add each user's preferred OpenRouter generation model."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("preferred_ai_model", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preferred_ai_model")
