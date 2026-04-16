"""Plugin management API routes."""

from fastapi import APIRouter, HTTPException

from app.plugins.loader import get_plugin_registry
from app.schemas.plugin import PluginListResponse, PluginResponse

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("/", response_model=PluginListResponse)
async def list_plugins() -> PluginListResponse:
    """List all registered plugins."""
    registry = get_plugin_registry()
    infos = registry.get_all_plugins()
    return PluginListResponse(
        plugins=[PluginResponse(**info.to_dict()) for info in infos],
        total=len(infos),
    )


@router.get("/{plugin_name}", response_model=PluginResponse)
async def get_plugin(plugin_name: str) -> PluginResponse:
    """Get details of a specific plugin by name."""
    registry = get_plugin_registry()
    info = registry.get_plugin(plugin_name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
    return PluginResponse(**info.to_dict())
