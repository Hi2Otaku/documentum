"""phase39_001_advanced_joins

Revision ID: phase39_001
Revises: phase38_001
Create Date: 2026-04-15

Add advanced join semantics: N-of-M, cancelling, and timeout join types.
Adds join_threshold and join_timeout_hours to activity_templates,
join_timeout_started_at to activity_instances, and extends the
triggertype and activitystate enums.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "phase39_001"
down_revision: Union[str, None] = "phase38_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend triggertype enum with new join types
    op.execute("ALTER TYPE triggertype ADD VALUE IF NOT EXISTS 'n_of_m_join'")
    op.execute("ALTER TYPE triggertype ADD VALUE IF NOT EXISTS 'cancelling_join'")
    op.execute("ALTER TYPE triggertype ADD VALUE IF NOT EXISTS 'timeout_join'")

    # 2. Extend activitystate enum with CANCELLED
    op.execute("ALTER TYPE activitystate ADD VALUE IF NOT EXISTS 'cancelled'")

    # 3. Add join columns to activity_templates
    op.add_column(
        "activity_templates",
        sa.Column("join_threshold", sa.Integer(), nullable=True),
    )
    op.add_column(
        "activity_templates",
        sa.Column("join_timeout_hours", sa.Float(), nullable=True),
    )

    # 4. Add join_timeout_started_at to activity_instances
    op.add_column(
        "activity_instances",
        sa.Column("join_timeout_started_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 5. Index for efficient timeout polling
    op.create_index(
        "ix_activity_instances_wf_state",
        "activity_instances",
        ["workflow_instance_id", "state"],
    )


def downgrade() -> None:
    op.drop_index("ix_activity_instances_wf_state", table_name="activity_instances")
    op.drop_column("activity_instances", "join_timeout_started_at")
    op.drop_column("activity_templates", "join_timeout_hours")
    op.drop_column("activity_templates", "join_threshold")
    # Note: PostgreSQL does not support removing enum values in downgrade
