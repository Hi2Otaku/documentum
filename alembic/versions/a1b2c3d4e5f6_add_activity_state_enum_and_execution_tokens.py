"""add activity_state enum and execution_tokens

Revision ID: a1b2c3d4e5f6
Revises: 3efa9fa4be2a
Create Date: 2026-03-30 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3efa9fa4be2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the activitystate enum type
    activitystate = sa.Enum('dormant', 'active', 'paused', 'complete', 'error', name='activitystate')
    activitystate.create(op.get_bind(), checkfirst=True)

    # Alter activity_instances.state from VARCHAR(50) to activitystate enum
    op.alter_column(
        'activity_instances',
        'state',
        existing_type=sa.String(50),
        type_=sa.Enum('dormant', 'active', 'paused', 'complete', 'error', name='activitystate'),
        existing_nullable=False,
        existing_server_default='dormant',
        postgresql_using='state::activitystate',
    )

    # Create execution_tokens table
    op.create_table(
        'execution_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workflow_instance_id', sa.Uuid(), nullable=False),
        sa.Column('flow_template_id', sa.Uuid(), nullable=False),
        sa.Column('source_activity_instance_id', sa.Uuid(), nullable=False),
        sa.Column('target_activity_template_id', sa.Uuid(), nullable=False),
        sa.Column('is_consumed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['workflow_instance_id'], ['workflow_instances.id']),
        sa.ForeignKeyConstraint(['flow_template_id'], ['flow_templates.id']),
        sa.ForeignKeyConstraint(['source_activity_instance_id'], ['activity_instances.id']),
        sa.ForeignKeyConstraint(['target_activity_template_id'], ['activity_templates.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_execution_tokens_workflow_instance_id', 'execution_tokens', ['workflow_instance_id'])


def downgrade() -> None:
    # Drop execution_tokens table
    op.drop_index('ix_execution_tokens_workflow_instance_id', table_name='execution_tokens')
    op.drop_table('execution_tokens')

    # Revert activity_instances.state from enum back to VARCHAR(50)
    op.alter_column(
        'activity_instances',
        'state',
        existing_type=sa.Enum('dormant', 'active', 'paused', 'complete', 'error', name='activitystate'),
        type_=sa.String(50),
        existing_nullable=False,
        existing_server_default='dormant',
    )

    # Drop the activitystate enum type
    sa.Enum(name='activitystate').drop(op.get_bind(), checkfirst=True)
