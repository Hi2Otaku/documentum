"""add_folder_acl

Revision ID: phase29_001
Revises: phase28_001
Create Date: 2026-04-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "phase29_001"
down_revision: Union[str, None] = "phase28_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Use create_type=False since permissionlevel enum already exists from document_acl migration
permissionlevel_enum = sa.Enum(
    "read", "write", "delete", "admin",
    name="permissionlevel",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "folder_acl",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("principal_id", sa.Uuid(), nullable=False),
        sa.Column("principal_type", sa.String(20), nullable=False),
        sa.Column("permission_level", permissionlevel_enum, nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], name="fk_folder_acl_folder_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "folder_id", "principal_id", "principal_type", "permission_level",
            name="uq_folder_acl_entry",
        ),
    )
    op.create_index("ix_folder_acl_folder_id", "folder_acl", ["folder_id"])


def downgrade() -> None:
    op.drop_index("ix_folder_acl_folder_id", table_name="folder_acl")
    op.drop_table("folder_acl")
