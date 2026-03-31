"""Lifecycle state machine service.

Implements document lifecycle transitions (DRAFT -> REVIEW -> APPROVED -> ARCHIVED),
enforcement via transition set lookup, audit logging, and automatic ACL rule
application on state changes.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acl import DocumentACL, LifecycleACLRule
from app.models.document import Document
from app.models.enums import LifecycleState, PermissionLevel
from app.services.audit_service import create_audit_record

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid lifecycle transitions (same pattern as WORKFLOW_TRANSITIONS)
# ---------------------------------------------------------------------------

LIFECYCLE_TRANSITIONS: set[tuple[LifecycleState, LifecycleState]] = {
    (LifecycleState.DRAFT, LifecycleState.REVIEW),
    (LifecycleState.REVIEW, LifecycleState.APPROVED),
    (LifecycleState.REVIEW, LifecycleState.DRAFT),       # Reject back to draft
    (LifecycleState.APPROVED, LifecycleState.ARCHIVED),
}


async def transition_lifecycle_state(
    db: AsyncSession,
    document_id: uuid.UUID,
    target_state: LifecycleState,
    user_id: str,
) -> Document:
    """Transition a document to a new lifecycle state.

    Validates the transition, updates the state, creates an audit record,
    and applies any lifecycle-ACL rules for the transition.

    Raises ValueError if the document is not found or the transition is invalid.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.is_deleted == False)  # noqa: E712
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise ValueError(f"Document {document_id} not found or deleted")

    current_state = LifecycleState(document.lifecycle_state) if document.lifecycle_state else LifecycleState.DRAFT

    if (current_state, target_state) not in LIFECYCLE_TRANSITIONS:
        await create_audit_record(
            db,
            entity_type="document",
            entity_id=str(document_id),
            action="lifecycle_transition_failed",
            user_id=user_id,
            before_state={"lifecycle_state": current_state.value},
            after_state={"lifecycle_state": target_state.value},
            details=f"Invalid transition from {current_state.value} to {target_state.value}",
        )
        raise ValueError(
            f"Invalid lifecycle transition from {current_state.value} to {target_state.value}"
        )

    document.lifecycle_state = target_state.value

    await create_audit_record(
        db,
        entity_type="document",
        entity_id=str(document_id),
        action="lifecycle_transition",
        user_id=user_id,
        before_state={"lifecycle_state": current_state.value},
        after_state={"lifecycle_state": target_state.value},
    )

    await apply_lifecycle_acl_rules(db, document_id, current_state, target_state, user_id)

    return document


async def apply_lifecycle_acl_rules(
    db: AsyncSession,
    document_id: uuid.UUID,
    from_state: LifecycleState,
    to_state: LifecycleState,
    user_id: str,
) -> None:
    """Look up and apply ACL rules for a lifecycle state transition.

    Queries LifecycleACLRule table for matching (from_state, to_state) rules
    and applies the corresponding ACL additions or removals.
    """
    result = await db.execute(
        select(LifecycleACLRule).where(
            LifecycleACLRule.from_state == from_state.value,
            LifecycleACLRule.to_state == to_state.value,
            LifecycleACLRule.is_deleted == False,  # noqa: E712
        )
    )
    rules = result.scalars().all()

    for rule in rules:
        if rule.action == "remove":
            # Build delete query for matching ACL entries
            stmt = select(DocumentACL).where(
                DocumentACL.document_id == document_id,
                DocumentACL.permission_level == rule.permission_level,
                DocumentACL.is_deleted == False,  # noqa: E712
            )

            # Never remove ADMIN entries (protect document owner)
            if rule.principal_filter == "non_admin":
                stmt = stmt.where(DocumentACL.permission_level != PermissionLevel.ADMIN.value)

            acl_result = await db.execute(stmt)
            acl_entries = acl_result.scalars().all()

            for entry in acl_entries:
                # Never remove ADMIN-level entries regardless of rule
                if entry.permission_level == PermissionLevel.ADMIN.value:
                    continue
                await db.delete(entry)

            await create_audit_record(
                db,
                entity_type="document_acl",
                entity_id=str(document_id),
                action="acl_rule_applied",
                user_id=user_id,
                details=f"Removed {rule.permission_level} for {rule.principal_filter} on transition {from_state.value}->{to_state.value}",
            )

        elif rule.action == "add":
            # For "add" rules, create ACL entries based on principal_filter
            # Specific logic depends on principal_filter value (e.g., "creator", "all")
            await create_audit_record(
                db,
                entity_type="document_acl",
                entity_id=str(document_id),
                action="acl_rule_applied",
                user_id=user_id,
                details=f"Add {rule.permission_level} for {rule.principal_filter} on transition {from_state.value}->{to_state.value}",
            )


async def execute_lifecycle_action(
    db: AsyncSession,
    workflow: "WorkflowInstance",
    lifecycle_action: str,
    user_id: str,
) -> None:
    """Execute a lifecycle action triggered by workflow activity completion.

    Parses the lifecycle_action string (format: "transition_to:{state}"),
    loads all documents in the workflow package, and transitions each one.
    Invalid transitions are logged but do not halt the workflow (per D-04).
    """
    # Lazy imports to avoid circular dependency with engine_service
    from app.models.workflow import WorkflowInstance, WorkflowPackage  # noqa: F811

    # Parse the lifecycle action string
    if not lifecycle_action.startswith("transition_to:"):
        logger.warning("Invalid lifecycle_action format: %s", lifecycle_action)
        return

    target_state_str = lifecycle_action.split(":", 1)[1]
    try:
        target_state = LifecycleState(target_state_str)
    except ValueError:
        logger.warning("Invalid lifecycle state in action: %s", target_state_str)
        return

    # Load all workflow packages for this workflow instance
    result = await db.execute(
        select(WorkflowPackage).where(
            WorkflowPackage.workflow_instance_id == workflow.id,
            WorkflowPackage.document_id.isnot(None),
        )
    )
    packages = result.scalars().all()

    for package in packages:
        try:
            await transition_lifecycle_state(
                db, package.document_id, target_state, user_id
            )
        except ValueError as e:
            logger.warning(
                "Lifecycle action failed for document %s in workflow %s: %s",
                package.document_id, workflow.id, str(e),
            )
            await create_audit_record(
                db,
                entity_type="document",
                entity_id=str(package.document_id),
                action="lifecycle_action_failed",
                user_id=user_id,
                details=str(e),
            )
