"""add triggertype enum and method_name column

Revision ID: 3efa9fa4be2a
Revises: 
Create Date: 2026-03-30 19:52:02.093702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3efa9fa4be2a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the triggertype enum type
    triggertype = sa.Enum('and_join', 'or_join', name='triggertype')
    triggertype.create(op.get_bind(), checkfirst=True)

    # Alter activity_templates.trigger_type from VARCHAR(20) to triggertype enum
    op.alter_column(
        'activity_templates',
        'trigger_type',
        existing_type=sa.String(20),
        type_=sa.Enum('and_join', 'or_join', name='triggertype'),
        existing_nullable=False,
        existing_server_default='or_join',
        postgresql_using='trigger_type::triggertype',
    )

    # Add method_name column to activity_templates
    op.add_column(
        'activity_templates',
        sa.Column('method_name', sa.String(255), nullable=True),
    )


def downgrade() -> None:
    # Remove method_name column
    op.drop_column('activity_templates', 'method_name')

    # Revert trigger_type from enum back to VARCHAR(20)
    op.alter_column(
        'activity_templates',
        'trigger_type',
        existing_type=sa.Enum('and_join', 'or_join', name='triggertype'),
        type_=sa.String(20),
        existing_nullable=False,
        existing_server_default='or_join',
    )

    # Drop the triggertype enum type
    sa.Enum(name='triggertype').drop(op.get_bind(), checkfirst=True)
