"""CMIS-QL query parser and executor.

Implements a practical subset of the CMIS Query Language (CMIS-QL):
  SELECT <fields> FROM <type> [WHERE <conditions>] [ORDER BY <sort>]

Supports: =, !=, <, >, <=, >=, LIKE, IN operators.
Conditions joined by AND (OR supported in parser but AND is the common case).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.folder import Folder
from app.services.cmis_service import to_cmis_document, to_cmis_folder


# ── Property mapping: CMIS property -> (Document column, Folder column) ─────

# Maps CMIS property names to SQLAlchemy model attribute names
PROPERTY_MAP_DOCUMENT: dict[str, str] = {
    "cmis:objectId": "id",
    "cmis:name": "title",
    "cmis:baseTypeId": None,  # virtual, always "cmis:document"
    "cmis:objectTypeId": None,
    "cmis:createdBy": "created_by",
    "cmis:creationDate": "created_at",
    "cmis:lastModificationDate": "updated_at",
    "cmis:contentStreamFileName": "filename",
    "cmis:contentStreamMimeType": "content_type",
    "cmis:isVersionSeriesCheckedOut": "locked_by",  # special handling
    "cmis:versionLabel": None,  # computed
}

PROPERTY_MAP_FOLDER: dict[str, str] = {
    "cmis:objectId": "id",
    "cmis:name": "name",
    "cmis:baseTypeId": None,
    "cmis:objectTypeId": None,
    "cmis:createdBy": "created_by",
    "cmis:creationDate": "created_at",
    "cmis:lastModificationDate": "updated_at",
    "cmis:parentId": "parent_id",
}


# ── Parsed query data structures ────────────────────────────────────────────


@dataclass
class WhereClause:
    property: str
    operator: str  # =, !=, <, >, <=, >=, LIKE, IN
    value: str | list[str]
    conjunction: str = "AND"  # AND or OR (preceding conjunction)


@dataclass
class OrderSpec:
    property: str
    direction: str = "ASC"  # ASC or DESC


@dataclass
class ParsedQuery:
    select_fields: list[str] = field(default_factory=list)
    from_type: str = ""
    where_clauses: list[WhereClause] = field(default_factory=list)
    order_by: list[OrderSpec] = field(default_factory=list)


# ── Parser ──────────────────────────────────────────────────────────────────


def parse_cmis_query(query: str) -> ParsedQuery:
    """Parse a CMIS-QL query string into a ParsedQuery structure.

    Raises ValueError if the query cannot be parsed.
    """
    q = query.strip()

    # Must start with SELECT
    if not re.match(r"(?i)^SELECT\s", q):
        raise ValueError(f"Invalid CMIS-QL query: must start with SELECT. Got: {q[:50]}")

    result = ParsedQuery()

    # Extract SELECT fields
    select_match = re.match(
        r"(?i)^SELECT\s+(.+?)\s+FROM\s+",
        q,
    )
    if not select_match:
        raise ValueError(f"Invalid CMIS-QL query: could not parse SELECT ... FROM. Got: {q[:80]}")

    fields_str = select_match.group(1).strip()
    if fields_str == "*":
        result.select_fields = ["*"]
    else:
        result.select_fields = [f.strip() for f in fields_str.split(",")]

    # Extract FROM type
    from_match = re.search(r"(?i)\bFROM\s+(cmis:\w+)", q)
    if not from_match:
        raise ValueError(f"Invalid CMIS-QL query: could not parse FROM clause. Got: {q[:80]}")
    result.from_type = from_match.group(1)

    if result.from_type not in ("cmis:document", "cmis:folder"):
        raise ValueError(f"Invalid CMIS-QL query: unsupported type '{result.from_type}'")

    # Extract WHERE clause (everything between WHERE and ORDER BY, or end of string)
    where_match = re.search(
        r"(?i)\bWHERE\s+(.+?)(?:\s+ORDER\s+BY\s+|$)",
        q,
    )
    if where_match:
        where_str = where_match.group(1).strip()
        result.where_clauses = _parse_where_clauses(where_str)

    # Extract ORDER BY clause
    order_match = re.search(r"(?i)\bORDER\s+BY\s+(.+)$", q)
    if order_match:
        order_str = order_match.group(1).strip()
        result.order_by = _parse_order_by(order_str)

    return result


def _parse_where_clauses(where_str: str) -> list[WhereClause]:
    """Parse WHERE clause conditions."""
    clauses: list[WhereClause] = []

    # Split by AND/OR (keep the conjunction)
    # Use regex to split while preserving string literals
    parts = re.split(r"\s+(?:AND|OR)\s+", where_str, flags=re.IGNORECASE)
    conjunctions = re.findall(r"\s+(AND|OR)\s+", where_str, flags=re.IGNORECASE)

    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue

        conjunction = conjunctions[i - 1].upper() if i > 0 and i - 1 < len(conjunctions) else "AND"

        # Try IN operator: property IN ('val1', 'val2', ...)
        in_match = re.match(
            r"([\w:]+)\s+IN\s*\((.+?)\)",
            part,
            re.IGNORECASE,
        )
        if in_match:
            prop = in_match.group(1)
            vals_str = in_match.group(2)
            values = [v.strip().strip("'\"") for v in vals_str.split(",")]
            clauses.append(WhereClause(
                property=prop,
                operator="IN",
                value=values,
                conjunction=conjunction,
            ))
            continue

        # Try LIKE operator: property LIKE 'pattern'
        like_match = re.match(
            r"([\w:]+)\s+LIKE\s+'([^']*)'",
            part,
            re.IGNORECASE,
        )
        if like_match:
            clauses.append(WhereClause(
                property=like_match.group(1),
                operator="LIKE",
                value=like_match.group(2),
                conjunction=conjunction,
            ))
            continue

        # Try comparison operators: property op 'value' or property op number
        comp_match = re.match(
            r"([\w:]+)\s*(!=|<=|>=|<|>|=)\s*'([^']*)'",
            part,
        )
        if comp_match:
            clauses.append(WhereClause(
                property=comp_match.group(1),
                operator=comp_match.group(2),
                value=comp_match.group(3),
                conjunction=conjunction,
            ))
            continue

        # Try numeric comparison
        num_match = re.match(
            r"([\w:]+)\s*(!=|<=|>=|<|>|=)\s*(\d+(?:\.\d+)?)",
            part,
        )
        if num_match:
            clauses.append(WhereClause(
                property=num_match.group(1),
                operator=num_match.group(2),
                value=num_match.group(3),
                conjunction=conjunction,
            ))
            continue

        raise ValueError(f"Invalid CMIS-QL WHERE clause: could not parse '{part}'")

    return clauses


def _parse_order_by(order_str: str) -> list[OrderSpec]:
    """Parse ORDER BY clause."""
    specs: list[OrderSpec] = []
    for part in order_str.split(","):
        part = part.strip()
        tokens = part.split()
        if len(tokens) == 0:
            continue
        prop = tokens[0]
        direction = tokens[1].upper() if len(tokens) > 1 else "ASC"
        if direction not in ("ASC", "DESC"):
            direction = "ASC"
        specs.append(OrderSpec(property=prop, direction=direction))
    return specs


# ── Executor ────────────────────────────────────────────────────────────────


async def execute_cmis_query(
    db: AsyncSession,
    query: str,
    user_id: str,
    is_superuser: bool,
    max_items: int = 100,
    skip_count: int = 0,
) -> dict[str, Any]:
    """Execute a CMIS-QL query and return results in CMIS format.

    Returns:
        {"objects": [...], "hasMoreItems": bool, "numItems": int}

    Raises:
        ValueError: If the query cannot be parsed.
    """
    parsed = parse_cmis_query(query)

    is_folder_query = parsed.from_type == "cmis:folder"
    model = Folder if is_folder_query else Document
    prop_map = PROPERTY_MAP_FOLDER if is_folder_query else PROPERTY_MAP_DOCUMENT

    # Build base query
    stmt = select(model).where(model.is_deleted == False)  # noqa: E712

    # Apply WHERE clauses
    for clause in parsed.where_clauses:
        col_name = prop_map.get(clause.property)
        if col_name is None:
            # Skip virtual/computed properties in WHERE
            continue

        column = getattr(model, col_name, None)
        if column is None:
            continue

        if clause.operator == "=":
            stmt = stmt.where(column == clause.value)
        elif clause.operator == "!=":
            stmt = stmt.where(column != clause.value)
        elif clause.operator == "<":
            stmt = stmt.where(column < clause.value)
        elif clause.operator == ">":
            stmt = stmt.where(column > clause.value)
        elif clause.operator == "<=":
            stmt = stmt.where(column <= clause.value)
        elif clause.operator == ">=":
            stmt = stmt.where(column >= clause.value)
        elif clause.operator == "LIKE":
            # CMIS uses SQL-style % wildcards; use ilike for case-insensitive
            stmt = stmt.where(column.ilike(clause.value))
        elif clause.operator == "IN":
            if isinstance(clause.value, list):
                stmt = stmt.where(column.in_(clause.value))

    # Apply ORDER BY
    for spec in parsed.order_by:
        col_name = prop_map.get(spec.property)
        if col_name is None:
            continue
        column = getattr(model, col_name, None)
        if column is None:
            continue
        if spec.direction == "DESC":
            stmt = stmt.order_by(column.desc())
        else:
            stmt = stmt.order_by(column.asc())

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Apply pagination
    stmt = stmt.offset(skip_count).limit(max_items)

    # Execute
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    # Convert to CMIS format
    objects = []
    for row in rows:
        if is_folder_query:
            props = to_cmis_folder(row)
        else:
            props = to_cmis_document(row)

        # Filter to requested fields if not SELECT *
        if parsed.select_fields != ["*"]:
            props = {k: v for k, v in props.items() if k in parsed.select_fields}

        objects.append({
            "succinctProperties": props,
            "propertiesExtension": {},
        })

    has_more = (skip_count + max_items) < total

    return {
        "objects": objects,
        "hasMoreItems": has_more,
        "numItems": total,
    }
