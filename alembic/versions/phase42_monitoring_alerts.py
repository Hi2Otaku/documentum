"""Phase 42: alert_rules table for system monitoring.

Revision ID: phase42_mon01
Revises: phase40_001
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa

revision: str = "phase42_mon01"
down_revision: str = "phase40_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS alert_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL,
            metric_name VARCHAR(100) NOT NULL,
            operator VARCHAR(10) NOT NULL,
            threshold DOUBLE PRECISION NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            notification_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by VARCHAR(255),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_alert_rules_metric_enabled
        ON alert_rules (metric_name, enabled)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_alert_rules_metric_enabled")
    op.execute("DROP TABLE IF EXISTS alert_rules")
