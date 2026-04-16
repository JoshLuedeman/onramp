"""Cloud environment model for sovereign cloud configuration.

Defines the supported Azure cloud environments (Commercial, Government,
China/21Vianet) and their corresponding service endpoints.
"""

from enum import Enum

from pydantic import BaseModel


class CloudEnvironment(str, Enum):
    """Supported Azure cloud environments."""

    COMMERCIAL = "commercial"
    GOVERNMENT = "government"
    CHINA = "china"


class CloudEndpoints(BaseModel):
    """Service endpoints for a specific Azure cloud environment."""

    resource_manager: str
    authentication: str
    portal: str
    graph: str
    storage_suffix: str
    sql_suffix: str
    keyvault_suffix: str
    ai_foundry: str | None = None


CLOUD_ENDPOINTS: dict[CloudEnvironment, CloudEndpoints] = {
    CloudEnvironment.COMMERCIAL: CloudEndpoints(
        resource_manager="https://management.azure.com",
        authentication="https://login.microsoftonline.com",
        portal="https://portal.azure.com",
        graph="https://graph.microsoft.com",
        storage_suffix=".blob.core.windows.net",
        sql_suffix=".database.windows.net",
        keyvault_suffix=".vault.azure.net",
        ai_foundry="https://ai.azure.com",
    ),
    CloudEnvironment.GOVERNMENT: CloudEndpoints(
        resource_manager="https://management.usgovcloudapi.net",
        authentication="https://login.microsoftonline.us",
        portal="https://portal.azure.us",
        graph="https://graph.microsoft.us",
        storage_suffix=".blob.core.usgovcloudapi.net",
        sql_suffix=".database.usgovcloudapi.net",
        keyvault_suffix=".vault.usgovcloudapi.net",
        ai_foundry=None,
    ),
    CloudEnvironment.CHINA: CloudEndpoints(
        resource_manager="https://management.chinacloudapi.cn",
        authentication="https://login.chinacloudapi.cn",
        portal="https://portal.azure.cn",
        graph="https://microsoftgraph.chinacloudapi.cn",
        storage_suffix=".blob.core.chinacloudapi.cn",
        sql_suffix=".database.chinacloudapi.cn",
        keyvault_suffix=".vault.azure.cn",
        ai_foundry=None,
    ),
}
