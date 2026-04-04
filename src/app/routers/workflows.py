"""Workflow lifecycle endpoints."""
import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin, get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.workflow import (
    CompleteWorkItemRequest,
    ProcessVariableResponse,
    UpdateVariableRequest,
    WorkflowActionResponse,
    WorkflowAdminListResponse,
    WorkflowDetailResponse,
    WorkflowInstanceResponse,
    WorkflowStartRequest,
    WorkItemResponse,
)
from app.services import engine_service, workflow_mgmt_service

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


# ---------------------------------------------------------------------------
# Admin workflow management (placed before /{workflow_id} to avoid path clash)
# ---------------------------------------------------------------------------


@router.get(
    "/admin/list",
    response_model=EnvelopeResponse[list[WorkflowAdminListResponse]],
)
async def list_workflows_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    state: str | None = Query(None),
    template_id: uuid.UUID | None = Query(None),
    created_by: uuid.UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Admin filtered workflow listing with enriched metadata."""
    workflows, total_count = await workflow_mgmt_service.list_workflows_filtered(
        db, skip, limit, state, template_id, created_by, date_from, date_to
    )
    return EnvelopeResponse(
        data=[WorkflowAdminListResponse(**w) for w in workflows],
        meta=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_count=total_count,
            total_pages=math.ceil(total_count / limit) if limit > 0 else 0,
        ),
    )


@router.post(
    "/{workflow_id}/halt",
    response_model=EnvelopeResponse[WorkflowActionResponse],
)
async def halt_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Halt a running workflow. Admin only."""
    try:
        workflow = await workflow_mgmt_service.halt_workflow(
            db, workflow_id, str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return EnvelopeResponse(
        data=WorkflowActionResponse(
            id=workflow.id, state=workflow.state, message="Workflow halted"
        )
    )


@router.post(
    "/{workflow_id}/resume",
    response_model=EnvelopeResponse[WorkflowActionResponse],
)
async def resume_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Resume a halted workflow. Admin only."""
    try:
        workflow = await workflow_mgmt_service.resume_workflow(
            db, workflow_id, str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return EnvelopeResponse(
        data=WorkflowActionResponse(
            id=workflow.id, state=workflow.state, message="Workflow resumed"
        )
    )


@router.post(
    "/{workflow_id}/abort",
    response_model=EnvelopeResponse[WorkflowActionResponse],
)
async def abort_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Abort a running or halted workflow. Admin only."""
    try:
        workflow = await workflow_mgmt_service.abort_workflow(
            db, workflow_id, str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return EnvelopeResponse(
        data=WorkflowActionResponse(
            id=workflow.id, state=workflow.state, message="Workflow aborted"
        )
    )


@router.post(
    "/{workflow_id}/restart",
    response_model=EnvelopeResponse[WorkflowActionResponse],
)
async def restart_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Restart a failed workflow back to dormant. Admin only."""
    try:
        workflow = await workflow_mgmt_service.restart_workflow(
            db, workflow_id, str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return EnvelopeResponse(
        data=WorkflowActionResponse(
            id=workflow.id, state=workflow.state, message="Workflow reset to dormant"
        )
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
            selected_path=request.selected_path,
            next_performer_id=request.next_performer_id,
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
