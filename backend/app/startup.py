"""Startup validation and diagnostics."""

import logging
import sys

from app.config import settings

logger = logging.getLogger("onramp.startup")


def validate_environment() -> dict:
    """Validate environment configuration and return a status report.

    Returns a dict with mode (development/production) and any warnings.
    """
    warnings = []
    errors = []
    mode = "development"

    # Check Azure Entra ID
    if settings.azure_tenant_id and settings.azure_client_id:
        mode = "production"
        logger.info("✅ Entra ID configured (tenant: %s)", settings.azure_tenant_id[:8] + "...")
    else:
        warnings.append("Entra ID not configured — using mock authentication")
        logger.warning("⚠️  Entra ID not configured — running in dev mode with mock auth")

    # Check AI Foundry
    if settings.ai_foundry_endpoint:
        if settings.ai_foundry_key:
            logger.info(
                "✅ AI Foundry configured (endpoint: %s, auth: api-key)",
                settings.ai_foundry_endpoint[:30] + "...",
            )
        elif settings.managed_identity_client_id:
            logger.info(
                "✅ AI Foundry configured (endpoint: %s, auth: managed-identity)",
                settings.ai_foundry_endpoint[:30] + "...",
            )
        else:
            warnings.append("AI Foundry endpoint set but no auth configured (need key or MI)")
            logger.warning("⚠️  AI Foundry endpoint set but no auth — AI features will use mock data")
    else:
        warnings.append("AI Foundry not configured — using mock responses")
        logger.warning("⚠️  AI Foundry not configured — AI features will return mock data")

    # Check Database
    if settings.database_url:
        db_type = (
            "MSSQL" if "mssql" in settings.database_url
            else "SQLite" if "sqlite" in settings.database_url
            else "Other"
        )
        # Detect Entra-authenticated SQL connections (no credentials in URL)
        entra_sql = "mssql" in settings.database_url and "://@" in settings.database_url
        if entra_sql:
            db_type = "MSSQL + Entra auth"
            if settings.managed_identity_client_id:
                logger.info(
                    "✅ Database configured (%s, MI: %s…)",
                    db_type,
                    settings.managed_identity_client_id[:8],
                )
            else:
                logger.info("✅ Database configured (%s, DefaultAzureCredential)", db_type)
        else:
            logger.info("✅ Database configured (%s)", db_type)
    else:
        warnings.append("Database not configured — data will not persist")
        logger.warning("⚠️  Database not configured — no data persistence")

    # Check CORS
    if settings.cors_origins:
        logger.info("✅ CORS origins: %s", str(settings.cors_origins)[:80])
    else:
        warnings.append("CORS origins not set — using permissive defaults")

    # Production-mode validations
    if mode == "production":
        if not settings.database_url:
            errors.append("Production mode requires ONRAMP_DATABASE_URL")
        if not settings.ai_foundry_endpoint:
            warnings.append("Production mode without AI Foundry — architecture generation will use archetypes only")

    # Report
    if errors:
        for error in errors:
            logger.error("❌ %s", error)
        logger.error("Cannot start in production mode with configuration errors.")
        logger.error("Set required environment variables or clear ONRAMP_AZURE_TENANT_ID for dev mode.")
        sys.exit(1)

    logger.info("🚀 OnRamp starting in %s mode", mode.upper())
    if warnings:
        logger.info("📋 %d warning(s) — see above for details", len(warnings))

    return {
        "mode": mode,
        "warnings": warnings,
        "errors": errors,
        "auth": "entra_id" if settings.azure_tenant_id else "mock",
        "ai": (
            "ai_foundry_key"
            if (settings.ai_foundry_endpoint and settings.ai_foundry_key)
            else "ai_foundry_mi"
            if (settings.ai_foundry_endpoint and settings.managed_identity_client_id)
            else "mock"
        ),
        "database": "configured" if settings.database_url else "none",
    }


# Cached result
_startup_status = None


def log_plugin_status() -> None:
    """Log the number of loaded plugins.

    Must be called *after* plugin discovery completes in the application
    lifespan — calling it earlier will always report zero plugins.
    """
    from app.plugins.loader import plugin_registry

    plugin_count = len(plugin_registry.get_all_plugins())
    logger.info("🔌 %d plugin(s) loaded", plugin_count)


def get_startup_status() -> dict:
    """Get cached startup validation status."""
    global _startup_status
    if _startup_status is None:
        _startup_status = validate_environment()
    return _startup_status
