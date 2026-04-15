"""Tests for CMIS-QL query parser and executor."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.folder import Folder
from app.models.user import User


@pytest.fixture(autouse=True)
def mock_celery_tasks(monkeypatch):
    """Prevent ALL Celery tasks from trying to connect to Redis during tests."""
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "app.celery_app.celery_app.send_task",
        MagicMock(return_value=MagicMock(id="mock-task-id")),
    )
    from celery.app.task import Task
    monkeypatch.setattr(Task, "delay", MagicMock(return_value=MagicMock(id="mock-task-id")))
    monkeypatch.setattr(Task, "apply_async", MagicMock(return_value=MagicMock(id="mock-task-id")))


# ── Unit tests for parse_cmis_query ────────────────────────────────────────


class TestParseCmisQuery:
    """Unit tests for the CMIS-QL parser (no DB needed)."""

    def test_parse_select_all_from_document(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query("SELECT * FROM cmis:document")
        assert parsed.select_fields == ["*"]
        assert parsed.from_type == "cmis:document"
        assert parsed.where_clauses == []
        assert parsed.order_by == []

    def test_parse_select_specific_fields(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query("SELECT cmis:objectId, cmis:name FROM cmis:document")
        assert "cmis:objectId" in parsed.select_fields
        assert "cmis:name" in parsed.select_fields
        assert len(parsed.select_fields) == 2

    def test_parse_where_equals(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query("SELECT * FROM cmis:document WHERE cmis:name = 'test.pdf'")
        assert len(parsed.where_clauses) == 1
        assert parsed.where_clauses[0].property == "cmis:name"
        assert parsed.where_clauses[0].operator == "="
        assert parsed.where_clauses[0].value == "test.pdf"

    def test_parse_where_like(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query("SELECT * FROM cmis:document WHERE cmis:name LIKE 'test%'")
        assert len(parsed.where_clauses) == 1
        assert parsed.where_clauses[0].operator == "LIKE"
        assert parsed.where_clauses[0].value == "test%"

    def test_parse_where_created_by(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query("SELECT * FROM cmis:document WHERE cmis:createdBy = 'admin'")
        assert parsed.where_clauses[0].property == "cmis:createdBy"
        assert parsed.where_clauses[0].value == "admin"

    def test_parse_order_by_asc(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query("SELECT * FROM cmis:document ORDER BY cmis:name ASC")
        assert len(parsed.order_by) == 1
        assert parsed.order_by[0].property == "cmis:name"
        assert parsed.order_by[0].direction == "ASC"

    def test_parse_order_by_desc(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query("SELECT * FROM cmis:document ORDER BY cmis:creationDate DESC")
        assert parsed.order_by[0].property == "cmis:creationDate"
        assert parsed.order_by[0].direction == "DESC"

    def test_parse_combined_where_and(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query(
            "SELECT * FROM cmis:document WHERE cmis:name = 'a' AND cmis:createdBy = 'b'"
        )
        assert len(parsed.where_clauses) == 2
        assert parsed.where_clauses[0].property == "cmis:name"
        assert parsed.where_clauses[1].property == "cmis:createdBy"

    def test_parse_from_folder(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query("SELECT * FROM cmis:folder")
        assert parsed.from_type == "cmis:folder"

    def test_parse_invalid_query_raises(self):
        from app.services.cmis_query_service import parse_cmis_query
        with pytest.raises(ValueError, match="Invalid"):
            parse_cmis_query("INVALID QUERY")

    def test_parse_where_content_type(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query(
            "SELECT * FROM cmis:document WHERE cmis:contentStreamMimeType = 'application/pdf'"
        )
        assert parsed.where_clauses[0].property == "cmis:contentStreamMimeType"
        assert parsed.where_clauses[0].value == "application/pdf"

    def test_parse_where_in(self):
        from app.services.cmis_query_service import parse_cmis_query
        parsed = parse_cmis_query(
            "SELECT * FROM cmis:document WHERE cmis:name IN ('a.pdf', 'b.pdf')"
        )
        assert parsed.where_clauses[0].operator == "IN"
        assert parsed.where_clauses[0].value == ["a.pdf", "b.pdf"]


# ── Integration tests for execute_cmis_query ────────────────────────────────


@pytest.mark.asyncio
class TestExecuteCmisQuery:
    """Integration tests: create test data, run CMIS-QL, verify results."""

    async def _seed_documents(self, db: AsyncSession, user_id: str):
        """Create a few test documents in the DB."""
        docs = []
        for title, content_type, created_by in [
            ("report.pdf", "application/pdf", user_id),
            ("test-file.txt", "text/plain", user_id),
            ("budget.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "other-user"),
        ]:
            doc = Document(
                title=title,
                filename=title,
                content_type=content_type,
                created_by=created_by,
                current_major_version=1,
                current_minor_version=0,
            )
            db.add(doc)
            docs.append(doc)
        await db.flush()
        return docs

    async def _seed_folders(self, db: AsyncSession, user_id: str):
        """Create test folders."""
        folders = []
        for name in ["Reports", "Archives"]:
            folder = Folder(name=name, is_cabinet=True, created_by=user_id)
            db.add(folder)
            folders.append(folder)
        await db.flush()
        return folders

    async def test_select_all_documents(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session, "SELECT * FROM cmis:document",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] == 3
        assert len(result["objects"]) == 3

    async def test_select_specific_fields(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session, "SELECT cmis:objectId, cmis:name FROM cmis:document",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] == 3
        # Each object should only have the requested fields
        for obj in result["objects"]:
            props = obj["succinctProperties"]
            assert "cmis:objectId" in props
            assert "cmis:name" in props
            # Should NOT have other fields
            assert "cmis:contentStreamMimeType" not in props

    async def test_where_name_equals(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session,
            "SELECT * FROM cmis:document WHERE cmis:name = 'report.pdf'",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] == 1
        assert result["objects"][0]["succinctProperties"]["cmis:name"] == "report.pdf"

    async def test_where_like_prefix(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session,
            "SELECT * FROM cmis:document WHERE cmis:name LIKE 'test%'",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] == 1
        assert result["objects"][0]["succinctProperties"]["cmis:name"] == "test-file.txt"

    async def test_where_created_by(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session,
            f"SELECT * FROM cmis:document WHERE cmis:createdBy = '{admin_user.id}'",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] == 2  # report.pdf and test-file.txt

    async def test_where_content_type(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session,
            "SELECT * FROM cmis:document WHERE cmis:contentStreamMimeType = 'application/pdf'",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] == 1
        assert result["objects"][0]["succinctProperties"]["cmis:name"] == "report.pdf"

    async def test_where_in_list(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session,
            "SELECT * FROM cmis:document WHERE cmis:name IN ('report.pdf', 'budget.xlsx')",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] == 2
        names = {o["succinctProperties"]["cmis:name"] for o in result["objects"]}
        assert names == {"report.pdf", "budget.xlsx"}

    async def test_order_by_name_asc(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session,
            "SELECT * FROM cmis:document ORDER BY cmis:name ASC",
            user_id=str(admin_user.id), is_superuser=True,
        )
        names = [o["succinctProperties"]["cmis:name"] for o in result["objects"]]
        assert names == sorted(names)

    async def test_order_by_creation_date_desc(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session,
            "SELECT * FROM cmis:document ORDER BY cmis:creationDate DESC",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] == 3

    async def test_combined_where_and(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session,
            f"SELECT * FROM cmis:document WHERE cmis:name = 'report.pdf' AND cmis:createdBy = '{admin_user.id}'",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] == 1
        assert result["objects"][0]["succinctProperties"]["cmis:name"] == "report.pdf"

    async def test_query_folders(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_folders(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session, "SELECT * FROM cmis:folder",
            user_id=str(admin_user.id), is_superuser=True,
        )
        assert result["numItems"] >= 2
        for obj in result["objects"]:
            assert obj["succinctProperties"]["cmis:baseTypeId"] == "cmis:folder"

    async def test_invalid_query_raises(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        with pytest.raises(ValueError):
            await execute_cmis_query(
                db_session, "INVALID QUERY",
                user_id=str(admin_user.id), is_superuser=True,
            )

    async def test_pagination(self, db_session: AsyncSession, admin_user: User):
        from app.services.cmis_query_service import execute_cmis_query
        await self._seed_documents(db_session, str(admin_user.id))
        result = await execute_cmis_query(
            db_session, "SELECT * FROM cmis:document",
            user_id=str(admin_user.id), is_superuser=True,
            max_items=2, skip_count=0,
        )
        assert len(result["objects"]) == 2
        assert result["hasMoreItems"] is True
        assert result["numItems"] == 3
