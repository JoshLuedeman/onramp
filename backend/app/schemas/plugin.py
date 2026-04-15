"""Plugin schemas for API responses."""

from pydantic import BaseModel


class PluginResponse(BaseModel):
    """Schema for a single plugin."""

    name: str
    version: str
    plugin_type: str
    description: str
    enabled: bool


class PluginListResponse(BaseModel):
    """Schema for a list of plugins."""

    plugins: list[PluginResponse]
    total: int
