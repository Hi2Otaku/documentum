"""phase37_001_error_handlers

Revision ID: phase37_001
Revises: phase36_001
Create Date: 2026-04-15

Add error handler and compensation columns to activity_templates and
error tracking columns to activity_instances.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "phase37_001"
down_revision: Union[str, None] = "phase36_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- activity_templates: error handler and compensation FKs --
    op.add_column(
        "activity_templates",
        sa.Column("error_handler_activity_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "activity_templates",
        sa.Column("compensation_activity_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_activity_templates_error_handler",
        "activity_templates",
        "activity_templates",
        ["error_handler_activity_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_activity_templates_compensation",
        "activity_templates",
        "activity_templates",
        ["compensation_activity_id"],
        ["id"],
    )

    # -- activity_instances: error tracking and completion order --
    op.add_column(
        "activity_instances",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "activity_instances",
        sa.Column("error_details", sa.JSON(), nullable=True),
    )
    op.add_column(
        "activity_instances",
        sa.Column("completed_order", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("activity_instances", "completed_order")
    op.drop_column("activity_instances", "error_details")
    op.drop_column("activity_instances", "error_message")

    op.drop_constraint(
        "fk_activity_templates_compensation",
        "activity_templates",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_activity_templates_error_handler",
        "activity_templates",
        type_="foreignkey",
    )
    op.drop_column("activity_templates", "compensation_activity_id")
    op.drop_column("activity_templates", "error_handler_activity_id")
