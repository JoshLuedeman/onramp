"""Database seeding — populates questions and compliance frameworks on first boot."""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory

logger = logging.getLogger("onramp.seed")


async def seed_database():
    """Seed the database with initial data if tables are empty. Idempotent."""
    factory = get_session_factory()
    if factory is None:
        logger.info("No database configured — skipping seed")
        return

    async with factory() as session:
        await _seed_dev_tenant(session)
        await _seed_question_categories(session)
        await _seed_questions(session)
        await _seed_compliance_frameworks(session)
        await _seed_curated_templates(session)
        await session.commit()
        logger.info("Database seeding complete")


async def _seed_curated_templates(session: AsyncSession):
    """Seed curated marketplace templates."""
    from app.db.seed_templates import seed_curated_templates
    await seed_curated_templates(session)


async def _seed_dev_tenant(session: AsyncSession):
    """Seed a dev tenant and user for local development."""
    from app.config import settings
    if settings.azure_tenant_id:
        return  # Only seed dev data in dev mode

    from app.models.tenant import Tenant
    from app.models.user import User

    count = await session.scalar(select(func.count()).select_from(Tenant))
    if count and count > 0:
        return

    tenant = Tenant(id="dev-tenant", name="Development Tenant", is_active=True)
    session.add(tenant)
    await session.flush()

    user = User(
        id="dev-user-id",
        entra_object_id="dev-user-id",
        email="dev@onramp.local",
        display_name="Development User",
        role="admin",
        is_active=True,
        tenant_id="dev-tenant",
    )
    session.add(user)
    logger.info("Seeded dev tenant and user")


async def _seed_question_categories(session: AsyncSession):
    """Seed question categories from the questionnaire service."""
    from app.models import QuestionCategory

    count = await session.scalar(select(func.count()).select_from(QuestionCategory))
    if count and count > 0:
        logger.info("Question categories already seeded (%d rows)", count)
        return

    from app.services.questionnaire import questionnaire_service
    categories = questionnaire_service.get_categories()

    for i, cat in enumerate(categories):
        session.add(QuestionCategory(
            id=cat["id"],
            name=cat["name"],
            caf_design_area=cat.get("caf_area", ""),
            description="",
            display_order=i,
        ))

    await session.flush()
    logger.info("Seeded %d question categories", len(categories))


async def _seed_questions(session: AsyncSession):
    """Seed questions from the questionnaire service."""
    from app.models import Question

    count = await session.scalar(select(func.count()).select_from(Question))
    if count and count > 0:
        logger.info("Questions already seeded (%d rows)", count)
        return

    from app.services.questionnaire import questionnaire_service
    questions = questionnaire_service.get_all_questions()

    for i, q in enumerate(questions):
        session.add(Question(
            id=q["id"],
            category_id=q.get("category", ""),
            text=q["text"],
            question_type=q["type"],
            options=q.get("options"),
            is_required=q.get("required", True),
            display_order=q.get("order", i),
            min_org_size=q.get("min_org_size"),
        ))

    await session.flush()
    logger.info("Seeded %d questions", len(questions))


async def _seed_compliance_frameworks(session: AsyncSession):
    """Seed compliance frameworks and controls."""
    from app.models import ComplianceControl, ComplianceFramework
    from app.services.compliance_data import COMPLIANCE_FRAMEWORKS

    count = await session.scalar(select(func.count()).select_from(ComplianceFramework))
    if count and count > 0:
        logger.info("Compliance frameworks already seeded (%d rows)", count)
        return

    total_controls = 0

    for fw in COMPLIANCE_FRAMEWORKS:
        fw_id = str(uuid.uuid4())
        session.add(ComplianceFramework(
            id=fw_id,
            name=fw["name"],
            short_name=fw["short_name"],
            description=fw.get("description", ""),
            version=fw.get("version", "1.0"),
        ))

        for ctrl in fw.get("controls", []):
            session.add(ComplianceControl(
                id=str(uuid.uuid4()),
                framework_id=fw_id,
                control_id=ctrl.get("control_id", ""),
                title=ctrl.get("title", ""),
                description=ctrl.get("description", ""),
                category=ctrl.get("category", ""),
                severity=ctrl.get("severity", "medium"),
                azure_policy_definitions=ctrl.get("azure_policies"),
            ))
            total_controls += 1

    await session.flush()
    logger.info("Seeded %d compliance frameworks with %d controls", len(COMPLIANCE_FRAMEWORKS), total_controls)
