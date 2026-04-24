"""Microsoft Entra ID (Azure AD) token validation middleware."""

import logging

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    """Fetch and cache the JWKS from Microsoft's discovery endpoint."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    openid_config_url = (
        f"https://login.microsoftonline.com/{settings.azure_tenant_id}"
        "/v2.0/.well-known/openid-configuration"
    )
    async with httpx.AsyncClient() as client:
        config_resp = await client.get(openid_config_url)
        config_resp.raise_for_status()
        jwks_uri = config_resp.json()["jwks_uri"]

        jwks_resp = await client.get(jwks_uri)
        jwks_resp.raise_for_status()
        _jwks_cache = jwks_resp.json()

    return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Validate the bearer token and return user claims.

    In development mode (no tenant configured), returns a mock user.
    """
    if settings.debug:
        logger.warning(
            "⚠️  Mock auth active — ONRAMP_DEBUG=true. "
            "Do NOT use in production."
        )
        return {
            "sub": "dev-user-id",
            "name": "Development User",
            "email": "dev@onramp.local",
            "roles": ["admin"],
        }

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        import jwt as pyjwt
        from jwt import PyJWKClient

        jwks_url = (
            f"https://login.microsoftonline.com/{settings.azure_tenant_id}"
            "/discovery/v2.0/keys"
        )
        jwk_client = PyJWKClient(jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        claims = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.azure_client_id,
            issuer=f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0",
        )
        return {
            "sub": claims.get("sub", ""),
            "name": claims.get("name", ""),
            "email": claims.get("preferred_username", ""),
            "roles": claims.get("roles", []),
            "tenant_id": claims.get("tid", ""),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_role(required_role: str):
    """Create a dependency that requires a specific role."""

    async def _check_role(
        user: dict = Depends(get_current_user),
    ) -> dict:
        if required_role not in user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user

    return _check_role
