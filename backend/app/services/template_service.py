"""Template marketplace service — CRUD, filtering, and curated templates."""

import json
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import generate_uuid

logger = logging.getLogger(__name__)


class TemplateService:
    """Singleton service for the template marketplace."""

    async def create_template(
        self,
        db: AsyncSession,
        data: dict,
        author_tenant_id: str | None = None,
    ) -> dict:
        """Save an architecture as a reusable template."""
        from app.models.template import Template

        template = Template(
            id=generate_uuid(),
            name=data["name"],
            description=data.get("description"),
            industry=data["industry"],
            tags=data.get("tags", []),
            architecture_json=data["architecture_json"],
            author_tenant_id=author_tenant_id,
            visibility=data.get("visibility", "private"),
        )
        db.add(template)
        await db.flush()
        await db.refresh(template)
        logger.info("Template created: %s (%s)", template.name, template.id)
        return self._row_to_dict(template)

    async def list_templates(
        self,
        db: AsyncSession,
        industry: str | None = None,
        tags: list[str] | None = None,
        visibility: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Browse templates with optional filters and pagination."""
        from app.models.template import Template

        query = select(Template)

        if industry:
            query = query.where(Template.industry == industry)
        if visibility:
            query = query.where(Template.visibility == visibility)

        # Count total before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        # Tag filtering — match any tag in the JSON list
        if tags:
            filtered_ids: list[str] = []
            all_result = await db.execute(query)
            for row in all_result.scalars().all():
                row_tags = row.tags or []
                if any(t in row_tags for t in tags):
                    filtered_ids.append(row.id)
            query = select(Template).where(Template.id.in_(filtered_ids))
            total = len(filtered_ids)

        # Pagination
        offset = (page - 1) * page_size
        query = query.order_by(Template.created_at.desc())
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        templates = result.scalars().all()

        logger.info(
            "Listed templates: page=%d, size=%d, total=%d",
            page, page_size, total,
        )
        return {
            "templates": [self._row_to_dict(t) for t in templates],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_template(
        self,
        db: AsyncSession,
        template_id: str,
    ) -> dict | None:
        """Get a single template by ID."""
        from app.models.template import Template

        result = await db.execute(
            select(Template).where(Template.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template is None:
            return None
        return self._row_to_dict(template)

    async def use_template(
        self,
        db: AsyncSession,
        template_id: str,
        project_id: str,
    ) -> dict | None:
        """Clone a template's architecture into a project.

        Increments download_count and copies architecture_json
        into the project's Architecture row.
        """
        from app.models.architecture import Architecture
        from app.models.template import Template

        result = await db.execute(
            select(Template).where(Template.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template is None:
            return None

        # Increment download count
        template.download_count = (template.download_count or 0) + 1

        # Parse architecture JSON and apply to project
        arch_data: Any = {}
        if template.architecture_json:
            try:
                arch_data = json.loads(template.architecture_json)
            except (json.JSONDecodeError, TypeError):
                arch_data = {"raw": template.architecture_json}

        # Check if project already has an architecture
        existing = await db.execute(
            select(Architecture).where(
                Architecture.project_id == project_id
            )
        )
        architecture = existing.scalar_one_or_none()

        if architecture:
            architecture.architecture_data = arch_data
        else:
            architecture = Architecture(
                id=generate_uuid(),
                project_id=project_id,
                architecture_data=arch_data,
            )
            db.add(architecture)

        await db.flush()
        await db.refresh(template)
        logger.info(
            "Template %s applied to project %s (downloads: %d)",
            template_id, project_id, template.download_count,
        )
        return self._row_to_dict(template)

    async def rate_template(
        self,
        db: AsyncSession,
        template_id: str,
        rating: str,
    ) -> dict | None:
        """Rate a template thumbs-up or thumbs-down."""
        from app.models.template import Template

        result = await db.execute(
            select(Template).where(Template.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template is None:
            return None

        if rating == "up":
            template.rating_up = (template.rating_up or 0) + 1
        elif rating == "down":
            template.rating_down = (template.rating_down or 0) + 1
        else:
            logger.warning("Invalid rating value: %s", rating)
            return self._row_to_dict(template)

        await db.flush()
        await db.refresh(template)
        logger.info(
            "Template %s rated %s (up=%d, down=%d)",
            template_id, rating, template.rating_up, template.rating_down,
        )
        return self._row_to_dict(template)

    def get_curated_templates(self) -> list[dict]:
        """Return built-in curated template definitions.

        These are static and do not require a database session.
        """
        from app.db.seed_templates import CURATED_TEMPLATES

        return list(CURATED_TEMPLATES)

    @staticmethod
    def _row_to_dict(row: Any) -> dict:
        return {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "industry": row.industry,
            "tags": row.tags or [],
            "architecture_json": row.architecture_json,
            "author_tenant_id": row.author_tenant_id,
            "visibility": row.visibility,
            "download_count": row.download_count or 0,
            "rating_up": row.rating_up or 0,
            "rating_down": row.rating_down or 0,
            "created_at": (
                row.created_at.isoformat() if row.created_at else None
            ),
            "updated_at": (
                row.updated_at.isoformat() if row.updated_at else None
            ),
        }


template_service = TemplateService()
