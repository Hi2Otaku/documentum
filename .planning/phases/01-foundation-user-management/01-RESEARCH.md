# Phase 1: Foundation & User Management - Research

**Researched:** 2026-03-30
**Domain:** FastAPI + PostgreSQL containerized stack, data model, auth, audit trail
**Confidence:** HIGH

## Summary

Phase 1 establishes the entire project foundation: Docker Compose orchestration for five services (FastAPI, PostgreSQL, Redis, MinIO, Celery), the database schema for Documentum's core object types, user/group/role management with JWT authentication, and an append-only audit trail that captures every mutation from day one.

The stack decisions are locked (FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Alembic, Celery, Redis, MinIO). Two critical library substitutions are needed from the original STACK.md recommendations: **python-jose is abandoned** and must be replaced with PyJWT, and **passlib is dead on Python 3.13+** (this system runs Python 3.14) and must be replaced with either pwdlib or direct bcrypt usage.

**Primary recommendation:** Build the project in a layered structure (routers -> services -> models) with the audit trail implemented as a service-layer concern (not middleware-only). Establish the common SQLAlchemy base model, Alembic migrations, Docker Compose stack, and test infrastructure in the first wave before building any features.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Template + Instance split -- separate tables for design-time (process_templates, activity_templates) and runtime (workflow_instances, activity_instances, work_items). Mirrors Documentum's dm_process vs dm_workflow.
- **D-02:** Copy-on-write template versioning -- installing creates a frozen snapshot row. Edits create a new row with incremented version. Running instances reference the snapshot they started with.
- **D-03:** Flows stored as a junction table -- a 'flows' table with source_activity_id, target_activity_id, flow_type (normal/reject), and condition expression. Standard relational approach.
- **D-04:** Process variables use typed columns table -- a 'process_variables' table with name, type, and separate value columns (string_value, int_value, bool_value, date_value). Type-safe queries.
- **D-05:** Workflow packages as many-to-many junction -- a 'workflow_packages' junction table linking workflow instances to documents, with package_name and activity-level tracking.
- **D-06:** Soft deletes everywhere -- is_deleted flag on all tables. Preserves audit trail integrity and enables recovery.
- **D-07:** UUID primary keys on all tables.
- **D-08:** UTC timestamps everywhere -- frontend converts to local time for display.
- **D-09:** Alembic for database migrations.
- **D-10:** Common base model -- all SQLAlchemy models inherit from a base with id (UUID), created_at, updated_at, created_by, is_deleted.
- **D-11:** PostgreSQL native ENUMs for workflow states, activity types, flow types.
- **D-12:** JWT stateless authentication -- no server-side session storage. Token contains user info.
- **D-13:** bcrypt for password hashing.
- **D-14:** Admin user seeded on first startup from environment variables.
- **D-15:** Audit records created via middleware/decorator -- automatic capture on all API endpoints, including background tasks.
- **D-16:** Full before/after state -- store complete object state (as JSON) before and after each change. Enables diff views.
- **D-17:** Single audit_log table -- entity_type, entity_id, action, user_id, timestamp, before_state (JSONB), after_state (JSONB). Simpler cross-entity queries.
- **D-18:** Versioned URL prefix -- /api/v1/workflows, /api/v1/documents, /api/v1/users.
- **D-19:** Envelope response format -- all responses wrapped: {"data": {...}, "meta": {...}, "errors": [...]}.
- **D-20:** Offset-based pagination -- ?page=2&page_size=20.

### Claude's Discretion
- JWT expiry duration and refresh strategy
- Exact Docker Compose service configuration and networking
- FastAPI project structure (routers, services, models organization)
- Redis usage pattern (caching, Celery broker, or both)
- Exact base model implementation details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | System runs via Docker Compose with FastAPI, PostgreSQL, Redis, MinIO, and Celery workers | Docker Compose service definitions, health checks, networking -- see Architecture Patterns |
| FOUND-02 | Database schema implements the 5 core Documentum object types: Process, Activity, Flow, Package, WorkItem | SQLAlchemy models with common base, Alembic migrations -- see Architecture Patterns and Code Examples |
| FOUND-03 | All schema tables include created_at, updated_at, and created_by audit columns | Common base model pattern with id, created_at, updated_at, created_by, is_deleted -- see Code Examples |
| USER-01 | Admin can create user accounts with username and password | User model + CRUD service + bcrypt hashing via pwdlib or bcrypt directly |
| USER-02 | User can log in and receive a session token | JWT auth with PyJWT, OAuth2PasswordBearer flow -- see Code Examples |
| USER-03 | Admin can create groups and assign users to groups | Group model with M2M user_groups junction table |
| USER-04 | Admin can define roles (e.g., Reviewer, Approver, Director) | Role model or PostgreSQL ENUM for built-in roles + custom role table |
| AUDIT-01 | Every workflow action is logged: who, what, when, decision, and affected objects | Single audit_log table with JSONB before/after state -- see Code Examples |
| AUDIT-02 | Audit records include: task assignment, task completion, task rejection, workflow state changes | Audit service captures entity_type + action, extensible for all future event types |
| AUDIT-03 | Audit records include: document upload, version creation, check-in/out, lifecycle transitions | Same audit_log table -- schema designed to accommodate all entity types from Phase 1 onward |
| AUDIT-04 | Audit trail is append-only and cannot be modified or deleted | Database-level constraint: REVOKE UPDATE, DELETE on audit_log table + no soft-delete on this table |
</phase_requirements>

## Standard Stack

### Core (Phase 1 specific)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.2 | HTTP API framework | Locked decision. Native async, Pydantic integration, OpenAPI docs |
| uvicorn | 0.42.0 | ASGI server | Standard production server for FastAPI |
| SQLAlchemy | 2.0.48 | Async ORM | Locked decision. Full async via asyncpg, declarative models |
| Alembic | 1.18.4 | Database migrations | Locked decision (D-09). Auto-generates from model changes |
| asyncpg | 0.31.0 | Async PostgreSQL driver | Fastest Python PG driver, required for SQLAlchemy async engine |
| Pydantic | 2.12.5 | Request/response validation | FastAPI's native validation layer |
| pydantic-settings | 2.13.1 | Configuration from env vars | Type-safe config for DB URLs, secrets, JWT settings |
| PyJWT | 2.12.1 | JWT token creation/verification | **Replaces python-jose** which is abandoned. FastAPI community has migrated to PyJWT |
| pwdlib[bcrypt] | 0.3.0 | Password hashing | **Replaces passlib** which is dead on Python 3.13+. Modern maintained alternative by FastAPI-Users author |
| Celery | 5.6.3 | Task queue / worker system | Locked decision. Broker = Redis. Used for background audit + future workflow engine |
| redis | 7.4.0 | Python Redis client | Async support via redis.asyncio. Celery broker + optional caching |
| python-multipart | 0.0.22 | Form data parsing | Required by FastAPI for OAuth2PasswordRequestForm |
| PostgreSQL | 16+ | Primary database | Locked decision. JSONB for audit state, native ENUMs |
| Redis | 7.x | Message broker | Celery broker. Optionally cache layer later |
| MinIO | latest | S3-compatible object storage | Locked decision. Service present in Compose, but not actively used until Phase 2 |

### Dev/Test

| Library | Version | Purpose |
|---------|---------|---------|
| pytest | 9.0.2 | Test framework |
| pytest-asyncio | 1.3.0 | Async test support for SQLAlchemy/FastAPI |
| httpx | 0.28.1 | Async HTTP test client (FastAPI recommended) |
| pytest-cov | 7.1.0 | Coverage reporting |
| ruff | 0.15.8 | Linter + formatter (replaces flake8+black+isort) |

### Critical Library Substitutions

| Original Recommendation | Replacement | Reason |
|--------------------------|-------------|--------|
| python-jose[cryptography] 3.3.x | PyJWT 2.12.1 | python-jose is abandoned (last meaningful release ~2022). FastAPI community has migrated. PyJWT is actively maintained |
| passlib[bcrypt] 1.7.x | pwdlib[bcrypt] 0.3.0 | passlib is dead, broken on Python 3.13+ (uses removed `crypt` module). System runs Python 3.14. pwdlib is the modern replacement by the FastAPI-Users maintainer |

**Installation:**
```bash
# Core dependencies
pip install fastapi[standard] uvicorn sqlalchemy[asyncio] asyncpg alembic pydantic pydantic-settings PyJWT "pwdlib[bcrypt]" celery redis python-multipart

# Dev/test dependencies
pip install pytest pytest-asyncio httpx pytest-cov ruff
```

## Architecture Patterns

### Recommended Project Structure

```
documentum_clone/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py                    # FastAPI app factory, lifespan events
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py              # pydantic-settings: Settings class
│       │   ├── database.py            # async engine, session factory
│       │   ├── security.py            # JWT encode/decode, password hashing
│       │   └── dependencies.py        # get_db, get_current_user
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py                # Common base model (D-10)
│       │   ├── user.py                # User, Group, Role, user_groups
│       │   ├── audit.py               # AuditLog
│       │   ├── workflow.py            # ProcessTemplate, ActivityTemplate, FlowTemplate
│       │   └── enums.py               # PostgreSQL ENUMs (D-11)
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── user.py                # Pydantic: UserCreate, UserResponse, etc.
│       │   ├── auth.py                # Token, LoginRequest
│       │   ├── audit.py               # AuditLogResponse
│       │   └── common.py              # EnvelopeResponse, PaginationMeta (D-19, D-20)
│       ├── services/
│       │   ├── __init__.py
│       │   ├── user_service.py        # CRUD for users, groups, roles
│       │   ├── auth_service.py        # Login, token creation
│       │   └── audit_service.py       # create_audit_record()
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── auth.py                # POST /api/v1/auth/login
│       │   ├── users.py               # CRUD /api/v1/users
│       │   ├── groups.py              # CRUD /api/v1/groups
│       │   ├── roles.py               # CRUD /api/v1/roles
│       │   └── health.py              # GET /api/v1/health
│       └── middleware/
│           ├── __init__.py
│           └── audit.py               # Request-level audit context
├── tests/
│   ├── conftest.py                    # Fixtures: async client, test DB, test user
│   ├── test_health.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_groups.py
│   ├── test_roles.py
│   └── test_audit.py
└── scripts/
    └── seed_admin.py                  # Seed admin user (D-14)
```

**Rationale:** Module-by-type structure (routers/, services/, models/) is standard for FastAPI monoliths. Each domain (users, auth, audit) gets its own router, service, model, and schema file. This scales well and avoids circular imports.

### Pattern 1: Common Base Model (D-10)

**What:** All SQLAlchemy models inherit from a shared base providing id (UUID), created_at, updated_at, created_by, is_deleted.
**When to use:** Every single model in the system.

```python
# src/app/models/base.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
```

### Pattern 2: Async Database Session as Dependency

**What:** FastAPI dependency injection yields an async SQLAlchemy session per request.
**When to use:** Every route that touches the database.

```python
# src/app/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# src/app/core/dependencies.py
from typing import AsyncGenerator

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Pattern 3: Envelope Response (D-19)

**What:** All API responses wrapped in a standard envelope.
**When to use:** Every API endpoint.

```python
# src/app/schemas/common.py
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int

class EnvelopeResponse(BaseModel, Generic[T]):
    data: T | None = None
    meta: dict[str, Any] | PaginationMeta | None = None
    errors: list[dict[str, Any]] = []
```

### Pattern 4: Audit Service (D-15, D-16, D-17)

**What:** A service-layer function that creates audit records. Called explicitly from service methods, not purely via middleware. Middleware sets request context (user, IP, request_id); service layer calls `audit_service.log()` with entity-specific before/after state.
**When to use:** Every create/update/delete operation.

```python
# src/app/services/audit_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog

async def create_audit_record(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: str,
    action: str,        # "create", "update", "delete"
    user_id: str | None,
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> AuditLog:
    record = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        before_state=before_state,
        after_state=after_state,
    )
    db.add(record)
    # Do NOT commit here -- let the request transaction handle it
    # This ensures audit record and data change are atomic
    return record
```

**Why service-layer, not pure middleware:** Middleware cannot see before/after entity state -- it only sees HTTP request/response bodies. For D-16 (full before/after state as JSON), the service layer must serialize the entity before modification, apply the change, then serialize after. The audit record is written in the same transaction as the data change.

### Pattern 5: JWT Authentication (D-12)

**What:** Stateless JWT with PyJWT. OAuth2PasswordBearer for token extraction.

```python
# src/app/core/security.py
import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings

ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
```

### Anti-Patterns to Avoid

- **Audit via middleware only:** Middleware cannot capture before/after entity state (D-16). Use middleware for request context, service layer for entity-level audit.
- **Committing inside service functions:** Let the dependency injection session handle commit/rollback. Services should add to the session but not commit, ensuring atomicity of audit + data changes.
- **Sync database calls in async routes:** Always use `AsyncSession` and `await`. Never call sync SQLAlchemy methods from async FastAPI routes.
- **Mutable audit records:** The audit_log table must be INSERT-only. Enforce with database REVOKE and by never writing UPDATE/DELETE queries against it.
- **Storing passwords in JWT claims:** JWT payload should contain user_id and minimal claims only. Never include the password hash.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom hash function | pwdlib[bcrypt] | Timing attacks, salt management, algorithm selection -- all solved |
| JWT creation/validation | Manual token parsing | PyJWT | Expiry validation, algorithm verification, claim extraction |
| Request validation | Manual field checking | Pydantic models (FastAPI) | Type coercion, error formatting, OpenAPI schema generation |
| Database migrations | Manual ALTER TABLE | Alembic auto-generation | Dependency tracking, rollback, version history |
| Config from env vars | os.environ.get() | pydantic-settings | Type validation, defaults, .env file loading |
| UUID generation | Custom ID schemes | PostgreSQL gen_random_uuid() + Python uuid4 | Collision resistance, sortability, standard format |
| CORS handling | Custom headers | FastAPI CORSMiddleware | Preflight handling, origin validation |

## Common Pitfalls

### Pitfall 1: passlib Breaks on Python 3.13+

**What goes wrong:** passlib uses the removed `crypt` module. Import fails on Python 3.13+.
**Why it happens:** passlib has not been maintained since 2020. Python 3.13 removed the `crypt` module per PEP 594.
**How to avoid:** Use pwdlib[bcrypt] instead. It has the same hash/verify API pattern.
**Warning signs:** ImportError on `from passlib.context import CryptContext`.

### Pitfall 2: python-jose Is Abandoned

**What goes wrong:** Security vulnerabilities go unpatched. Incompatibilities with new Python versions emerge.
**Why it happens:** Last meaningful release was 2022. FastAPI's own documentation discussions recommend migrating away.
**How to avoid:** Use PyJWT. Drop-in replacement for HS256 JWT use cases. Different API but simpler.
**Warning signs:** Any online tutorial using `from jose import jwt` is outdated.

### Pitfall 3: Audit Trail Not Atomic with Data Changes

**What goes wrong:** Audit record is written in a separate transaction from the data change. If the data change succeeds but audit write fails (or vice versa), the audit trail has gaps.
**Why it happens:** Writing audit in middleware after response, or in a separate Celery task.
**How to avoid:** Write the audit record in the SAME database transaction as the data change. Use the service layer pattern where both happen before session.commit().
**Warning signs:** Audit records with no corresponding data changes, or data changes with no audit record.

### Pitfall 4: Alembic env.py Not Configured for Async

**What goes wrong:** `alembic upgrade head` fails because the default env.py uses sync connections, but the project uses asyncpg.
**Why it happens:** Alembic's default template is sync. Async requires explicit configuration.
**How to avoid:** Use `alembic init -t async` when initializing Alembic, or manually configure env.py with `run_async` and `AsyncEngine`.
**Warning signs:** `NotImplementedError` or `asyncpg` driver errors during migration.

### Pitfall 5: Missing Import of All Models Before Migration Auto-Generation

**What goes wrong:** `alembic revision --autogenerate` produces empty migrations because Alembic does not see the SQLAlchemy models.
**Why it happens:** Models must be imported before `Base.metadata` is inspected. If models are in separate files and not imported in env.py, their tables are invisible.
**How to avoid:** In alembic/env.py, import the Base from models and ensure all model modules are imported (e.g., `from app.models import base, user, audit, workflow`).
**Warning signs:** Auto-generated migration with no operations despite new models existing.

### Pitfall 6: PostgreSQL ENUM Migration Pain

**What goes wrong:** After creating a PostgreSQL ENUM type, adding new values requires manual Alembic migration code (ALTER TYPE ... ADD VALUE). Alembic's autogenerate does not handle ENUM value additions.
**Why it happens:** PostgreSQL ENUMs are database-level types, not just column constraints. They have their own lifecycle.
**How to avoid:** Start with all known values in the initial ENUM. For future additions, write manual migration steps. Consider using a CHECK constraint on a VARCHAR column if values change frequently.
**Warning signs:** Auto-generated migrations that try to drop and recreate ENUM types (this fails if columns reference them).

### Pitfall 7: Docker Compose Health Check Missing

**What goes wrong:** FastAPI container starts before PostgreSQL is ready to accept connections. SQLAlchemy connection fails on startup.
**Why it happens:** Docker Compose `depends_on` only waits for container start, not service readiness.
**How to avoid:** Use `depends_on` with `condition: service_healthy` and define `healthcheck` on the PostgreSQL service using `pg_isready`.
**Warning signs:** Intermittent startup failures, "connection refused" errors on first request.

## Code Examples

### Docker Compose Configuration

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://docuser:docpass@db:5432/documentum
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=change-me-in-production
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=admin
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./src:/app/src
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: docuser
      POSTGRES_PASSWORD: docpass
      POSTGRES_DB: documentum
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U docuser -d documentum"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - miniodata:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 5

  celery-worker:
    build: .
    environment:
      - DATABASE_URL=postgresql+asyncpg://docuser:docpass@db:5432/documentum
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: celery -A app.celery_app worker --loglevel=info

  celery-beat:
    build: .
    environment:
      - DATABASE_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    command: celery -A app.celery_app beat --loglevel=info

volumes:
  pgdata:
  miniodata:
```

### Audit Log Model (D-17)

```python
# src/app/models/audit.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AuditLog(Base):
    """Append-only audit trail. No updates or deletes allowed."""
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # create, update, delete
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Note: AuditLog does NOT inherit from BaseModel (no is_deleted, no updated_at). It is append-only with its own minimal schema. Enforce immutability with a database migration that REVOKEs UPDATE and DELETE privileges on this table for the application role.

### User and Group Models

```python
# src/app/models/user.py
from sqlalchemy import Boolean, Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

# M2M junction: users <-> groups
user_groups = Table(
    "user_groups",
    BaseModel.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("group_id", UUID(as_uuid=True), ForeignKey("groups.id"), primary_key=True),
)

# M2M junction: users <-> roles
user_roles = Table(
    "user_roles",
    BaseModel.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)


class User(BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    groups = relationship("Group", secondary=user_groups, back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")


class Group(BaseModel):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    users = relationship("User", secondary=user_groups, back_populates="groups")


class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    users = relationship("User", secondary=user_roles, back_populates="roles")
```

### Workflow Schema Tables (Skeleton for Phase 1)

```python
# src/app/models/enums.py
import enum

class ProcessState(str, enum.Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"

class ActivityType(str, enum.Enum):
    START = "start"
    END = "end"
    MANUAL = "manual"
    AUTO = "auto"

class FlowType(str, enum.Enum):
    NORMAL = "normal"
    REJECT = "reject"

class WorkflowState(str, enum.Enum):
    DORMANT = "dormant"
    RUNNING = "running"
    HALTED = "halted"
    FAILED = "failed"
    FINISHED = "finished"

class WorkItemState(str, enum.Enum):
    ACQUIRED = "acquired"
    AVAILABLE = "available"
    DELEGATED = "delegated"
    COMPLETE = "complete"
```

### Password Hashing with pwdlib

```python
# src/app/core/security.py (password section)
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
```

### Admin Seeding (D-14)

```python
# In app lifespan or startup event
from app.core.config import settings
from app.core.security import hash_password

async def seed_admin_user(db: AsyncSession) -> None:
    """Create admin user from env vars if not exists."""
    result = await db.execute(
        select(User).where(User.username == settings.admin_username)
    )
    if result.scalar_one_or_none() is None:
        admin = User(
            username=settings.admin_username,
            hashed_password=hash_password(settings.admin_password),
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)
        await db.commit()
```

### Append-Only Enforcement via Migration

```python
# In an Alembic migration after creating audit_log table
def upgrade():
    # ... create audit_log table ...

    # Enforce append-only: revoke UPDATE and DELETE on audit_log for app user
    op.execute("""
        REVOKE UPDATE, DELETE ON TABLE audit_log FROM docuser;
    """)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose for JWT | PyJWT | 2024-2025 | python-jose abandoned; FastAPI community migrated |
| passlib for password hashing | pwdlib or direct bcrypt | 2024-2025 | passlib broken on Python 3.13+ (removed crypt module) |
| SQLAlchemy 1.x sync | SQLAlchemy 2.0 async (Mapped type hints) | 2023 | New declarative style with mapped_column, native async |
| Alembic sync-only | Alembic async template | 2023 | `alembic init -t async` generates async-compatible env.py |
| Pydantic v1 | Pydantic v2 | 2023 | 5-50x faster, model_validator replaces root_validator |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | none -- must be created in Wave 0 (pyproject.toml [tool.pytest.ini_options]) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --cov=app --cov-report=term-missing` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | Docker Compose stack starts and API responds to health check | smoke | `docker compose up -d && curl http://localhost:8000/api/v1/health` | No -- Wave 0 |
| FOUND-02 | Database schema has tables for Process, Activity, Flow, Package, WorkItem | integration | `pytest tests/test_schema.py -x` | No -- Wave 0 |
| FOUND-03 | All tables have created_at, updated_at, created_by columns | unit | `pytest tests/test_base_model.py -x` | No -- Wave 0 |
| USER-01 | Admin can create user with username and password | integration | `pytest tests/test_users.py::test_create_user -x` | No -- Wave 0 |
| USER-02 | User can login and receive JWT token | integration | `pytest tests/test_auth.py::test_login -x` | No -- Wave 0 |
| USER-03 | Admin can create groups and assign users | integration | `pytest tests/test_groups.py::test_create_group -x` | No -- Wave 0 |
| USER-04 | Admin can define roles | integration | `pytest tests/test_roles.py::test_create_role -x` | No -- Wave 0 |
| AUDIT-01 | Create/update/delete operations produce audit records | integration | `pytest tests/test_audit.py::test_audit_on_create -x` | No -- Wave 0 |
| AUDIT-02 | Audit records capture entity type, action, user | integration | `pytest tests/test_audit.py::test_audit_fields -x` | No -- Wave 0 |
| AUDIT-03 | Audit records include before/after state as JSONB | integration | `pytest tests/test_audit.py::test_before_after_state -x` | No -- Wave 0 |
| AUDIT-04 | Audit trail is append-only (no update/delete) | integration | `pytest tests/test_audit.py::test_append_only -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (quick run, stop on first failure)
- **Per wave merge:** `pytest tests/ -v --cov=app --cov-report=term-missing`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `pyproject.toml` -- pytest config section ([tool.pytest.ini_options] with asyncio_mode = "auto")
- [ ] `tests/conftest.py` -- shared fixtures (async test client, test DB session, test user/admin)
- [ ] `tests/test_health.py` -- covers FOUND-01 (health endpoint)
- [ ] `tests/test_schema.py` -- covers FOUND-02 (table existence verification)
- [ ] `tests/test_base_model.py` -- covers FOUND-03 (base model columns)
- [ ] Framework install: `pip install pytest pytest-asyncio httpx pytest-cov`

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.14.3 | -- |
| Docker | Containerization | Yes | 29.2.1 | -- |
| Docker Compose | Orchestration | Yes | v5.0.2 | -- |
| pip | Package installation | Yes | 25.3 | -- |
| Node.js | Frontend (future) | Yes | 25.8.0 | Not needed for Phase 1 |
| PostgreSQL (via Docker) | Database | Via Docker | 16+ (image) | -- |
| Redis (via Docker) | Celery broker | Via Docker | 7.x (image) | -- |
| MinIO (via Docker) | File storage | Via Docker | latest (image) | -- |

**Missing dependencies with no fallback:** None -- all dependencies available.

**Note on Python 3.14:** Python 3.14 is installed locally. This is fine for development but requires attention to library compatibility. SQLAlchemy 2.0.48, asyncpg 0.31.0, Celery 5.6.3 all support Python 3.14. The critical issue is that **passlib does NOT work on Python 3.14** -- use pwdlib instead (see Critical Library Substitutions above).

## Open Questions

1. **JWT Expiry and Refresh Strategy (Claude's Discretion)**
   - What we know: D-12 says stateless JWT, no server-side sessions
   - Recommendation: 30-minute access token expiry. No refresh tokens for v1 (simplicity). User re-authenticates when token expires. Add refresh tokens in v2 if needed.

2. **Redis Usage Pattern (Claude's Discretion)**
   - What we know: Redis is in the stack as Celery broker
   - Recommendation: Use Redis only as Celery broker in Phase 1. Caching can be added later when performance data shows it is needed. Avoids premature optimization.

3. **Role Model Design**
   - What we know: D-04 mentions roles like Reviewer, Approver, Director. No decision on whether roles are an ENUM or a table.
   - Recommendation: Use a `roles` table (not ENUM) because users should be able to define custom roles. Pre-seed standard roles (Admin, Reviewer, Approver, Director) via migration.

4. **Celery Sync vs Async in Phase 1**
   - What we know: Celery workers are sync. SQLAlchemy async sessions cannot be directly used in Celery tasks.
   - Recommendation: In Phase 1, Celery is only set up (not heavily used). When tasks are needed later, use `async_to_sync` from asgiref or create a separate sync SQLAlchemy engine for Celery workers.

## Sources

### Primary (HIGH confidence)
- PyPI package index -- verified all library versions via `pip index versions` (2026-03-30)
- [FastAPI Official Docs - Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) -- project structure
- [SQLAlchemy 2.0 Async Docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) -- async session patterns
- [Alembic 1.18 Docs](https://alembic.sqlalchemy.org/) -- migration configuration

### Secondary (MEDIUM confidence)
- [FastAPI Discussion #11345 - Abandoning python-jose](https://github.com/fastapi/fastapi/discussions/11345) -- confirmed python-jose deprecation
- [FastAPI Discussion #11773 - passlib unmaintained](https://github.com/fastapi/fastapi/discussions/11773) -- confirmed passlib incompatibility
- [pwdlib introduction by FastAPI-Users author](https://www.francoisvoron.com/blog/introducing-pwdlib-a-modern-password-hash-helper-for-python) -- pwdlib as passlib replacement
- [FastAPI + SQLAlchemy 2.0 Modern Async Patterns](https://dev-faizan.medium.com/fastapi-sqlalchemy-2-0-modern-async-database-patterns-7879d39b6843) -- dependency injection pattern
- [Audit Log Design in FastAPI](https://blog.greeden.me/en/2026/03/17/a-practical-introduction-to-audit-log-design-in-fastapi-design-and-implementation-patterns-for-safely-recording-who-did-what-and-when/) -- audit trail design patterns
- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) -- project structure conventions

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against PyPI, compatibility confirmed
- Architecture: HIGH -- standard FastAPI project structure, well-documented patterns
- Pitfalls: HIGH -- python-jose/passlib issues confirmed by FastAPI maintainers, audit patterns from multiple sources

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable ecosystem, 30-day validity)
