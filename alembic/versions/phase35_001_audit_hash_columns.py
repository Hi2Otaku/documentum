"""phase35_001_audit_hash_columns

Revision ID: phase35_001
Revises: phase34_004
Create Date: 2026-04-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "phase35_001"
down_revision: Union[str, None] = "phase34_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("content_hash", sa.String(64), nullable=True))
    op.add_column("audit_log", sa.Column("chain_hash", sa.String(64), nullable=True))
    op.add_column("audit_log", sa.Column("chain_sequence", sa.BigInteger(), nullable=True))
    op.create_index("ix_audit_log_chain_sequence", "audit_log", ["chain_sequence"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_chain_sequence", table_name="audit_log")
    op.drop_column("audit_log", "chain_sequence")
    op.drop_column("audit_log", "chain_hash")
    op.drop_column("audit_log", "content_hash")
