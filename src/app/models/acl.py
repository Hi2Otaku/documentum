import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import LifecycleState, PermissionLevel


class DocumentACL(BaseModel):
    __tablename__ = "document_acl"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "principal_id", "principal_type", "permission_level",
            name="uq_document_acl_entry",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False, index=True
    )
    principal_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    permission_level: Mapped[str] = mapped_column(
        Enum(PermissionLevel, name="permissionlevel"), nullable=False
    )

    document = relationship("Document")


class LifecycleACLRule(BaseModel):
    __tablename__ = "lifecycle_acl_rules"

    from_state: Mapped[str] = mapped_column(
        Enum(LifecycleState, name="lifecyclestate"), nullable=False
    )
    to_state: Mapped[str] = mapped_column(
        Enum(LifecycleState, name="lifecyclestate"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    permission_level: Mapped[str] = mapped_column(
        Enum(PermissionLevel, name="permissionlevel"), nullable=False
    )
    principal_filter: Mapped[str] = mapped_column(String(50), nullable=False)
