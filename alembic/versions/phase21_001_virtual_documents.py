"""add virtual documents tables

Revision ID: phase21_001
Revises: phase20_001
Create Date: 2026-04-06 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase21_001'
down_revision: Union[str, None] = 'phase20_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'virtual_documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'virtual_document_children',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('virtual_document_id', sa.Uuid(), sa.ForeignKey('virtual_documents.id'), nullable=False),
        sa.Column('document_id', sa.Uuid(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('virtual_document_id', 'document_id', name='uq_vdoc_child_document'),
        sa.UniqueConstraint('virtual_document_id', 'sort_order', name='uq_vdoc_child_sort_order'),
    )


def downgrade() -> None:
    op.drop_table('virtual_document_children')
    op.drop_table('virtual_documents')
