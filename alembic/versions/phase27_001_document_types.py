"""phase27_001_document_types

Revision ID: phase27_001
Revises: e790b1fcc622
Create Date: 2026-04-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "phase27_001"
down_revision: Union[str, None] = "e790b1fcc622"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata_schema",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("parent_type_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.ForeignKeyConstraint(
            ["parent_type_id"],
            ["document_types.id"],
            name="fk_document_types_parent_type_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_document_types_name"),
    )

    op.add_column(
        "documents",
        sa.Column("document_type_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_documents_document_type_id",
        "documents",
        "document_types",
        ["document_type_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_documents_document_type_id",
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "document_type_id")
    op.drop_table("document_types")
