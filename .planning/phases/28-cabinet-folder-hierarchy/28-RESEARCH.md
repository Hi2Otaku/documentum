# Phase 28: Cabinet/Folder Hierarchy - Research

**Researched:** 2026-04-13
**Domain:** Hierarchical data modeling (adjacency list), recursive CTEs, tree UI
**Confidence:** HIGH

## Summary

Phase 28 implements a cabinet/folder hierarchy for organizing documents. The data model uses a single `folders` table with adjacency list pattern (self-referential `parent_id` FK), a `document_folders` many-to-many junction table for multi-filing, and recursive CTEs for path resolution. This maps closely to the existing `DocumentType` model's self-referential pattern but with deeper nesting (unlimited depth vs 1-level) and additional complexity around circular reference prevention, recursive soft-delete, and tree serialization.

The backend approach is well-supported by SQLAlchemy 2.0's `with_recursive()` CTE API and the project's existing async patterns. The frontend requires a custom recursive tree component (no third-party tree library needed) with expand/collapse state managed via Zustand or local React state, plus TanStack Query for data fetching.

**Primary recommendation:** Follow the existing `DocumentType` model/service/router/schema/API-client pattern exactly, adding recursive CTE helpers for path and tree operations. Build FolderTree as a recursive React component with local expand state, not a third-party widget.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Single `folders` table with `parent_id IS NULL` = cabinet (adjacency list), `is_cabinet` boolean flag
- Many-to-many `document_folders` junction table (composite PK: document_id, folder_id) for multi-filing
- Recursive CTE for path resolution (no ltree extension)
- REST API: `/api/v1/folders/` CRUD + `/tree` + sub-resources for filing
- Frontend: FolderTree component + admin page + filing UI in DocumentDetailPanel
- Full browse experience deferred to Phase 32
- Shallow copy: re-links documents, does not duplicate files
- Soft delete: recursive, unfiles documents but does not delete them
- Unlimited nesting depth
- Full tree returned by `/tree` endpoint (no lazy loading in Phase 28)

### Claude's Discretion
- Internal implementation details of CTE queries, service method signatures, Pydantic schema structure
- Frontend tree component expand/collapse state management approach
- TanStack Query cache key structure and invalidation strategy

### Deferred Ideas (OUT OF SCOPE)
- Full `/browse` route with folder tree sidebar (Phase 32)
- Document grid view inside a folder (Phase 32)
- Inline document detail panel from browse view (Phase 32)
- Lazy-load tree children on expand (Phase 32 optimization)
- Folder-level ACL propagation (FOLD-05, Phase 29)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOLD-01 | User can create a cabinet (top-level container) and nested folders within any folder | Folder model with parent_id FK, service methods for create cabinet + create subfolder, POST endpoints |
| FOLD-02 | User can browse the full cabinet/folder tree via a hierarchical navigator | GET /tree endpoint with recursive CTE to build nested JSON, FolderTree React component with expand/collapse |
| FOLD-03 | User can file a document into one or more folders and remove from folder without deleting document | document_folders junction table, POST/DELETE filing endpoints, folder_ids in DocumentResponse |
| FOLD-04 | User can move, rename, and copy folders; breadcrumb navigation shows full path | PUT endpoint for move/rename with circular reference check, POST /copy for shallow copy, recursive CTE for breadcrumb path |
</phase_requirements>

## Standard Stack

All libraries are already in the project. No new dependencies needed.

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.x | ORM + recursive CTE via `with_recursive()` | Already in project; CTE API is mature |
| FastAPI | 0.135.x | REST endpoints | Already in project |
| Pydantic | 2.12.x | Request/response schemas | Already in project |
| Alembic | 1.18.x | Migration for new tables | Already in project |
| React | 19.x | Frontend UI | Already in project |
| TanStack Query | 5.x | Server state management | Already in project |
| Zustand | 5.x | Client state (optional for tree expand state) | Already in project |

### No New Dependencies
The folder tree UI is best built as a custom recursive React component using existing shadcn/ui primitives (Button, Collapsible if added, or raw disclosure pattern). Third-party tree libraries (react-arborist, rc-tree) add bundle size and styling complexity for what is a straightforward recursive render.

**shadcn/ui Collapsible:** If not already installed, add via `npx shadcn@latest add collapsible` -- provides accessible expand/collapse with Radix primitives. Alternatively, use a simple `useState` boolean per node.

## Architecture Patterns

### Recommended Project Structure
```
src/app/
  models/
    folder.py              # Folder model + DocumentFolder association table
  schemas/
    folder.py              # Pydantic schemas for folder CRUD + tree + filing
  services/
    folder_service.py      # CTE queries, tree building, circular ref check, copy
  routers/
    folders.py             # REST endpoints

frontend/src/
  api/
    folders.ts             # API client
  components/
    folders/
      FolderTree.tsx        # Recursive tree navigator
      FolderTreeNode.tsx    # Single tree node (expand/collapse, context menu)
      FolderBreadcrumb.tsx  # Path breadcrumb
      CreateFolderDialog.tsx
      FolderPicker.tsx      # Used in DocumentDetailPanel for filing
  pages/
    FoldersPage.tsx         # Admin page
```

### Pattern 1: Folder Model (Adjacency List)

**What:** Self-referential FK for parent/children, mirroring DocumentType pattern but with unlimited depth.

```python
# src/app/models/folder.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel


# Junction table for document multi-filing
document_folders = Table(
    "document_folders",
    Base.metadata,
    Column("document_id", Uuid(), ForeignKey("documents.id"), primary_key=True),
    Column("folder_id", Uuid(), ForeignKey("folders.id"), primary_key=True),
    Column("filed_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False),
    Column("filed_by", String(255), nullable=True),
)


class Folder(BaseModel):
    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("folders.id"), nullable=True
    )
    is_cabinet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    parent: Mapped["Folder | None"] = relationship(
        "Folder",
        remote_side="Folder.id",
        back_populates="children",
        lazy="selectin",
        foreign_keys=[parent_id],
    )
    children: Mapped[list["Folder"]] = relationship(
        "Folder",
        back_populates="parent",
        foreign_keys=[parent_id],
        viewonly=True,
    )

    # Many-to-many with documents
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        secondary=document_folders,
        viewonly=True,
    )
```

**Key difference from DocumentType:** `lazy="selectin"` on parent is fine for single-folder lookups, but the tree endpoint should NOT use eager loading of children recursively (it would cause N+1). Use a flat query + Python assembly instead.

### Pattern 2: Recursive CTE for Path Resolution

**What:** SQLAlchemy 2.0's `select().cte(recursive=True)` for computing ancestor path.

```python
# In folder_service.py
from sqlalchemy import select, union_all, literal_column

async def get_folder_path(db: AsyncSession, folder_id: uuid.UUID) -> list[dict]:
    """Return ordered list of ancestors from root cabinet to this folder."""
    from app.models.folder import Folder

    # Anchor: the target folder
    anchor = (
        select(
            Folder.id,
            Folder.name,
            Folder.parent_id,
            literal_column("0").label("depth"),
        )
        .where(Folder.id == folder_id, Folder.is_deleted == False)
        .cte(name="ancestors", recursive=True)
    )

    # Recursive: join parent
    parent_alias = Folder.__table__.alias("p")
    recursive = select(
        parent_alias.c.id,
        parent_alias.c.name,
        parent_alias.c.parent_id,
        (anchor.c.depth + 1).label("depth"),
    ).join(anchor, parent_alias.c.id == anchor.c.parent_id)

    ancestors_cte = anchor.union_all(recursive)

    result = await db.execute(
        select(ancestors_cte.c.id, ancestors_cte.c.name)
        .order_by(ancestors_cte.c.depth.desc())
    )
    return [{"id": str(row.id), "name": row.name} for row in result.all()]
```

### Pattern 3: Full Tree Loading (Flat Query + Python Assembly)

**What:** Load all non-deleted folders in one query, build tree in Python. Avoids recursive eager loading.

```python
async def get_folder_tree(db: AsyncSession) -> list[dict]:
    """Return full folder tree as nested JSON."""
    from app.models.folder import Folder
    from sqlalchemy import func

    # Single query: all non-deleted folders with document count
    stmt = (
        select(Folder)
        .where(Folder.is_deleted == False)
        .order_by(Folder.name)
    )
    result = await db.execute(stmt)
    folders = result.scalars().all()

    # Build lookup and tree
    by_id = {f.id: {
        "id": str(f.id),
        "name": f.name,
        "is_cabinet": f.is_cabinet,
        "parent_id": str(f.parent_id) if f.parent_id else None,
        "children": [],
    } for f in folders}

    roots = []
    for f in folders:
        node = by_id[f.id]
        if f.parent_id and f.parent_id in by_id:
            by_id[f.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots
```

### Pattern 4: Circular Reference Prevention (Move Validation)

**What:** Before allowing a folder move, verify the target parent is not a descendant of the folder being moved.

```python
async def _is_descendant(db: AsyncSession, folder_id: uuid.UUID, candidate_id: uuid.UUID) -> bool:
    """Check if candidate_id is a descendant of folder_id using recursive CTE."""
    from app.models.folder import Folder

    anchor = (
        select(Folder.id)
        .where(Folder.parent_id == folder_id, Folder.is_deleted == False)
        .cte(name="descendants", recursive=True)
    )
    recursive = (
        select(Folder.id)
        .join(anchor, Folder.parent_id == anchor.c.id)
        .where(Folder.is_deleted == False)
    )
    descendants_cte = anchor.union_all(recursive)

    result = await db.execute(
        select(descendants_cte.c.id).where(descendants_cte.c.id == candidate_id)
    )
    return result.scalar_one_or_none() is not None
```

Then in the move/update service method:
```python
if new_parent_id == folder_id:
    raise HTTPException(400, "Cannot move folder into itself")
if await _is_descendant(db, folder_id, new_parent_id):
    raise HTTPException(400, "Cannot move folder into its own subtree")
```

### Pattern 5: Recursive Soft Delete

```python
async def delete_folder(db: AsyncSession, folder_id: uuid.UUID) -> None:
    """Soft-delete folder and all descendants. Remove document filings."""
    from app.models.folder import Folder, document_folders

    # Get all descendant IDs via CTE
    anchor = (
        select(Folder.id)
        .where(Folder.id == folder_id, Folder.is_deleted == False)
        .cte(name="subtree", recursive=True)
    )
    recursive = (
        select(Folder.id)
        .join(anchor, Folder.parent_id == anchor.c.id)
        .where(Folder.is_deleted == False)
    )
    subtree_cte = anchor.union_all(recursive)

    # Collect IDs
    result = await db.execute(select(subtree_cte.c.id))
    ids_to_delete = [row[0] for row in result.all()]

    if not ids_to_delete:
        raise HTTPException(404, "Folder not found")

    # Soft-delete all folders in subtree
    await db.execute(
        Folder.__table__.update()
        .where(Folder.id.in_(ids_to_delete))
        .values(is_deleted=True)
    )

    # Remove document filings for deleted folders
    await db.execute(
        document_folders.delete().where(
            document_folders.c.folder_id.in_(ids_to_delete)
        )
    )

    await db.flush()
```

### Pattern 6: Frontend Recursive Tree Component

```tsx
// FolderTreeNode.tsx
interface FolderTreeNodeProps {
  node: FolderTreeNode;
  depth: number;
  onSelect: (id: string) => void;
  selectedId: string | null;
}

function FolderTreeNode({ node, depth, onSelect, selectedId }: FolderTreeNodeProps) {
  const [expanded, setExpanded] = useState(node.is_cabinet); // cabinets start expanded

  return (
    <div>
      <button
        className={cn(
          "flex items-center gap-1 w-full text-left px-2 py-1 text-sm rounded hover:bg-accent",
          selectedId === node.id && "bg-accent",
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => onSelect(node.id)}
      >
        {node.children.length > 0 && (
          <ChevronRight
            className={cn("h-4 w-4 shrink-0 transition-transform", expanded && "rotate-90")}
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          />
        )}
        {node.is_cabinet ? <Archive className="h-4 w-4" /> : <FolderIcon className="h-4 w-4" />}
        <span className="truncate">{node.name}</span>
      </button>
      {expanded && node.children.map(child => (
        <FolderTreeNode key={child.id} node={child} depth={depth + 1} onSelect={onSelect} selectedId={selectedId} />
      ))}
    </div>
  );
}
```

### Pattern 7: TanStack Query Cache Strategy

```tsx
// Query keys
const folderKeys = {
  all: ["folders"] as const,
  tree: () => [...folderKeys.all, "tree"] as const,
  detail: (id: string) => [...folderKeys.all, id] as const,
  documents: (id: string) => [...folderKeys.all, id, "documents"] as const,
};

// Invalidation after mutation (create, move, rename, delete, copy)
// Always invalidate the tree + any affected folder detail
const createMutation = useMutation({
  mutationFn: createFolder,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: folderKeys.tree() });
  },
});
```

**Key insight:** Since the tree endpoint returns the full tree, a single `invalidateQueries({ queryKey: folderKeys.tree() })` after any folder mutation is sufficient. No need for granular cache updates.

### Anti-Patterns to Avoid
- **Recursive eager loading:** Do NOT use `selectinload(Folder.children)` recursively for the tree endpoint. It causes N+1 queries per depth level. Load flat, assemble in Python.
- **Storing computed path:** Do NOT add a `path` column. It desynchronizes on rename/move. Compute via CTE on demand.
- **Client-side tree building from flat list:** The backend should return the nested tree structure. Client should not have to build hierarchy from a flat array.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Recursive CTE | Manual multi-query ancestor walk | SQLAlchemy `select().cte(recursive=True)` | Single query, database-optimized |
| Tree serialization | Recursive ORM eager loading | Flat query + Python dict assembly | O(n) vs O(n * depth) queries |
| Expand/collapse UI | Custom disclosure primitive | React `useState` per node or shadcn Collapsible | Accessibility built-in |
| Breadcrumb path | String manipulation on stored path | CTE-computed ancestor list | Always consistent with actual hierarchy |

## Common Pitfalls

### Pitfall 1: MissingGreenlet on Relationship Access
**What goes wrong:** Accessing `folder.parent` or `folder.children` outside an async context raises `MissingGreenlet`.
**Why it happens:** SQLAlchemy async requires explicit eager loading.
**How to avoid:** Use `selectinload(Folder.parent)` in queries that need parent data. For tree endpoint, avoid relationship traversal entirely -- use flat query.
**Warning signs:** `MissingGreenlet: greenlet_spawn has not been called` error.

### Pitfall 2: Circular Reference on Move
**What goes wrong:** Moving folder A into its own child B creates an infinite loop in CTE traversal.
**Why it happens:** No validation that target parent is not a descendant.
**How to avoid:** Run descendant check CTE before updating `parent_id`. Also check `parent_id != folder_id` (self-reference).
**Warning signs:** Infinite loop or stack overflow in path resolution.

### Pitfall 3: SQLite Recursive CTE Differences in Tests
**What goes wrong:** Tests use aiosqlite (in-memory SQLite). Recursive CTEs work in SQLite but syntax edge cases differ from PostgreSQL.
**Why it happens:** SQLite supports `WITH RECURSIVE` but has quirks with aliased columns.
**How to avoid:** Keep CTE queries simple. Test with actual CTE queries in test suite. Avoid PostgreSQL-specific functions in CTEs.
**Warning signs:** Tests pass but production fails, or vice versa.

### Pitfall 4: Orphaned document_folders Rows on Folder Delete
**What goes wrong:** Soft-deleting a folder without cleaning up `document_folders` leaves stale filing records.
**Why it happens:** Junction table has no `is_deleted` flag.
**How to avoid:** Delete `document_folders` rows when soft-deleting folders. The delete service method must handle this explicitly.
**Warning signs:** Documents appear filed in deleted folders.

### Pitfall 5: N+1 Document Count Queries
**What goes wrong:** Computing `document_count` per folder in the tree requires N queries.
**Why it happens:** Each tree node needs a COUNT from junction table.
**How to avoid:** Use a single aggregated query with GROUP BY to get all counts, then merge into tree nodes in Python.
**Warning signs:** Slow tree endpoint response times.

### Pitfall 6: Frontend Key Prop on Recursive Components
**What goes wrong:** React reconciliation breaks when tree structure changes if keys are not stable.
**Why it happens:** Using array index as key in recursive render.
**How to avoid:** Always use `folder.id` as key.
**Warning signs:** Stale expand/collapse state after move/rename.

## Code Examples

### Pydantic Schemas

```python
# src/app/schemas/folder.py
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_cabinet: bool = False  # True for top-level cabinets


class FolderUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None  # Move operation


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    is_cabinet: bool
    document_count: int = 0
    path: list[dict]  # [{id, name}, ...] from root to this folder
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FolderTreeNode(BaseModel):
    id: uuid.UUID
    name: str
    is_cabinet: bool
    document_count: int = 0
    children: list["FolderTreeNode"] = []


class FolderCopyRequest(BaseModel):
    destination_parent_id: uuid.UUID | None = None  # None = same parent


class FileDocumentRequest(BaseModel):
    document_id: uuid.UUID
```

### Migration Pattern

```python
# alembic/versions/phase28_001_folders.py
def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("is_cabinet", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"], name="fk_folders_parent_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Index for tree queries (children lookup)
    op.create_index("ix_folders_parent_id", "folders", ["parent_id"])

    op.create_table(
        "document_folders",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filed_by", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_document_folders_document_id"),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], name="fk_document_folders_folder_id"),
        sa.PrimaryKeyConstraint("document_id", "folder_id"),
    )
```

### Router Pattern (following document_types.py)

```python
# Key endpoints following existing project conventions
router = APIRouter(prefix="/folders", tags=["folders"])

@router.get("/tree", response_model=EnvelopeResponse[list[FolderTreeNode]])
async def get_folder_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[list[FolderTreeNode]]:
    tree = await folder_service.get_folder_tree(db)
    return EnvelopeResponse(data=tree)

@router.post("/{folder_id}/documents", response_model=EnvelopeResponse)
async def file_document(
    folder_id: uuid.UUID,
    body: FileDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse:
    await folder_service.file_document(db, folder_id, body.document_id, str(current_user.id))
    return EnvelopeResponse(data=None, meta={"message": "Document filed"})
```

### Frontend API Client Pattern (following documentTypes.ts)

```typescript
// frontend/src/api/folders.ts
export interface FolderTreeNode {
  id: string;
  name: string;
  is_cabinet: boolean;
  document_count: number;
  children: FolderTreeNode[];
}

export interface FolderResponse {
  id: string;
  name: string;
  description: string | null;
  parent_id: string | null;
  is_cabinet: boolean;
  document_count: number;
  path: Array<{ id: string; name: string }>;
  created_at: string;
  updated_at: string;
}

export async function fetchFolderTree(): Promise<FolderTreeNode[]> {
  const res = await apiFetch<{ data: FolderTreeNode[] }>("/api/v1/folders/tree");
  return res.data;
}

export async function fileDocument(folderId: string, documentId: string): Promise<void> {
  await apiMutate("/api/v1/folders/" + folderId + "/documents", "POST", { document_id: documentId });
}
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `tests/conftest.py` (session-scoped fixtures, in-memory SQLite) |
| Quick run command | `python -m pytest tests/test_folders.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOLD-01 | Create cabinet (POST, parent_id=null, is_cabinet=true) | unit | `python -m pytest tests/test_folders.py::test_create_cabinet -x` | Wave 0 |
| FOLD-01 | Create subfolder (POST /{id}/children) | unit | `python -m pytest tests/test_folders.py::test_create_subfolder -x` | Wave 0 |
| FOLD-01 | Non-admin can create subfolder | unit | `python -m pytest tests/test_folders.py::test_create_subfolder_regular_user -x` | Wave 0 |
| FOLD-02 | GET /tree returns nested structure | unit | `python -m pytest tests/test_folders.py::test_get_folder_tree -x` | Wave 0 |
| FOLD-02 | Tree excludes soft-deleted folders | unit | `python -m pytest tests/test_folders.py::test_tree_excludes_deleted -x` | Wave 0 |
| FOLD-03 | File document into folder | unit | `python -m pytest tests/test_folders.py::test_file_document -x` | Wave 0 |
| FOLD-03 | File document into multiple folders | unit | `python -m pytest tests/test_folders.py::test_multi_file_document -x` | Wave 0 |
| FOLD-03 | Unfile document (DELETE) does not delete document | unit | `python -m pytest tests/test_folders.py::test_unfile_document -x` | Wave 0 |
| FOLD-03 | Document folder_ids in DocumentResponse | unit | `python -m pytest tests/test_folders.py::test_document_response_includes_folder_ids -x` | Wave 0 |
| FOLD-04 | Move folder (PUT with new parent_id) | unit | `python -m pytest tests/test_folders.py::test_move_folder -x` | Wave 0 |
| FOLD-04 | Move rejects circular reference | unit | `python -m pytest tests/test_folders.py::test_move_circular_rejected -x` | Wave 0 |
| FOLD-04 | Move rejects self-reference | unit | `python -m pytest tests/test_folders.py::test_move_self_rejected -x` | Wave 0 |
| FOLD-04 | Rename folder | unit | `python -m pytest tests/test_folders.py::test_rename_folder -x` | Wave 0 |
| FOLD-04 | Copy folder (shallow) | unit | `python -m pytest tests/test_folders.py::test_copy_folder -x` | Wave 0 |
| FOLD-04 | GET /{id} includes breadcrumb path | unit | `python -m pytest tests/test_folders.py::test_folder_detail_has_path -x` | Wave 0 |
| FOLD-04 | Delete folder cascades to subtree | unit | `python -m pytest tests/test_folders.py::test_delete_cascades_subtree -x` | Wave 0 |
| FOLD-04 | Delete unfiles documents but preserves them | unit | `python -m pytest tests/test_folders.py::test_delete_unfiles_documents -x` | Wave 0 |
| FOLD-03 | GET /documents/?folder_id= filters by folder | unit | `python -m pytest tests/test_folders.py::test_list_documents_by_folder -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_folders.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_folders.py` -- covers FOLD-01 through FOLD-04 (all tests above)
- No framework changes needed -- existing conftest.py handles in-memory SQLite and async test setup

## Risk Areas

1. **Recursive CTE compatibility between SQLite (tests) and PostgreSQL (prod):** The recursive CTE syntax used must work on both. SQLAlchemy's CTE API abstracts most differences, but edge cases with type casting or column aliases may surface. Mitigation: keep CTEs simple, test thoroughly.

2. **Performance of full tree endpoint at scale:** Loading all folders in one query is fine for hundreds of folders but may degrade at thousands. Acceptable for Phase 28 per CONTEXT.md (lazy loading deferred to Phase 32).

3. **Shallow copy with deep subtrees:** Copying a large folder subtree requires loading all descendants, creating new folder records, and re-linking all document_folders rows. This could be slow for very large subtrees. Mitigation: wrap in a single transaction, use bulk insert.

4. **DocumentResponse schema change (adding folder_ids):** Existing document endpoints must return `folder_ids`. This requires a LEFT JOIN or subquery on every document fetch. Mitigation: use a subquery to avoid N+1, or compute lazily only when needed.

5. **Junction table cleanup on document soft-delete:** When a document is soft-deleted (existing behavior), should its `document_folders` rows be removed? Decision: No -- if the document is restored, it should still be in its folders. But `folder_ids` in DocumentResponse should only show for non-deleted documents.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/app/models/document_type.py` -- self-referential FK pattern
- Existing codebase: `src/app/services/document_type_service.py` -- service layer pattern
- Existing codebase: `src/app/routers/document_types.py` -- router pattern
- Existing codebase: `tests/test_document_types.py` -- test pattern
- Existing codebase: `frontend/src/api/documentTypes.ts` -- API client pattern
- SQLAlchemy 2.0 documentation on recursive CTEs (training data, verified against codebase patterns)

### Secondary (MEDIUM confidence)
- SQLAlchemy async CTE syntax -- based on SQLAlchemy 2.0 docs and confirmed working with project's async engine setup
- React recursive rendering pattern -- standard React pattern, no library-specific concerns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns exist in codebase
- Architecture: HIGH -- adjacency list + CTE is well-documented, project precedent exists
- Pitfalls: HIGH -- common issues are well-known for this pattern
- Frontend tree: MEDIUM -- recursive component is straightforward but expand state management choices need validation during implementation

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable patterns, no fast-moving dependencies)
