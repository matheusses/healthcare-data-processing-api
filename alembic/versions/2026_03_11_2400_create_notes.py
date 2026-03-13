"""create notes table

Revision ID (hash): a1b2c3d4e5f6
Revises: 656dcd0fa7a3
Create Date (timestamp): 2026-03-11 24:00:00+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "656dcd0fa7a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notes_patient_id", "notes", ["patient_id"], unique=False)
    op.create_index("ix_notes_recorded_at", "notes", ["recorded_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notes_recorded_at", table_name="notes")
    op.drop_index("ix_notes_patient_id", table_name="notes")
    op.drop_table("notes")
