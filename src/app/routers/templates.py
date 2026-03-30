import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.template import (
    ActivityTemplateCreate,
    ActivityTemplateResponse,
    ActivityTemplateUpdate,
    FlowTemplateCreate,
    FlowTemplateResponse,
    FlowTemplateUpdate,
    ProcessTemplateCreate,
    ProcessTemplateDetailResponse,
    ProcessTemplateResponse,
    ProcessTemplateUpdate,
    ProcessVariableCreate,
    ProcessVariableResponse,
    ProcessVariableUpdate,
    ValidationErrorDetail,
    ValidationResult,
)
from app.services import template_service

router = APIRouter(prefix="/templates", tags=["templates"])


# ---------------------------------------------------------------------------
# ProcessTemplate endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=EnvelopeResponse[ProcessTemplateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: ProcessTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workflow template in Draft state."""
    template = await template_service.create_template(
        db, data, user_id=str(current_user.id)
    )
    return EnvelopeResponse(data=ProcessTemplateResponse.model_validate(template))


@router.get(
    "/",
    response_model=EnvelopeResponse[list[ProcessTemplateResponse]],
)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List templates with pagination."""
    templates, total_count = await template_service.list_templates(db, page, page_size)
    return EnvelopeResponse(
        data=[ProcessTemplateResponse.model_validate(t) for t in templates],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=math.ceil(total_count / page_size) if page_size > 0 else 0,
        ),
    )


@router.get(
    "/{template_id}",
    response_model=EnvelopeResponse[ProcessTemplateDetailResponse],
)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a template with full detail (activities, flows, variables)."""
    template = await template_service.get_template(db, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    # Filter out soft-deleted sub-entities and build nested response
    activities = [
        ActivityTemplateResponse.model_validate(a)
        for a in template.activity_templates
        if not a.is_deleted
    ]
    flows = [
        FlowTemplateResponse.model_validate(f)
        for f in template.flow_templates
        if not f.is_deleted
    ]
    variables = [
        ProcessVariableResponse.model_validate(v)
        for v in template.process_variables
        if not v.is_deleted
    ]

    detail = ProcessTemplateDetailResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        version=template.version,
        state=template.state,
        is_installed=template.is_installed,
        installed_at=template.installed_at,
        created_at=template.created_at,
        updated_at=template.updated_at,
        created_by=template.created_by,
        is_deleted=template.is_deleted,
        activities=activities,
        flows=flows,
        variables=variables,
    )
    return EnvelopeResponse(data=detail)


@router.put(
    "/{template_id}",
    response_model=EnvelopeResponse[ProcessTemplateResponse],
)
async def update_template(
    template_id: UUID,
    data: ProcessTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update template metadata."""
    try:
        template = await template_service.update_template(
            db, template_id, data, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ProcessTemplateResponse.model_validate(template))


@router.delete(
    "/{template_id}",
    response_model=EnvelopeResponse[ProcessTemplateResponse],
)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a template."""
    try:
        template = await template_service.delete_template(
            db, template_id, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ProcessTemplateResponse.model_validate(template))


# ---------------------------------------------------------------------------
# ActivityTemplate endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{template_id}/activities",
    response_model=EnvelopeResponse[ActivityTemplateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_activity(
    template_id: UUID,
    data: ActivityTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an activity to a template."""
    try:
        activity = await template_service.add_activity(
            db, template_id, data, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ActivityTemplateResponse.model_validate(activity))


@router.put(
    "/{template_id}/activities/{activity_id}",
    response_model=EnvelopeResponse[ActivityTemplateResponse],
)
async def update_activity(
    template_id: UUID,
    activity_id: UUID,
    data: ActivityTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an activity within a template."""
    try:
        activity = await template_service.update_activity(
            db, template_id, activity_id, data, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ActivityTemplateResponse.model_validate(activity))


@router.delete(
    "/{template_id}/activities/{activity_id}",
    response_model=EnvelopeResponse[ActivityTemplateResponse],
)
async def delete_activity(
    template_id: UUID,
    activity_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete an activity from a template."""
    try:
        activity = await template_service.delete_activity(
            db, template_id, activity_id, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ActivityTemplateResponse.model_validate(activity))


# ---------------------------------------------------------------------------
# FlowTemplate endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{template_id}/flows",
    response_model=EnvelopeResponse[FlowTemplateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_flow(
    template_id: UUID,
    data: FlowTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a flow connecting two activities."""
    try:
        flow = await template_service.add_flow(
            db, template_id, data, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=FlowTemplateResponse.model_validate(flow))


@router.put(
    "/{template_id}/flows/{flow_id}",
    response_model=EnvelopeResponse[FlowTemplateResponse],
)
async def update_flow(
    template_id: UUID,
    flow_id: UUID,
    data: FlowTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a flow within a template."""
    try:
        flow = await template_service.update_flow(
            db, template_id, flow_id, data, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=FlowTemplateResponse.model_validate(flow))


@router.delete(
    "/{template_id}/flows/{flow_id}",
    response_model=EnvelopeResponse[FlowTemplateResponse],
)
async def delete_flow(
    template_id: UUID,
    flow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a flow from a template."""
    try:
        flow = await template_service.delete_flow(
            db, template_id, flow_id, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=FlowTemplateResponse.model_validate(flow))


# ---------------------------------------------------------------------------
# ProcessVariable endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{template_id}/variables",
    response_model=EnvelopeResponse[ProcessVariableResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_variable(
    template_id: UUID,
    data: ProcessVariableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a process variable to a template."""
    try:
        variable = await template_service.add_variable(
            db, template_id, data, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ProcessVariableResponse.model_validate(variable))


@router.put(
    "/{template_id}/variables/{variable_id}",
    response_model=EnvelopeResponse[ProcessVariableResponse],
)
async def update_variable(
    template_id: UUID,
    variable_id: UUID,
    data: ProcessVariableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a process variable within a template."""
    try:
        variable = await template_service.update_variable(
            db, template_id, variable_id, data, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ProcessVariableResponse.model_validate(variable))


@router.delete(
    "/{template_id}/variables/{variable_id}",
    response_model=EnvelopeResponse[ProcessVariableResponse],
)
async def delete_variable(
    template_id: UUID,
    variable_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a process variable from a template."""
    try:
        variable = await template_service.delete_variable(
            db, template_id, variable_id, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ProcessVariableResponse.model_validate(variable))


# ---------------------------------------------------------------------------
# Validation, Installation, Versioning
# ---------------------------------------------------------------------------


@router.post(
    "/{template_id}/validate",
    response_model=EnvelopeResponse[ValidationResult],
)
async def validate_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validate a template's graph structure and configuration."""
    try:
        is_valid, errors = await template_service.validate_template(
            db, template_id, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    error_details = [
        ValidationErrorDetail(
            code=e["code"],
            message=e["message"],
            entity_type=e["entity_type"],
            entity_id=e.get("entity_id"),
        )
        for e in errors
    ]
    result = ValidationResult(valid=is_valid, errors=error_details)
    return EnvelopeResponse(data=result)


@router.post(
    "/{template_id}/install",
    response_model=EnvelopeResponse[ProcessTemplateResponse],
)
async def install_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Install a validated template, making it Active."""
    try:
        template = await template_service.install_template(
            db, template_id, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ProcessTemplateResponse.model_validate(template))


@router.post(
    "/{template_id}/new-version",
    response_model=EnvelopeResponse[ProcessTemplateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_new_version(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new draft version by cloning an existing template."""
    try:
        template = await template_service.create_new_version(
            db, template_id, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(data=ProcessTemplateResponse.model_validate(template))
