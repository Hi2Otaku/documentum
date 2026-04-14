"""Service layer for DocumentRelationship: CRUD for typed document links."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.document_relationship import DocumentRelationship, RelationshipType


async def _fetch_document_or_404(
    db: AsyncSession, document_id: uuid.UUID
) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.is_deleted == False  # noqa: E712
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    return doc


async def create_relationship(
    db: AsyncSession,
    source_document_id: uuid.UUID,
    target_document_id: uuid.UUID,
    relationship_type: str,
    description: str | None = None,
    created_by: str | None = None,
) -> DocumentRelationship:
    """Create a typed directional relationship between two documents."""
    if source_document_id == target_document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a relationship from a document to itself",
        )

    # Validate both documents exist
    await _fetch_document_or_404(db, source_document_id)
    await _fetch_document_or_404(db, target_document_id)

    # Validate relationship type
    try:
        rel_type = RelationshipType(relationship_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid relationship type: {relationship_type}. "
            f"Must be one of: {[t.value for t in RelationshipType]}",
        )

    # Check for duplicate
    existing = await db.execute(
        select(DocumentRelationship).where(
            DocumentRelationship.source_document_id == source_document_id,
            DocumentRelationship.target_document_id == target_document_id,
            DocumentRelationship.relationship_type == rel_type,
            DocumentRelationship.is_deleted == False,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This relationship already exists",
        )

    rel = DocumentRelationship(
        source_document_id=source_document_id,
        target_document_id=target_document_id,
        relationship_type=rel_type,
        description=description,
        created_by=created_by,
    )
    db.add(rel)
    await db.flush()
    await db.refresh(rel, attribute_names=["source_document", "target_document"])
    return rel


async def list_relationships(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> list[DocumentRelationship]:
    """List all relationships where the document is source OR target."""
    result = await db.execute(
        select(DocumentRelationship)
        .options(
            selectinload(DocumentRelationship.source_document),
            selectinload(DocumentRelationship.target_document),
        )
        .where(
            DocumentRelationship.is_deleted == False,  # noqa: E712
            or_(
                DocumentRelationship.source_document_id == document_id,
                DocumentRelationship.target_document_id == document_id,
            ),
        )
        .order_by(DocumentRelationship.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_relationship(
    db: AsyncSession,
    document_id: uuid.UUID,
    relationship_id: uuid.UUID,
) -> None:
    """Soft-delete a relationship. The document_id must be the source or target."""
    result = await db.execute(
        select(DocumentRelationship).where(
            DocumentRelationship.id == relationship_id,
            DocumentRelationship.is_deleted == False,  # noqa: E712
            or_(
                DocumentRelationship.source_document_id == document_id,
                DocumentRelationship.target_document_id == document_id,
            ),
        )
    )
    rel = result.scalar_one_or_none()
    if rel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found",
        )
    rel.is_deleted = True
    await db.flush()
