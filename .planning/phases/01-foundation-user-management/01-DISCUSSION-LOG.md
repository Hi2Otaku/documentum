# Phase 1: Foundation & User Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 01-foundation-user-management
**Areas discussed:** Data model strategy, Auth & sessions, Audit trail design, API conventions

---

## Data Model Strategy

### Object Type Mapping
| Option | Description | Selected |
|--------|-------------|----------|
| Template + Instance split | Separate tables for design-time and runtime. Mirrors Documentum's dm_process vs dm_workflow. | ✓ |
| Single table per type | One table with state column distinguishing template vs instance. | |
| You decide | Let Claude pick | |

**User's choice:** Template + Instance split
**Notes:** Clean separation, mirrors Documentum architecture

### Template Versioning
| Option | Description | Selected |
|--------|-------------|----------|
| Copy-on-write | Installing creates frozen snapshot. Edits create new row. Running instances reference snapshot. | ✓ |
| Version column | Same row, version column increments. History in separate table. | |
| You decide | Let Claude pick | |

**User's choice:** Copy-on-write

### Flow Storage
| Option | Description | Selected |
|--------|-------------|----------|
| Junction table | Flows table with source/target activity IDs, flow_type, condition. Standard relational. | ✓ |
| JSON in template | Full flow graph as JSON field on template. | |
| You decide | Let Claude pick | |

**User's choice:** Junction table

### Process Variables Storage
| Option | Description | Selected |
|--------|-------------|----------|
| Typed columns table | Separate value columns per type (string_value, int_value, etc.). Type-safe queries. | ✓ |
| JSON field | Single JSONB column. Flexible but less type enforcement. | |
| You decide | Let Claude pick | |

**User's choice:** Typed columns table

### Workflow Packages
| Option | Description | Selected |
|--------|-------------|----------|
| Many-to-many junction | Junction table linking workflow instances to documents. | ✓ |
| Package as entity | First-class entity with own metadata. | |
| You decide | Let Claude pick | |

**User's choice:** Many-to-many junction

### Soft Delete
| Option | Description | Selected |
|--------|-------------|----------|
| Soft delete | Records marked as deleted but preserved. | ✓ |
| Hard delete | Records actually removed. | |
| You decide | Let Claude pick | |

**User's choice:** Soft delete

### ID Strategy
| Option | Description | Selected |
|--------|-------------|----------|
| UUID primary keys | UUID4 as PKs everywhere. No sequential info leak. | ✓ |
| Auto-increment IDs | Standard integer auto-increment. | |
| Both | Auto-increment internal + UUID public-facing. | |

**User's choice:** UUID primary keys

### Timestamps
| Option | Description | Selected |
|--------|-------------|----------|
| UTC everywhere | All timestamps stored/returned as UTC. Frontend converts. | ✓ |
| Timezone-aware | Store with timezone info (timestamptz). | |
| You decide | Let Claude pick | |

**User's choice:** UTC everywhere

### Migrations
| Option | Description | Selected |
|--------|-------------|----------|
| Alembic | SQLAlchemy's migration tool. Auto-generates from model changes. | ✓ |
| You decide | Let Claude pick | |

**User's choice:** Alembic

### Base Model
| Option | Description | Selected |
|--------|-------------|----------|
| Yes, base model | All models inherit from base with id, created_at, updated_at, created_by, is_deleted. | ✓ |
| No, per-table | Each table defines its own columns. | |
| You decide | Let Claude pick | |

**User's choice:** Yes, base model

### Enum Storage
| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL ENUMs | Native PG enum types. Type-safe at DB level. | ✓ |
| String columns | VARCHAR with application-level validation. | |
| Lookup tables | Separate tables per enum type. | |
| You decide | Let Claude pick | |

**User's choice:** PostgreSQL ENUMs

---

## Auth & Sessions

### Token Strategy
| Option | Description | Selected |
|--------|-------------|----------|
| JWT (stateless) | No server-side session storage. Token contains user info. | ✓ |
| Database sessions | Random token stored in DB. Easy to revoke. | |
| JWT + refresh token | Short-lived JWT + long-lived refresh token in DB. | |
| You decide | Let Claude pick | |

**User's choice:** JWT (stateless)

### Password Hashing
| Option | Description | Selected |
|--------|-------------|----------|
| bcrypt | Battle-tested, widely used, built-in salt. | ✓ |
| argon2 | Password Hashing Competition winner, memory-hard. | |
| You decide | Let Claude pick | |

**User's choice:** bcrypt

### Admin User Creation
| Option | Description | Selected |
|--------|-------------|----------|
| Seed on startup | Default admin from env vars on first boot. | ✓ |
| CLI command | Management command like create-superuser. | |
| You decide | Let Claude pick | |

**User's choice:** Seed on startup

---

## Audit Trail Design

### Audit Implementation
| Option | Description | Selected |
|--------|-------------|----------|
| Middleware/decorator | Automatic capture via FastAPI middleware. | ✓ |
| Explicit service | AuditService.log() call at each operation. | |
| SQLAlchemy events | Hook into after_insert/after_update/after_delete. | |
| You decide | Let Claude pick | |

**User's choice:** Middleware/decorator

### Detail Level
| Option | Description | Selected |
|--------|-------------|----------|
| Action + object ref | Lightweight: who, what, which object, when. | |
| Full before/after | Complete object state as JSON before and after. | ✓ |
| Action + changed fields | Action plus which fields changed. | |

**User's choice:** Full before/after

### Table Structure
| Option | Description | Selected |
|--------|-------------|----------|
| Single table | One audit_log table with entity_type, entity_id, action, details. | ✓ |
| Per-entity tables | Separate audit tables per entity type. | |
| You decide | Let Claude pick | |

**User's choice:** Single table

---

## API Conventions

### URL Structure
| Option | Description | Selected |
|--------|-------------|----------|
| Versioned prefix | /api/v1/workflows, /api/v1/documents. | ✓ |
| No version prefix | /workflows, /documents. Version via headers. | |
| You decide | Let Claude pick | |

**User's choice:** Versioned prefix

### Response Format
| Option | Description | Selected |
|--------|-------------|----------|
| Envelope | {data, meta, errors} wrapper. Consistent, room for pagination. | ✓ |
| Direct | Return object directly. HTTP status for errors. | |
| You decide | Let Claude pick | |

**User's choice:** Envelope

### Pagination
| Option | Description | Selected |
|--------|-------------|----------|
| Offset-based | ?page=2&page_size=20. Simple, standard. | ✓ |
| Cursor-based | ?cursor=abc123&limit=20. Better for real-time data. | |
| You decide | Let Claude pick | |

**User's choice:** Offset-based

---

## Claude's Discretion

- JWT expiry duration and refresh strategy
- Exact Docker Compose service configuration and networking
- FastAPI project structure (routers, services, models organization)
- Redis usage pattern (caching, Celery broker, or both)
- Exact base model implementation details

## Deferred Ideas

None — discussion stayed within phase scope
