from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "OnRamp API"
    debug: bool = False

    # Database
    database_url: str = "mssql+aioodbc://sa:Password123!@localhost:1433/onramp?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

    # Azure AD / Entra ID
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""

    # Azure AI Foundry
    ai_foundry_endpoint: str = ""
    ai_foundry_model: str = "gpt-4o"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "ONRAMP_", "env_file": ".env"}


settings = Settings()
