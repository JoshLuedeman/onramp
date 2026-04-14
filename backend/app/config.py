from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "OnRamp API"
    debug: bool = False

    # Database (empty = dev mode with SQLite)
    database_url: str = ""

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

    model_config = {"env_prefix": "ONRAMP_", "env_file": ".env"}


settings = Settings()
