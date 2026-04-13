"""add_folder_acl

Revision ID: phase29_001
Revises: phase28_001
Create Date: 2026-04-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "phase29_001"
down_revision: Union[str, None] = "phase28_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw DDL to avoid SQLAlchemy re-creating the permissionlevel enum
    # which already exists from the document_acl migration.
    op.execute(sa.text("""
        CREATE TABLE folder_acl (
            id UUID NOT NULL,
            folder_id UUID NOT NULL REFERENCES folders(id),
            principal_id UUID NOT NULL,
            principal_type VARCHAR(20) NOT NULL,
            permission_level permissionlevel NOT NULL,
            created_by VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            CONSTRAINT pk_folder_acl PRIMARY KEY (id),
            CONSTRAINT uq_folder_acl_entry UNIQUE (folder_id, principal_id, principal_type, permission_level)
        )
    """))
    op.execute(sa.text("CREATE INDEX ix_folder_acl_folder_id ON folder_acl (folder_id)"))


def downgrade() -> None:
    op.drop_index("ix_folder_acl_folder_id", table_name="folder_acl")
    op.drop_table("folder_acl")
