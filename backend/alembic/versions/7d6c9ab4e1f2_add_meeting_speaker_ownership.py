"""add meeting ownership to speakers.

Revision ID: 7d6c9ab4e1f2
Revises: 02edca43c36f
Create Date: 2026-09-09 22:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d6c9ab4e1f2"
down_revision: str | None = "02edca43c36f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("speakers", sa.Column("meeting_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_speakers_meeting_id_meetings",
        "speakers",
        "meetings",
        ["meeting_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_speakers_meeting_id", "speakers", ["meeting_id"], unique=False)
    op.create_unique_constraint("uq_speakers_meeting_label", "speakers", ["meeting_id", "label"])


def downgrade() -> None:
    op.drop_constraint("uq_speakers_meeting_label", "speakers", type_="unique")
    op.drop_index("ix_speakers_meeting_id", table_name="speakers")
    op.drop_constraint("fk_speakers_meeting_id_meetings", "speakers", type_="foreignkey")
    op.drop_column("speakers", "meeting_id")
