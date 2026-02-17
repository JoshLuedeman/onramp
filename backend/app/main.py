from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.architecture import router as architecture_router
from app.api.routes.bicep import router as bicep_router
from app.api.routes.compliance import router as compliance_router
from app.api.routes.deployment import router as deployment_router
from app.api.routes.projects import router as projects_router
from app.api.routes.questionnaire import router as questionnaire_router
from app.api.routes.questionnaire_state import router as questionnaire_state_router
from app.api.routes.scoring import router as scoring_router
from app.api.routes.users import router as users_router
from app.config import settings
from app.db.seed import seed_database
from app.db.session import close_db, init_db
from app.security import SecurityHeadersMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(users_router)
app.include_router(questionnaire_router)
app.include_router(compliance_router)
app.include_router(projects_router)
app.include_router(architecture_router)
app.include_router(deployment_router)
app.include_router(bicep_router)
app.include_router(scoring_router)
app.include_router(questionnaire_state_router)


@app.get("/health")
async def health_check():
    status = get_startup_status()
    return {
        "status": "healthy",
        "service": "onramp-api",
        "mode": status["mode"],
        "auth": status["auth"],
        "ai": status["ai"],
        "database": status["database"],
    }
