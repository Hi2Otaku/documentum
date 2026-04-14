"""phase30_001_search_columns

Revision ID: phase30_001
Revises: phase28_001
Create Date: 2026-04-14

Add search_vector (TSVECTOR with GIN index) and extraction_status to documents,
fulltext_content to document_versions for full-text search support.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "phase30_001"
down_revision: Union[str, None] = "phase28_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents ADD COLUMN search_vector tsvector")
    op.execute(
        "ALTER TABLE documents ADD COLUMN extraction_status varchar(20) NOT NULL DEFAULT 'pending'"
    )
    op.execute("ALTER TABLE document_versions ADD COLUMN fulltext_content text")
    op.execute(
        "CREATE INDEX ix_documents_search_vector ON documents USING gin (search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_search_vector")
    op.execute("ALTER TABLE document_versions DROP COLUMN IF EXISTS fulltext_content")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS extraction_status")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS search_vector")
