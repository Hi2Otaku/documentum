import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.user import Group, Role, User
from app.schemas.user import GroupCreate, RoleCreate, UserCreate, UserUpdate
from app.services.audit_service import create_audit_record


def _user_to_dict(user: User) -> dict:
    """Serialize a User to a dict for audit state snapshots."""
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }


def _group_to_dict(group: Group) -> dict:
    """Serialize a Group to a dict for audit state snapshots."""
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
    }


def _role_to_dict(role: Role) -> dict:
    """Serialize a Role to a dict for audit state snapshots."""
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
    }


# --- User CRUD ---


async def create_user(
    db: AsyncSession, data: UserCreate, user_id: str | None
) -> User:
    """Create a new user. Raises 409 if username already exists."""
    result = await db.execute(
        select(User).where(
            User.username == data.username,
            User.is_deleted == False,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{data.username}' already exists",
        )

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        is_superuser=data.is_superuser,
        is_active=True,
        created_by=user_id,
    )
    db.add(user)
    await db.flush()  # Populate id and defaults

    await create_audit_record(
        db,
        entity_type="user",
        entity_id=str(user.id),
        action="create",
        user_id=user_id,
        after_state=_user_to_dict(user),
    )

    return user


async def get_user(db: AsyncSession, user_id_param: uuid.UUID) -> User:
    """Get a single user by ID. Raises 404 if not found."""
    result = await db.execute(
        select(User).where(
            User.id == user_id_param,
            User.is_deleted == False,  # noqa: E712
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def list_users(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[User], int]:
    """List users with pagination. Returns (users, total_count)."""
    count_result = await db.execute(
        select(func.count()).select_from(User).where(
            User.is_deleted == False  # noqa: E712
        )
    )
    total_count = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(User)
        .where(User.is_deleted == False)  # noqa: E712
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    users = list(result.scalars().all())

    return users, total_count


async def update_user(
    db: AsyncSession,
    user_id_param: uuid.UUID,
    data: UserUpdate,
    acting_user_id: str | None,
) -> User:
    """Update a user. Raises 404 if not found."""
    user = await get_user(db, user_id_param)
    before_state = _user_to_dict(user)

    update_data = data.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"] is not None:
        user.hashed_password = hash_password(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    after_state = _user_to_dict(user)

    await create_audit_record(
        db,
        entity_type="user",
        entity_id=str(user.id),
        action="update",
        user_id=acting_user_id,
        before_state=before_state,
        after_state=after_state,
    )

    return user


async def delete_user(
    db: AsyncSession,
    user_id_param: uuid.UUID,
    acting_user_id: str | None,
) -> None:
    """Soft delete a user. Raises 404 if not found."""
    user = await get_user(db, user_id_param)
    before_state = _user_to_dict(user)

    user.is_deleted = True

    await create_audit_record(
        db,
        entity_type="user",
        entity_id=str(user.id),
        action="delete",
        user_id=acting_user_id,
        before_state=before_state,
    )


# --- Group CRUD ---


async def create_group(
    db: AsyncSession, data: GroupCreate, user_id: str | None
) -> Group:
    """Create a new group. Raises 409 if name already exists."""
    result = await db.execute(
        select(Group).where(
            Group.name == data.name,
            Group.is_deleted == False,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Group '{data.name}' already exists",
        )

    group = Group(
        name=data.name,
        description=data.description,
        created_by=user_id,
    )
    db.add(group)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="group",
        entity_id=str(group.id),
        action="create",
        user_id=user_id,
        after_state=_group_to_dict(group),
    )

    return group


async def list_groups(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[Group], int]:
    """List groups with pagination."""
    count_result = await db.execute(
        select(func.count()).select_from(Group).where(
            Group.is_deleted == False  # noqa: E712
        )
    )
    total_count = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Group)
        .where(Group.is_deleted == False)  # noqa: E712
        .order_by(Group.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    groups = list(result.scalars().all())

    return groups, total_count


async def add_users_to_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_ids: list[uuid.UUID],
    acting_user_id: str | None,
) -> Group:
    """Add users to a group. Raises 404 if group or any user not found."""
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.users))
        .where(
            Group.id == group_id,
            Group.is_deleted == False,  # noqa: E712
        )
    )
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    for uid in user_ids:
        user = await get_user(db, uid)
        if user not in group.users:
            group.users.append(user)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="group",
        entity_id=str(group.id),
        action="update",
        user_id=acting_user_id,
        details=f"Added users to group: {[str(uid) for uid in user_ids]}",
    )

    return group


# --- Role CRUD ---


async def create_role(
    db: AsyncSession, data: RoleCreate, user_id: str | None
) -> Role:
    """Create a new role. Raises 409 if name already exists."""
    result = await db.execute(
        select(Role).where(
            Role.name == data.name,
            Role.is_deleted == False,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{data.name}' already exists",
        )

    role = Role(
        name=data.name,
        description=data.description,
        created_by=user_id,
    )
    db.add(role)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="role",
        entity_id=str(role.id),
        action="create",
        user_id=user_id,
        after_state=_role_to_dict(role),
    )

    return role


async def list_roles(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[Role], int]:
    """List roles with pagination."""
    count_result = await db.execute(
        select(func.count()).select_from(Role).where(
            Role.is_deleted == False  # noqa: E712
        )
    )
    total_count = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Role)
        .where(Role.is_deleted == False)  # noqa: E712
        .order_by(Role.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    roles = list(result.scalars().all())

    return roles, total_count


async def assign_role_to_user(
    db: AsyncSession,
    user_id_param: uuid.UUID,
    role_id: uuid.UUID,
    acting_user_id: str | None,
) -> User:
    """Assign a role to a user. Raises 404 if user or role not found."""
    # Eagerly load roles to avoid lazy-loading in async context
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(
            User.id == user_id_param,
            User.is_deleted == False,  # noqa: E712
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = await db.execute(
        select(Role).where(
            Role.id == role_id,
            Role.is_deleted == False,  # noqa: E712
        )
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    if role not in user.roles:
        user.roles.append(role)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="user",
        entity_id=str(user.id),
        action="update",
        user_id=acting_user_id,
        details=f"Assigned role '{role.name}' to user '{user.username}'",
    )

    return user
