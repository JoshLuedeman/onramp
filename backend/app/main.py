from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.adr import router as adr_router
from app.api.routes.ai_quality import router as ai_quality_router
from app.api.routes.ai_validation import router as ai_validation_router
from app.api.routes.approvals import router as approvals_router
from app.api.routes.architecture import router as architecture_router
from app.api.routes.bicep import router as bicep_router
from app.api.routes.chat import router as chat_router
from app.api.routes.compliance import router as compliance_router
from app.api.routes.cost import router as cost_router
from app.api.routes.deployment import router as deployment_router
from app.api.routes.discovery import router as discovery_router
from app.api.routes.drift import router as drift_router
from app.api.routes.drift_notifications import router as drift_notifications_router
from app.api.routes.events import router as events_router
from app.api.routes.governance_audit import router as governance_audit_router
from app.api.routes.governance_scorecard import router as governance_scorecard_router
from app.api.routes.governance_tasks import router as governance_tasks_router
from app.api.routes.migration import router as migration_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.plugins import router as plugins_router
from app.api.routes.policies import router as policies_router
from app.api.routes.policy_compliance import router as policy_compliance_router
from app.api.routes.projects import router as projects_router
from app.api.routes.questionnaire import router as questionnaire_router
from app.api.routes.questionnaire_state import router as questionnaire_state_router
from app.api.routes.rbac_health import router as rbac_health_router
from app.api.routes.regulatory import router as regulatory_router
from app.api.routes.scan_operations import router as scan_operations_router
from app.api.routes.scoring import router as scoring_router
from app.api.routes.security import router as security_router
from app.api.routes.sizing import router as sizing_router
from app.api.routes.tagging import router as tagging_router
from app.api.routes.users import router as users_router
from app.api.routes.workloads import router as workloads_router
from app.config import settings
from app.db.seed import seed_database
from app.db.session import close_db, init_db
from app.security import (
    RateLimitMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
)
from app.startup import get_startup_status, log_plugin_status, validate_environment


@asynccontextmanager
async def lifespan(app):
    validate_environment()
    await init_db()
    await seed_database()

    from app.plugins.loader import plugin_registry

    plugin_registry.discover_plugins("plugins")
    plugin_registry.load_entry_points()
    log_plugin_status()

    # Start the governance task scheduler
    # Import monitors to register periodic tasks via @task_scheduler.periodic
    import app.services.tagging_monitor  # noqa: F401
    from app.services.task_scheduler import task_scheduler

    await task_scheduler.start()

    yield

    # Shut down scheduler before closing DB
    await task_scheduler.shutdown()
    await close_db()


app = FastAPI(
    title="OnRamp API",
    description="Azure Landing Zone Architect & Deployer",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — restrict methods/headers in production
_cors_methods = (
    ["*"] if settings.is_dev_mode
    else ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)
_cors_headers = (
    ["*"] if settings.is_dev_mode
    else ["Authorization", "Content-Type", "Accept", "X-Requested-With"]
)

# Middleware ordering: Starlette applies middleware in reverse add order.
# Add rate-limit/validation first so CORS and security headers wrap ALL responses
# (including 429/413/400 early returns).
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=_cors_methods,
    allow_headers=_cors_headers,
)

app.include_router(users_router)
app.include_router(questionnaire_router)
app.include_router(compliance_router)
app.include_router(projects_router)
app.include_router(architecture_router)
app.include_router(adr_router)
app.include_router(deployment_router)
app.include_router(bicep_router)
app.include_router(scoring_router)
app.include_router(questionnaire_state_router)
app.include_router(discovery_router)
app.include_router(workloads_router)
app.include_router(migration_router)
app.include_router(notifications_router)
app.include_router(plugins_router)
app.include_router(events_router)
app.include_router(governance_tasks_router)
app.include_router(drift_router)
app.include_router(drift_notifications_router)
app.include_router(rbac_health_router)
app.include_router(cost_router)
app.include_router(policies_router)
app.include_router(policy_compliance_router)
app.include_router(tagging_router)
app.include_router(governance_scorecard_router)
app.include_router(approvals_router)
app.include_router(governance_audit_router)
app.include_router(scan_operations_router)
app.include_router(ai_quality_router)
app.include_router(ai_validation_router)
app.include_router(chat_router)
app.include_router(regulatory_router)
app.include_router(security_router)
app.include_router(sizing_router)


@app.get("/health")
async def health_check():
    """Health endpoint — minimal in production, verbose in dev mode."""
    status = get_startup_status()
    if settings.is_dev_mode:
        return {
            "status": "healthy",
            "service": "onramp-api",
            "mode": status["mode"],
            "auth": status["auth"],
            "ai": status["ai"],
            "database": status["database"],
        }
    return {"status": "healthy"}
