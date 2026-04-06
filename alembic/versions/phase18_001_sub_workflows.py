"""add sub-workflow columns to activity_templates and workflow_instances

Revision ID: phase18_001
Revises: phase11_001
Create Date: 2026-04-06 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase18_001'
down_revision: Union[str, None] = 'phase11_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Add SUB_WORKFLOW to ActivityType enum (PostgreSQL only)
    if bind.dialect.name != "sqlite":
        op.execute("ALTER TYPE activitytype ADD VALUE IF NOT EXISTS 'sub_workflow'")

    # ActivityTemplate: sub_template_id and variable_mapping
    op.add_column(
        "activity_templates",
        sa.Column("sub_template_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "activity_templates",
        sa.Column("variable_mapping", sa.JSON(), nullable=True),
    )
    op.create_foreign_key(
        "fk_activity_templates_sub_template_id",
        "activity_templates",
        "process_templates",
        ["sub_template_id"],
        ["id"],
    )

    # WorkflowInstance: parent_workflow_id, parent_activity_instance_id, nesting_depth
    op.add_column(
        "workflow_instances",
        sa.Column("parent_workflow_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "workflow_instances",
        sa.Column("parent_activity_instance_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "workflow_instances",
        sa.Column("nesting_depth", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_foreign_key(
        "fk_workflow_instances_parent",
        "workflow_instances",
        "workflow_instances",
        ["parent_workflow_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_workflow_instances_parent_activity",
        "workflow_instances",
        "activity_instances",
        ["parent_activity_instance_id"],
        ["id"],
    )


def downgrade() -> None:
    # Drop foreign keys first, then columns (reverse order)
    bind = op.get_bind()

    if bind.dialect.name != "sqlite":
        op.drop_constraint(
            "fk_workflow_instances_parent_activity", "workflow_instances", type_="foreignkey"
        )
        op.drop_constraint(
            "fk_workflow_instances_parent", "workflow_instances", type_="foreignkey"
        )

    op.drop_column("workflow_instances", "nesting_depth")
    op.drop_column("workflow_instances", "parent_activity_instance_id")
    op.drop_column("workflow_instances", "parent_workflow_id")

    if bind.dialect.name != "sqlite":
        op.drop_constraint(
            "fk_activity_templates_sub_template_id", "activity_templates", type_="foreignkey"
        )

    op.drop_column("activity_templates", "variable_mapping")
    op.drop_column("activity_templates", "sub_template_id")

    # Note: PostgreSQL does not support removing values from enums.
    # The 'sub_workflow' value will remain in the activitytype enum.
