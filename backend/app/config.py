from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Database
    database_url: str = "postgresql://insightsql:insightsql_hpe@10.25.69.114:5432/insightsql"

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_deployment: str = "gpt-5.4-mini-hackathon1"
    azure_openai_api_version: str = "2024-12-01-preview"

    # Deployment rotation for rate-limit resilience
    azure_openai_deployments: list[str] = [
        "gpt-5.4-mini-hackathon1",
        "gpt-5.4-mini-hackathon2",
        "gpt-5.4-mini-hackathon3",
        "gpt-5.4-mini-hackathon4",
    ]

    # App
    app_name: str = "InsightSQL"
    ws_heartbeat_interval: int = 15  # seconds

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
