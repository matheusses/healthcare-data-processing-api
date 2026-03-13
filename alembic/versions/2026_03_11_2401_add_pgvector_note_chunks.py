"""add pgvector and note_chunks table

Revision ID (hash): b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date (timestamp): 2026-03-11 24:01:00+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Default embedding dimension (OpenAI text-embedding-3-small)
VECTOR_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.create_table(
        "note_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "chunk_metadata", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_note_chunks_note_id", "note_chunks", ["note_id"], unique=False)
    op.execute(f"ALTER TABLE note_chunks ADD COLUMN embedding vector({VECTOR_DIM});")
    op.execute(
        "CREATE INDEX ix_note_chunks_embedding_hnsw ON note_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_note_chunks_embedding_hnsw;")
    op.drop_index("ix_note_chunks_note_id", table_name="note_chunks")
    op.drop_table("note_chunks")
    op.execute("DROP EXTENSION IF EXISTS vector;")
