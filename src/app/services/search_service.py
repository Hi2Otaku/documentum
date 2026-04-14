"""Full-text search service using PostgreSQL tsvector/tsquery.

Provides ranked document search with ts_headline snippet generation,
optional folder/type/lifecycle filters, and ACL enforcement.
"""
import uuid

from sqlalchemy import case, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentVersion


def _build_tsquery(query_text: str):
    """Build a tsquery that supports prefix matching.

    Splits the input into words and appends :* to each for prefix matching.
    e.g. "par agr" -> "par:* & agr:*"
    This means typing "par" will match "partnership".
    """
    words = query_text.strip().split()
    if not words:
        return func.to_tsquery("english", "''")
    prefix_terms = " & ".join(f"{w}:*" for w in words)
    return func.to_tsquery("english", prefix_terms)


async def search_documents(
    db: AsyncSession,
    query_text: str,
    folder_id: uuid.UUID | None = None,
    document_type_id: uuid.UUID | None = None,
    lifecycle_state: str | None = None,
    skip: int = 0,
    limit: int = 20,
    user_id: str | None = None,
    is_superuser: bool = False,
) -> tuple[list[dict], int]:
    """Search documents using PostgreSQL full-text search with prefix matching.

    Supports partial word matching: typing "par" finds "partnership".
    Also falls back to ILIKE title match for short queries.
    """
    ts_query = _build_tsquery(query_text)
    # Rank: use ts_rank when FTS matches, fallback score of 0.1 for ILIKE-only matches
    ilike_pattern_rank = f"%{query_text}%"
    rank = case(
        (Document.search_vector.op("@@")(ts_query), func.ts_rank(Document.search_vector, ts_query)),
        else_=literal(0.1),
    ).label("rank")

    # Correlated subquery for latest version's fulltext_content
    latest_content_subq = (
        select(DocumentVersion.fulltext_content)
        .where(DocumentVersion.document_id == Document.id)
        .order_by(
            DocumentVersion.major_version.desc(),
            DocumentVersion.minor_version.desc(),
        )
        .limit(1)
        .correlate(Document)
        .scalar_subquery()
    )

    headline = func.ts_headline(
        "english",
        func.coalesce(latest_content_subq, Document.title),
        ts_query,
        "StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, MaxFragments=3",
    ).label("headline")

    # Base conditions: FTS prefix match OR title/author ILIKE for substring matches
    ilike_pattern = f"%{query_text}%"
    conditions = [
        or_(
            Document.search_vector.op("@@")(ts_query),
            Document.title.ilike(ilike_pattern),
            Document.author.ilike(ilike_pattern),
        ),
        Document.is_deleted == False,  # noqa: E712
    ]

    # Optional filters
    if folder_id:
        from app.models.folder import document_folders

        conditions.append(
            Document.id.in_(
                select(document_folders.c.document_id).where(
                    document_folders.c.folder_id == folder_id
                )
            )
        )

    if document_type_id:
        conditions.append(Document.document_type_id == document_type_id)

    if lifecycle_state:
        conditions.append(Document.lifecycle_state == lifecycle_state)

    # ACL enforcement
    if not is_superuser and user_id:
        from app.models.acl import DocumentACL
        from app.models.enums import WorkItemState
        from app.models.workflow import ActivityInstance, WorkItem, WorkflowPackage

        uid = uuid.UUID(user_id)

        # Documents with direct ACL for this user
        acl_doc_ids = (
            select(DocumentACL.document_id)
            .where(
                DocumentACL.principal_id == uid,
                DocumentACL.principal_type == "user",
                DocumentACL.is_deleted == False,  # noqa: E712
            )
            .correlate(None)
        )

        # Documents with NO ACL entries at all (open access)
        docs_with_acl = (
            select(DocumentACL.document_id)
            .where(DocumentACL.is_deleted == False)  # noqa: E712
            .distinct()
            .correlate(None)
        )

        # Documents attached to workflows where user has active work item
        wf_doc_ids = (
            select(WorkflowPackage.document_id)
            .join(
                ActivityInstance,
                ActivityInstance.workflow_instance_id
                == WorkflowPackage.workflow_instance_id,
            )
            .join(WorkItem, WorkItem.activity_instance_id == ActivityInstance.id)
            .where(
                WorkItem.performer_id == uid,
                WorkItem.state.in_(
                    [WorkItemState.AVAILABLE, WorkItemState.ACQUIRED]
                ),
                WorkflowPackage.document_id.isnot(None),
            )
            .correlate(None)
        )

        conditions.append(
            or_(
                Document.id.in_(acl_doc_ids),
                Document.id.notin_(docs_with_acl),
                Document.id.in_(wf_doc_ids),
            )
        )

    # Build base query
    base_query = (
        select(Document, rank, headline)
        .options(selectinload(Document.document_type))
        .where(*conditions)
    )

    # Total count
    count_query = select(func.count()).select_from(
        select(Document.id).where(*conditions).subquery()
    )
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    # Fetch results with ranking
    results_query = base_query.order_by(rank.desc()).offset(skip).limit(limit)
    results = await db.execute(results_query)

    search_results = []
    for doc, doc_rank, doc_headline in results:
        search_results.append(
            {
                "id": doc.id,
                "title": doc.title,
                "author": doc.author,
                "filename": doc.filename,
                "content_type": doc.content_type,
                "lifecycle_state": doc.lifecycle_state,
                "extraction_status": doc.extraction_status,
                "document_type_name": (
                    doc.document_type.name if doc.document_type else None
                ),
                "headline": doc_headline,
                "rank": float(doc_rank) if doc_rank else 0.0,
            }
        )

    return search_results, total_count
