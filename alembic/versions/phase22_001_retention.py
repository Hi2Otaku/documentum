"""add retention policies, document retentions, and legal holds

Revision ID: phase22_001
Revises: phase11_001
Create Date: 2026-04-06 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase22_001'
down_revision: Union[str, None] = 'phase21_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create disposition action enum
    dispositionaction_enum = sa.Enum('archive', 'delete', name='dispositionaction')
    dispositionaction_enum.create(op.get_bind(), checkfirst=True)

    # Create retention_policies table
    op.create_table(
        'retention_policies',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('retention_period_days', sa.Integer(), nullable=False),
        sa.Column('disposition_action', dispositionaction_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )

    # Create document_retentions table
    op.create_table(
        'document_retentions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('document_id', sa.Uuid(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('policy_id', sa.Uuid(), sa.ForeignKey('retention_policies.id'), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )

    # Create legal_holds table
    op.create_table(
        'legal_holds',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('document_id', sa.Uuid(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('placed_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('placed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_table('legal_holds')
    op.drop_table('document_retentions')
    op.drop_table('retention_policies')
    sa.Enum(name='dispositionaction').drop(op.get_bind(), checkfirst=True)
