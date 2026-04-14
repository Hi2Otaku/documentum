"""phase31_001_document_relationships

Revision ID: phase31_001
Revises: phase28_001
Create Date: 2026-04-14

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "phase31_001"
down_revision: Union[str, None] = "phase28_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw DDL to avoid duplicate enum errors (same pattern as Phase 29)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE relationshiptype AS ENUM ('supersedes', 'references', 'is_part_of', 'related_to');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS document_relationships (
            id UUID PRIMARY KEY,
            source_document_id UUID NOT NULL REFERENCES documents(id),
            target_document_id UUID NOT NULL REFERENCES documents(id),
            relationship_type relationshiptype NOT NULL,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by VARCHAR(255),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            CONSTRAINT uq_document_relationship UNIQUE (source_document_id, target_document_id, relationship_type)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_relationships_source ON document_relationships (source_document_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_relationships_target ON document_relationships (target_document_id);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_relationships_target;")
    op.execute("DROP INDEX IF EXISTS ix_document_relationships_source;")
    op.execute("DROP TABLE IF EXISTS document_relationships;")
    op.execute("DROP TYPE IF EXISTS relationshiptype;")
