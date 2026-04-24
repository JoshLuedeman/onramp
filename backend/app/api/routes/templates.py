"""Template marketplace API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.template import (
    TemplateCreate,
    TemplateListResponse,
    TemplateRatingRequest,
    TemplateResponse,
    TemplateUseRequest,
)
from app.services.template_service import template_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(
    payload: TemplateCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new template from an architecture."""
    if db is None:
        raise HTTPException(
            status_code=503, detail="Database not configured"
        )

    try:
        tenant_id = user.get(
            "tid", user.get("tenant_id", "dev-tenant")
        )
        result = await template_service.create_template(
            db=db,
            data={
                "name": payload.name,
                "description": payload.description,
                "industry": payload.industry,
                "tags": payload.tags,
                "architecture_json": payload.architecture_json,
                "visibility": payload.visibility.value,
            },
            author_tenant_id=tenant_id,
        )
        return TemplateResponse(**result)
    except Exception as e:
        logger.exception("Failed to create template")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    industry: str | None = Query(
        None, description="Filter by industry"
    ),
    tags: str | None = Query(
        None, description="Comma-separated tag filter"
    ),
    visibility: str | None = Query(
        None, description="Filter by visibility"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        20, ge=1, le=100, description="Page size"
    ),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List templates with optional filters."""
    if db is None:
        # Return curated templates from memory
        curated = template_service.get_curated_templates()
        return TemplateListResponse(
            templates=[
                TemplateResponse(
                    id=t["id"],
                    name=t["name"],
                    description=t.get("description"),
                    industry=t["industry"],
                    tags=t.get("tags", []),
                    architecture_json=t.get("architecture_json"),
                    visibility=t.get("visibility", "curated"),
                    download_count=0,
                    rating_up=0,
                    rating_down=0,
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00",
                )
                for t in curated
            ],
            total=len(curated),
            page=1,
            page_size=len(curated),
        )

    try:
        tag_list = (
            [t.strip() for t in tags.split(",") if t.strip()]
            if tags
            else None
        )
        result = await template_service.list_templates(
            db=db,
            industry=industry,
            tags=tag_list,
            visibility=visibility,
            page=page,
            page_size=page_size,
        )
        return TemplateListResponse(**result)
    except Exception as e:
        logger.exception("Failed to list templates")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a template by ID."""
    if db is None:
        raise HTTPException(
            status_code=503, detail="Database not configured"
        )

    try:
        result = await template_service.get_template(
            db=db, template_id=template_id
        )
        if result is None:
            raise HTTPException(
                status_code=404, detail="Template not found"
            )
        return TemplateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get template")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{template_id}/use", response_model=TemplateResponse
)
async def use_template(
    template_id: str,
    payload: TemplateUseRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply a template to a project."""
    if db is None:
        raise HTTPException(
            status_code=503, detail="Database not configured"
        )

    try:
        result = await template_service.use_template(
            db=db,
            template_id=template_id,
            project_id=payload.project_id,
        )
        if result is None:
            raise HTTPException(
                status_code=404, detail="Template not found"
            )
        return TemplateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to use template")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{template_id}/rate", response_model=TemplateResponse
)
async def rate_template(
    template_id: str,
    payload: TemplateRatingRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rate a template up or down."""
    if db is None:
        raise HTTPException(
            status_code=503, detail="Database not configured"
        )

    try:
        result = await template_service.rate_template(
            db=db,
            template_id=template_id,
            rating=payload.rating.value,
        )
        if result is None:
            raise HTTPException(
                status_code=404, detail="Template not found"
            )
        return TemplateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to rate template")
        raise HTTPException(status_code=500, detail=str(e))
