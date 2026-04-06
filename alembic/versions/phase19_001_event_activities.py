"""add event activity columns to activity_templates

Revision ID: phase19_001
Revises: phase18_001
Create Date: 2026-04-06 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase19_001'
down_revision: Union[str, None] = 'phase18_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Add EVENT to ActivityType enum (PostgreSQL only)
    if bind.dialect.name != "sqlite":
        op.execute("ALTER TYPE activitytype ADD VALUE IF NOT EXISTS 'event'")

    # ActivityTemplate: event_type_filter and event_filter_config
    op.add_column(
        "activity_templates",
        sa.Column("event_type_filter", sa.String(255), nullable=True),
    )
    op.add_column(
        "activity_templates",
        sa.Column("event_filter_config", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("activity_templates", "event_filter_config")
    op.drop_column("activity_templates", "event_type_filter")

    # Note: PostgreSQL does not support removing values from enums.
    # The 'event' value will remain in the activitytype enum.
