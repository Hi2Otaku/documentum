"""phase36_identity_provider

Revision ID: phase36_001
Revises: phase35_001
Create Date: 2026-04-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "phase36_001"
down_revision: Union[str, None] = "phase35_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identity_providers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(150), unique=True, nullable=False),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column(
            "config",
            sa.dialects.postgresql.JSONB(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_enabled", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "service_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.String(128), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_service_tokens_token_hash",
        "service_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_service_tokens_token_hash", table_name="service_tokens")
    op.drop_table("service_tokens")
    op.drop_table("identity_providers")
