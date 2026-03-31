"""add lifecycle state acl tables and columns

Revision ID: phase7_001
Revises: phase6_001
Create Date: 2026-03-31 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase7_001'
down_revision: Union[str, None] = 'phase6_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create document_acl table
    op.create_table(
        'document_acl',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('principal_id', sa.Uuid(), nullable=False),
        sa.Column('principal_type', sa.String(20), nullable=False),
        sa.Column('permission_level', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.UniqueConstraint(
            'document_id', 'principal_id', 'principal_type', 'permission_level',
            name='uq_document_acl_entry',
        ),
    )
    op.create_index('ix_document_acl_document_id', 'document_acl', ['document_id'])

    # Create lifecycle_acl_rules table
    op.create_table(
        'lifecycle_acl_rules',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('from_state', sa.String(20), nullable=False),
        sa.Column('to_state', sa.String(20), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('permission_level', sa.String(10), nullable=False),
        sa.Column('principal_filter', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Add lifecycle_state column to documents table
    op.add_column('documents', sa.Column('lifecycle_state', sa.String(20), nullable=True, server_default='draft'))

    # Add lifecycle_action column to activity_templates table
    op.add_column('activity_templates', sa.Column('lifecycle_action', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('activity_templates', 'lifecycle_action')
    op.drop_column('documents', 'lifecycle_state')
    op.drop_index('ix_document_acl_document_id', 'document_acl')
    op.drop_table('lifecycle_acl_rules')
    op.drop_table('document_acl')
