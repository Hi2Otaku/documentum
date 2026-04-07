"""add renditions table

Revision ID: phase20_001
Revises: phase11_001
Create Date: 2026-04-06 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase20_001'
down_revision: Union[str, None] = 'phase19_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'renditions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_version_id', sa.Uuid(), nullable=False),
        sa.Column('rendition_type', sa.Enum('pdf', 'thumbnail', name='renditiontype', create_type=False), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'ready', 'failed', name='renditionstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('minio_object_key', sa.String(500), nullable=True),
        sa.Column('content_type', sa.String(255), nullable=True),
        sa.Column('content_size', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_renditions_document_version_id', 'renditions', ['document_version_id'])


def downgrade() -> None:
    op.drop_index('ix_renditions_document_version_id', table_name='renditions')
    op.drop_table('renditions')

    sa.Enum(name='renditionstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='renditiontype').drop(op.get_bind(), checkfirst=True)
