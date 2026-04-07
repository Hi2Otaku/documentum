"""add document_signatures table and is_signed column on document_versions

Revision ID: phase23_001
Revises: phase11_001
Create Date: 2026-04-06 20:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase23_001'
down_revision: Union[str, None] = 'phase22_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_signed column to document_versions
    op.add_column(
        'document_versions',
        sa.Column('is_signed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )

    # Create document_signatures table
    op.create_table(
        'document_signatures',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('version_id', sa.Uuid(), nullable=False),
        sa.Column('signer_id', sa.Uuid(), nullable=False),
        sa.Column('signature_data', sa.LargeBinary(), nullable=False),
        sa.Column('certificate_pem', sa.Text(), nullable=False),
        sa.Column('signer_cn', sa.String(500), nullable=False),
        sa.Column('signed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('algorithm', sa.String(50), nullable=False, server_default='sha256WithRSAEncryption'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['version_id'], ['document_versions.id']),
        sa.ForeignKeyConstraint(['signer_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_document_signatures_version_id',
        'document_signatures',
        ['version_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_document_signatures_version_id', table_name='document_signatures')
    op.drop_table('document_signatures')
    op.drop_column('document_versions', 'is_signed')
