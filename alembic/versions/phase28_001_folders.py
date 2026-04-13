"""phase28_001_folders

Revision ID: phase28_001
Revises: phase27_001
Create Date: 2026-04-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "phase28_001"
down_revision: Union[str, None] = "phase27_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the folders table
    op.create_table(
        "folders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column(
            "is_cabinet",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["folders.id"],
            name="fk_folders_parent_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_folders_parent_id", "folders", ["parent_id"])

    # Create the document_folders association table
    op.create_table(
        "document_folders",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filed_by", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["folder_id"],
            ["folders.id"],
        ),
        sa.PrimaryKeyConstraint("document_id", "folder_id"),
    )


def downgrade() -> None:
    op.drop_table("document_folders")
    op.drop_index("ix_folders_parent_id", table_name="folders")
    op.drop_table("folders")
