"""add routing types, alias sets, and advanced routing fields

Revision ID: phase6_001
Revises: a1b2c3d4e5f6
Create Date: 2026-03-31 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase6_001'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create alias_sets table
    op.create_table(
        'alias_sets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create alias_mappings table
    op.create_table(
        'alias_mappings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('alias_set_id', sa.Uuid(), nullable=False),
        sa.Column('alias_name', sa.String(255), nullable=False),
        sa.Column('target_type', sa.String(50), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['alias_set_id'], ['alias_sets.id']),
    )

    # Add new columns to existing tables
    op.add_column('activity_templates', sa.Column('routing_type', sa.String(50), nullable=True, server_default='conditional'))
    op.add_column('activity_templates', sa.Column('performer_list', sa.JSON(), nullable=True))
    op.add_column('flow_templates', sa.Column('display_label', sa.String(255), nullable=True))
    op.add_column('activity_instances', sa.Column('current_performer_index', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('workflow_instances', sa.Column('alias_snapshot', sa.JSON(), nullable=True))
    op.add_column('process_templates', sa.Column('alias_set_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_process_templates_alias_set_id',
        'process_templates', 'alias_sets',
        ['alias_set_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_process_templates_alias_set_id', 'process_templates', type_='foreignkey')
    op.drop_column('process_templates', 'alias_set_id')
    op.drop_column('workflow_instances', 'alias_snapshot')
    op.drop_column('activity_instances', 'current_performer_index')
    op.drop_column('flow_templates', 'display_label')
    op.drop_column('activity_templates', 'performer_list')
    op.drop_column('activity_templates', 'routing_type')
    op.drop_table('alias_mappings')
    op.drop_table('alias_sets')
