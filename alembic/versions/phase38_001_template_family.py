"""phase38_001_template_family

Revision ID: phase38_001
Revises: phase37_001
Create Date: 2026-04-15

Add template_family_id column to process_templates for concurrent
template versioning. Backfill existing templates as their own family root.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "phase38_001"
down_revision: Union[str, None] = "phase37_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column as nullable first
    op.add_column(
        "process_templates",
        sa.Column("template_family_id", sa.Uuid(), nullable=True),
    )

    # 2. Backfill: each existing template becomes its own family root
    op.execute(
        "UPDATE process_templates SET template_family_id = id WHERE template_family_id IS NULL"
    )

    # 3. Make column NOT NULL after backfill
    op.alter_column(
        "process_templates",
        "template_family_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )

    # 4. Add composite index for fast latest-version lookups
    op.create_index(
        "ix_process_templates_family_installed",
        "process_templates",
        ["template_family_id", "is_installed"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_process_templates_family_installed",
        table_name="process_templates",
    )
    op.drop_column("process_templates", "template_family_id")
