from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "OnRamp API"
    debug: bool = False

    # Database (empty = dev mode with SQLite)
    database_url: str = ""

    # Managed identity client ID for Entra-authenticated SQL connections.
    # Set when the backend runs on Azure with a user-assigned managed identity.
    managed_identity_client_id: str = ""

    # Azure AD / Entra ID
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""

    # Azure AI Foundry
    ai_foundry_endpoint: str = ""
    ai_foundry_key: str = ""
    ai_foundry_deployment: str = ""
    ai_foundry_model: str = "gpt-4o"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # Content Security Policy (empty = use default CSP)
    csp_policy: str = ""

    # Rate limiting (requests per minute)
    rate_limit_default: int = 60
    rate_limit_ai: int = 5
    rate_limit_deploy: int = 3

    model_config = {"env_prefix": "ONRAMP_", "env_file": ".env"}

    @property
    def is_dev_mode(self) -> bool:
        """True when Azure production settings are not fully configured."""
        return not (self.azure_tenant_id and self.azure_client_id)


settings = Settings()
