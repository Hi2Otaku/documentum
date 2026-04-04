"""add delegation fields work queues and suspended state

Revision ID: phase10_001
Revises: phase7_001
Create Date: 2026-04-04 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase10_001'
down_revision: Union[str, None] = 'phase7_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add delegation fields to users table
    op.add_column('users', sa.Column(
        'is_available', sa.Boolean(), nullable=False, server_default='true'
    ))
    op.add_column('users', sa.Column(
        'delegate_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=True
    ))

    # Create work_queues table
    op.create_table(
        'work_queues',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create work_queue_members association table
    op.create_table(
        'work_queue_members',
        sa.Column('queue_id', sa.Uuid(), sa.ForeignKey('work_queues.id'), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.PrimaryKeyConstraint('queue_id', 'user_id'),
    )

    # Add queue_id to work_items table
    op.add_column('work_items', sa.Column(
        'queue_id', sa.Uuid(), sa.ForeignKey('work_queues.id'), nullable=True
    ))

    # Extend PostgreSQL enums (skip for SQLite in tests)
    try:
        op.execute("ALTER TYPE workitemstate ADD VALUE IF NOT EXISTS 'suspended'")
        op.execute("ALTER TYPE performertype ADD VALUE IF NOT EXISTS 'queue'")
    except Exception:
        # SQLite does not have enum types
        pass


def downgrade() -> None:
    op.drop_column('work_items', 'queue_id')
    op.drop_table('work_queue_members')
    op.drop_table('work_queues')
    op.drop_column('users', 'delegate_id')
    op.drop_column('users', 'is_available')
    # Note: PostgreSQL enum values cannot be removed in a downgrade
