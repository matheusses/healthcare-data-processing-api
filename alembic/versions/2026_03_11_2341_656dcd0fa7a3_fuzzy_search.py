"""fuzzy-search

Revision ID (hash): 656dcd0fa7a3
Revises: 772d3bd63787
Create Date (timestamp): 2026-03-11 23:41:46.371550+00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "656dcd0fa7a3"
down_revision: Union[str, None] = "772d3bd63787"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE INDEX idx_patients_name_trgm ON patients USING GIN (name gin_trgm_ops)")
    op.execute(
        "CREATE INDEX idx_patients_document_number_trgm ON patients "
        "USING GIN (document_number gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_patients_name_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_patients_document_number_trgm;")
