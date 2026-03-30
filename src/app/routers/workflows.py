"""Workflow lifecycle endpoints."""
import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.workflow import (
    CompleteWorkItemRequest,
    ProcessVariableResponse,
    UpdateVariableRequest,
    WorkflowDetailResponse,
    WorkflowInstanceResponse,
    WorkflowStartRequest,
    WorkItemResponse,
)
from app.services import engine_service

router = APIRouter(prefix="/workflows", tags=["workflows"])


# ---------------------------------------------------------------------------
# Workflow lifecycle
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=EnvelopeResponse[WorkflowInstanceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def start_workflow(
    request: WorkflowStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new workflow instance from an installed template."""
    try:
        instance = await engine_service.start_workflow(
            db,
            request.template_id,
            str(current_user.id),
            request.document_ids,
            request.performer_overrides,
            request.initial_variables,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(
        data=WorkflowInstanceResponse.model_validate(instance)
    )


@router.get(
    "",
    response_model=EnvelopeResponse[list[WorkflowInstanceResponse]],
)
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List workflow instances with pagination."""
    workflows, total_count = await engine_service.list_workflows(db, skip, limit)
    return EnvelopeResponse(
        data=[WorkflowInstanceResponse.model_validate(w) for w in workflows],
        meta=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_count=total_count,
            total_pages=math.ceil(total_count / limit) if limit > 0 else 0,
        ),
    )


@router.get(
    "/{workflow_id}",
    response_model=EnvelopeResponse[WorkflowDetailResponse],
)
async def get_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a workflow instance with full detail."""
    try:
        workflow = await engine_service.get_workflow(db, workflow_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    return EnvelopeResponse(
        data=WorkflowDetailResponse.model_validate(workflow)
    )


@router.get(
    "/{workflow_id}/work-items",
    response_model=EnvelopeResponse[list[WorkItemResponse]],
)
async def list_work_items(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all work items for a workflow."""
    work_items = await engine_service.get_workflow_work_items(db, workflow_id)
    return EnvelopeResponse(
        data=[WorkItemResponse.model_validate(wi) for wi in work_items]
    )


@router.post(
    "/{workflow_id}/work-items/{work_item_id}/complete",
    response_model=EnvelopeResponse[WorkItemResponse],
)
async def complete_work_item(
    workflow_id: uuid.UUID,
    work_item_id: uuid.UUID,
    request: CompleteWorkItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete a work item and advance the workflow."""
    try:
        work_item = await engine_service.complete_work_item(
            db,
            workflow_id,
            work_item_id,
            str(current_user.id),
            request.output_variables,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(
        data=WorkItemResponse.model_validate(work_item)
    )


@router.get(
    "/{workflow_id}/variables",
    response_model=EnvelopeResponse[list[ProcessVariableResponse]],
)
async def list_variables(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all process variables for a workflow instance."""
    from sqlalchemy import select

    from app.models.workflow import ProcessVariable

    result = await db.execute(
        select(ProcessVariable).where(
            ProcessVariable.workflow_instance_id == workflow_id,
            ProcessVariable.is_deleted == False,  # noqa: E712
        )
    )
    variables = list(result.scalars().all())
    return EnvelopeResponse(
        data=[ProcessVariableResponse.model_validate(v) for v in variables]
    )


@router.put(
    "/{workflow_id}/variables/{variable_name}",
    response_model=EnvelopeResponse[ProcessVariableResponse],
)
async def update_variable(
    workflow_id: uuid.UUID,
    variable_name: str,
    request: UpdateVariableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a process variable on a workflow instance."""
    try:
        variable = await engine_service.update_variable(
            db,
            workflow_id,
            variable_name,
            request.value,
            str(current_user.id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(
        data=ProcessVariableResponse.model_validate(variable)
    )
