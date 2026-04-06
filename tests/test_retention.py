"""Tests for retention policy models, schemas, and API endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import DispositionAction
from app.models.retention import DocumentRetention, LegalHold, RetentionPolicy
from app.schemas.retention import (
    DocumentRetentionResponse,
    LegalHoldResponse,
    RetentionPolicyCreate,
    RetentionPolicyResponse,
)


# === Model Tests ===


class TestDispositionActionEnum:
    def test_archive_value(self):
        assert DispositionAction.ARCHIVE == "archive"

    def test_delete_value(self):
        assert DispositionAction.DELETE == "delete"

    def test_enum_has_two_values(self):
        assert len(DispositionAction) == 2


class TestRetentionPolicyModel:
    @pytest.mark.asyncio
    async def test_create_retention_policy(self, db_session: AsyncSession):
        policy = RetentionPolicy(
            id=uuid.uuid4(),
            name="7-Year Financial Retention",
            description="Required by SOX compliance",
            retention_period_days=2555,
            disposition_action=DispositionAction.ARCHIVE,
            is_active=True,
            created_by="admin",
        )
        db_session.add(policy)
        await db_session.flush()

        assert policy.id is not None
        assert policy.name == "7-Year Financial Retention"
        assert policy.retention_period_days == 2555
        assert policy.disposition_action == DispositionAction.ARCHIVE
        assert policy.is_active is True

    @pytest.mark.asyncio
    async def test_retention_policy_fields(self, db_session: AsyncSession):
        policy = RetentionPolicy(
            id=uuid.uuid4(),
            name="Short Retention",
            retention_period_days=30,
            disposition_action=DispositionAction.DELETE,
            created_by="admin",
        )
        db_session.add(policy)
        await db_session.flush()

        assert policy.description is None
        assert policy.is_active is True  # default
        assert policy.is_deleted is False  # from BaseModel


class TestDocumentRetentionModel:
    @pytest.mark.asyncio
    async def test_create_document_retention(self, db_session: AsyncSession):
        from app.models.document import Document

        doc = Document(
            id=uuid.uuid4(),
            title="Test Doc",
            filename="test.pdf",
            content_type="application/pdf",
            created_by="admin",
        )
        db_session.add(doc)
        await db_session.flush()

        policy = RetentionPolicy(
            id=uuid.uuid4(),
            name="Test Policy",
            retention_period_days=365,
            disposition_action=DispositionAction.ARCHIVE,
            created_by="admin",
        )
        db_session.add(policy)
        await db_session.flush()

        now = datetime.now(timezone.utc)
        dr = DocumentRetention(
            id=uuid.uuid4(),
            document_id=doc.id,
            retention_policy_id=policy.id,
            applied_at=now,
            expires_at=now + timedelta(days=365),
            applied_by="admin",
            created_by="admin",
        )
        db_session.add(dr)
        await db_session.flush()

        assert dr.document_id == doc.id
        assert dr.retention_policy_id == policy.id
        assert dr.applied_by == "admin"


class TestLegalHoldModel:
    @pytest.mark.asyncio
    async def test_create_legal_hold(self, db_session: AsyncSession):
        from app.models.document import Document

        doc = Document(
            id=uuid.uuid4(),
            title="Legal Doc",
            filename="legal.pdf",
            content_type="application/pdf",
            created_by="admin",
        )
        db_session.add(doc)
        await db_session.flush()

        hold = LegalHold(
            id=uuid.uuid4(),
            document_id=doc.id,
            reason="Litigation pending",
            placed_by="admin",
            placed_at=datetime.now(timezone.utc),
            created_by="admin",
        )
        db_session.add(hold)
        await db_session.flush()

        assert hold.document_id == doc.id
        assert hold.reason == "Litigation pending"
        assert hold.released_at is None
        assert hold.released_by is None


# === Schema Tests ===


class TestRetentionPolicySchemas:
    def test_create_schema_valid(self):
        schema = RetentionPolicyCreate(
            name="Test Policy",
            retention_period_days=365,
            disposition_action=DispositionAction.ARCHIVE,
        )
        assert schema.name == "Test Policy"
        assert schema.retention_period_days == 365

    def test_create_schema_name_min_length(self):
        with pytest.raises(Exception):
            RetentionPolicyCreate(
                name="",
                retention_period_days=365,
                disposition_action=DispositionAction.ARCHIVE,
            )

    def test_create_schema_name_max_length(self):
        with pytest.raises(Exception):
            RetentionPolicyCreate(
                name="x" * 256,
                retention_period_days=365,
                disposition_action=DispositionAction.ARCHIVE,
            )

    def test_create_schema_period_ge_1(self):
        with pytest.raises(Exception):
            RetentionPolicyCreate(
                name="Test",
                retention_period_days=0,
                disposition_action=DispositionAction.ARCHIVE,
            )

    def test_response_schema_from_attributes(self):
        assert RetentionPolicyResponse.model_config.get("from_attributes") is True


class TestDocumentRetentionResponseSchema:
    def test_is_expired_computed_field(self):
        now = datetime.now(timezone.utc)
        resp = DocumentRetentionResponse(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            retention_policy_id=uuid.uuid4(),
            policy_name="Test",
            applied_at=now - timedelta(days=400),
            expires_at=now - timedelta(days=35),
            applied_by="admin",
        )
        assert resp.is_expired is True

    def test_not_expired(self):
        now = datetime.now(timezone.utc)
        resp = DocumentRetentionResponse(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            retention_policy_id=uuid.uuid4(),
            policy_name="Test",
            applied_at=now,
            expires_at=now + timedelta(days=365),
            applied_by="admin",
        )
        assert resp.is_expired is False


class TestLegalHoldResponseSchema:
    def test_is_active_computed_field(self):
        resp = LegalHoldResponse(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            reason="Litigation",
            placed_by="admin",
            placed_at=datetime.now(timezone.utc),
            released_at=None,
            released_by=None,
        )
        assert resp.is_active is True

    def test_released_hold_not_active(self):
        resp = LegalHoldResponse(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            reason="Litigation",
            placed_by="admin",
            placed_at=datetime.now(timezone.utc),
            released_at=datetime.now(timezone.utc),
            released_by="admin",
        )
        assert resp.is_active is False
