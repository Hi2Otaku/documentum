"""add timer escalation columns to activity_templates and work_items

Revision ID: phase17_001
Revises: phase16_001
Create Date: 2026-04-06 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "phase17_001"
down_revision: Union[str, None] = "phase16_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add escalation configuration to activity_templates
    op.add_column('activity_templates', sa.Column(
        'escalation_action', sa.String(50), nullable=True
    ))
    op.add_column('activity_templates', sa.Column(
        'warning_threshold_hours', sa.Float(), nullable=True
    ))

    # Add escalation tracking to work_items
    op.add_column('work_items', sa.Column(
        'is_escalated', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('work_items', sa.Column(
        'deadline_warning_sent', sa.Boolean(), nullable=False, server_default='false'
    ))


def downgrade() -> None:
    op.drop_column('work_items', 'deadline_warning_sent')
    op.drop_column('work_items', 'is_escalated')
    op.drop_column('activity_templates', 'warning_threshold_hours')
    op.drop_column('activity_templates', 'escalation_action')
