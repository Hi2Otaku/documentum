"""phase33_001_saved_searches

Revision ID: phase33_001
Revises: phase31_001
Create Date: 2026-04-14

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "phase33_001"
down_revision: Union[str, None] = "phase31_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE saved_searches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            query TEXT NOT NULL,
            filters JSONB NOT NULL DEFAULT '{}',
            is_smart_folder BOOLEAN NOT NULL DEFAULT FALSE,
            display_order INTEGER NOT NULL DEFAULT 0,
            user_id UUID NOT NULL REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by VARCHAR(255),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    op.execute(
        "CREATE INDEX ix_saved_searches_user_id ON saved_searches(user_id)"
    )
    op.execute(
        "CREATE INDEX ix_saved_searches_smart_folder "
        "ON saved_searches(user_id, is_smart_folder) "
        "WHERE is_smart_folder = TRUE"
    )


def downgrade() -> None:
    op.execute("DROP TABLE saved_searches")
