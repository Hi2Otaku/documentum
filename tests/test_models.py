"""Tests for data models (FOUND-02, FOUND-03)."""

import pytest

from app.models.base import Base, BaseModel
from app.models.audit import AuditLog

# Ensure all models are imported so Base.metadata has all tables
import app.models  # noqa: F401


class TestBaseModelColumns:
    """FOUND-03: BaseModel has required columns."""

    def test_base_model_has_required_columns(self):
        """Inspect BaseModel columns for id, created_at, updated_at, created_by, is_deleted."""
        # Get column names from a concrete model that inherits BaseModel
        from app.models.user import User

        column_names = [c.name for c in User.__table__.columns]
        assert "id" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names
        assert "created_by" in column_names
        assert "is_deleted" in column_names


class TestTableExistence:
    """FOUND-02: All workflow tables exist in metadata."""

    def test_all_workflow_tables_exist(self):
        """All 8 Documentum workflow tables are registered in Base.metadata."""
        table_names = set(Base.metadata.tables.keys())
        expected_workflow_tables = {
            "process_templates",
            "activity_templates",
            "flow_templates",
            "workflow_instances",
            "activity_instances",
            "work_items",
            "process_variables",
            "workflow_packages",
        }
        for table in expected_workflow_tables:
            assert table in table_names, f"Missing workflow table: {table}"

    def test_user_tables_exist(self):
        """User/group/role tables and junction tables exist."""
        table_names = set(Base.metadata.tables.keys())
        expected = {"users", "groups", "roles", "user_groups", "user_roles"}
        for table in expected:
            assert table in table_names, f"Missing user table: {table}"

    def test_audit_log_table_exists(self):
        """audit_log table exists."""
        assert "audit_log" in Base.metadata.tables

    def test_audit_log_not_base_model(self):
        """AuditLog does not have is_deleted or updated_at (it's append-only)."""
        column_names = [c.name for c in AuditLog.__table__.columns]
        assert "is_deleted" not in column_names
        assert "updated_at" not in column_names
