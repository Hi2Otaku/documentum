"""phase31_001_document_relationships

Revision ID: phase31_001
Revises: phase28_001
Create Date: 2026-04-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "phase31_001"
down_revision: Union[str, None] = "phase28_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create relationshiptype enum
    relationshiptype = sa.Enum(
        "supersedes", "references", "is_part_of", "related_to",
        name="relationshiptype",
    )
    relationshiptype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "document_relationships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("target_document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("relationship_type", relationshiptype, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint(
            "source_document_id", "target_document_id", "relationship_type",
            name="uq_document_relationship",
        ),
    )
    op.create_index("ix_document_relationships_source", "document_relationships", ["source_document_id"])
    op.create_index("ix_document_relationships_target", "document_relationships", ["target_document_id"])


def downgrade() -> None:
    op.drop_index("ix_document_relationships_target")
    op.drop_index("ix_document_relationships_source")
    op.drop_table("document_relationships")
    sa.Enum(name="relationshiptype").drop(op.get_bind(), checkfirst=True)
