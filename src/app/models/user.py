import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

user_groups = Table(
    "user_groups",
    BaseModel.metadata,
    Column("user_id", Uuid(), ForeignKey("users.id"), primary_key=True),
    Column("group_id", Uuid(), ForeignKey("groups.id"), primary_key=True),
)

user_roles = Table(
    "user_roles",
    BaseModel.metadata,
    Column("user_id", Uuid(), ForeignKey("users.id"), primary_key=True),
    Column("role_id", Uuid(), ForeignKey("roles.id"), primary_key=True),
)


class User(BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    groups: Mapped[list["Group"]] = relationship(secondary=user_groups, back_populates="users")
    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users")


class Group(BaseModel):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    users: Mapped[list["User"]] = relationship(secondary=user_groups, back_populates="groups")


class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")
