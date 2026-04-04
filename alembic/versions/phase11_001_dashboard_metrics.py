"""add expected_duration_hours and metrics_summary table

Revision ID: phase11_001
Revises: phase10_001
Create Date: 2026-04-04 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase11_001'
down_revision: Union[str, None] = 'phase10_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add expected_duration_hours to activity_templates for SLA tracking
    op.add_column('activity_templates', sa.Column(
        'expected_duration_hours', sa.Float(), nullable=True
    ))

    # Create metrics_summary table for pre-aggregated dashboard chart data
    op.create_table(
        'metrics_summary',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('metric_type', sa.String(50), nullable=False, index=True),
        sa.Column('template_id', sa.Uuid(), sa.ForeignKey('process_templates.id'), nullable=True),
        sa.Column('dimension_key', sa.String(255), nullable=False),
        sa.Column('dimension_label', sa.String(255), nullable=True),
        sa.Column('numeric_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('count_value', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('metrics_summary')
    op.drop_column('activity_templates', 'expected_duration_hours')
