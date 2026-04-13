"""Service layer for DocumentType: CRUD, schema merging, and metadata validation."""

import uuid

import jsonschema
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_type import DocumentType
from app.schemas.document_type import DocumentTypeCreate, DocumentTypeUpdate


def merge_schemas(parent_schema: dict, child_schema: dict) -> dict:
    """Merge parent and child JSON Schemas.

    Child properties override parent properties with the same name.
    Required arrays are unioned (deduplicated).
    """
    parent_props = parent_schema.get("properties", {})
    child_props = child_schema.get("properties", {})
    merged_props = {**parent_props, **child_props}

    parent_required = parent_schema.get("required", [])
    child_required = child_schema.get("required", [])
    merged_required = list(dict.fromkeys(parent_required + child_required))

    merged: dict = {"type": "object", "properties": merged_props}
    if merged_required:
        merged["required"] = merged_required
    return merged


def get_effective_schema(doc_type: DocumentType) -> dict:
    """Return the effective schema for a DocumentType, merging parent if present."""
    if doc_type.parent_type is not None:
        return merge_schemas(doc_type.parent_type.metadata_schema, doc_type.metadata_schema)

    schema = doc_type.metadata_schema
    # Ensure it is wrapped as a proper object schema
    if not isinstance(schema, dict) or "type" not in schema:
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        required = schema.get("required", []) if isinstance(schema, dict) else []
        wrapped: dict = {"type": "object", "properties": props}
        if required:
            wrapped["required"] = required
        return wrapped
    return schema


async def validate_metadata(
    db: AsyncSession,
    document_type_id: uuid.UUID | None,
    custom_properties: dict,
) -> None:
    """Validate custom_properties against the DocumentType's effective JSON Schema.

    If document_type_id is None (untyped document), validation is skipped entirely.
    Raises HTTPException(422) with all validation errors if validation fails.
    """
    if document_type_id is None:
        return

    doc_type = await get_document_type(db, document_type_id)
    effective_schema = get_effective_schema(doc_type)

    validator = jsonschema.Draft7Validator(effective_schema)
    errors = list(validator.iter_errors(custom_properties))

    if errors:
        error_details = []
        for e in errors:
            field = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else e.json_path
            error_details.append({"field": field, "error": e.message})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Metadata validation failed", "errors": error_details},
        )


async def create_document_type(
    db: AsyncSession,
    data: DocumentTypeCreate,
    user_id: str,
) -> DocumentType:
    """Create a new DocumentType.

    Guards:
    - Name must be unique.
    - Parent must not itself have a parent (max 1 level inheritance).
    """
    # Check name uniqueness
    existing = await db.execute(
        select(DocumentType).where(
            DocumentType.name == data.name,
            DocumentType.is_deleted == False,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document type with name '{data.name}' already exists",
        )

    # Validate parent hierarchy (max 1 level)
    if data.parent_type_id is not None:
        parent = await _fetch_type_or_404(db, data.parent_type_id)
        if parent.parent_type_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create type: parent type already has a parent (max 1 level inheritance)",
            )

    doc_type = DocumentType(
        name=data.name,
        description=data.description,
        metadata_schema=data.metadata_schema,
        parent_type_id=data.parent_type_id,
        created_by=user_id,
    )
    db.add(doc_type)
    await db.flush()
    await db.refresh(doc_type)
    return doc_type


async def list_document_types(db: AsyncSession) -> list[DocumentType]:
    """Return all non-deleted document types ordered by name."""
    result = await db.execute(
        select(DocumentType)
        .where(DocumentType.is_deleted == False)  # noqa: E712
        .order_by(DocumentType.name)
    )
    return list(result.scalars().all())


async def get_document_type(db: AsyncSession, type_id: uuid.UUID) -> DocumentType:
    """Fetch a DocumentType by ID. Raises 404 if not found or soft-deleted."""
    return await _fetch_type_or_404(db, type_id)


async def update_document_type(
    db: AsyncSession,
    type_id: uuid.UUID,
    data: DocumentTypeUpdate,
    user_id: str,
) -> DocumentType:
    """Update a DocumentType.

    Guards:
    - Name uniqueness if name is being changed.
    - No grandchild creation: if assigning a parent, verify parent has no parent.
    - If this type has children, cannot assign it a parent (would create grandchild chain).
    """
    doc_type = await _fetch_type_or_404(db, type_id)

    if data.name is not None and data.name != doc_type.name:
        existing = await db.execute(
            select(DocumentType).where(
                DocumentType.name == data.name,
                DocumentType.is_deleted == False,  # noqa: E712
                DocumentType.id != type_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document type with name '{data.name}' already exists",
            )
        doc_type.name = data.name

    if data.description is not None:
        doc_type.description = data.description

    if data.metadata_schema is not None:
        doc_type.metadata_schema = data.metadata_schema

    if data.parent_type_id is not None:
        # Check this type doesn't already have children (would create grandchild chain)
        children_result = await db.execute(
            select(DocumentType).where(
                DocumentType.parent_type_id == type_id,
                DocumentType.is_deleted == False,  # noqa: E712
            ).limit(1)
        )
        if children_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign parent to a type that already has children (max 1 level inheritance)",
            )

        # Validate proposed parent has no parent
        parent = await _fetch_type_or_404(db, data.parent_type_id)
        if parent.parent_type_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create type: parent type already has a parent (max 1 level inheritance)",
            )
        doc_type.parent_type_id = data.parent_type_id

    await db.flush()
    await db.refresh(doc_type)
    return doc_type


async def delete_document_type(db: AsyncSession, type_id: uuid.UUID) -> None:
    """Soft-delete a DocumentType and unlink all documents referencing it."""
    doc_type = await _fetch_type_or_404(db, type_id)
    doc_type.is_deleted = True

    # Unlink all documents that reference this type
    docs_result = await db.execute(
        select(Document).where(
            Document.document_type_id == type_id,
            Document.is_deleted == False,  # noqa: E712
        )
    )
    for doc in docs_result.scalars().all():
        doc.document_type_id = None

    await db.flush()


async def get_document_count_for_type(db: AsyncSession, type_id: uuid.UUID) -> int:
    """Count active documents that have this document type assigned."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.count(Document.id)).where(
            Document.document_type_id == type_id,
            Document.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one()


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _fetch_type_or_404(db: AsyncSession, type_id: uuid.UUID) -> DocumentType:
    """Fetch DocumentType by ID or raise HTTP 404."""
    result = await db.execute(
        select(DocumentType).where(
            DocumentType.id == type_id,
            DocumentType.is_deleted == False,  # noqa: E712
        )
    )
    doc_type = result.scalar_one_or_none()
    if doc_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document type not found",
        )
    return doc_type
