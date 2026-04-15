from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.adr import router as adr_router
from app.api.routes.architecture import router as architecture_router
from app.api.routes.bicep import router as bicep_router
from app.api.routes.compliance import router as compliance_router
from app.api.routes.deployment import router as deployment_router
from app.api.routes.discovery import router as discovery_router
from app.api.routes.migration import router as migration_router
from app.api.routes.projects import router as projects_router
from app.api.routes.questionnaire import router as questionnaire_router
from app.api.routes.questionnaire_state import router as questionnaire_state_router
from app.api.routes.scoring import router as scoring_router
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
from app.startup import get_startup_status, validate_environment


@asynccontextmanager
async def lifespan(app):
    validate_environment()
    await init_db()
    await seed_database()
    yield
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
