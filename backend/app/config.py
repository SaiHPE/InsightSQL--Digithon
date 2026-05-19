from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Database — Required: set via DATABASE_URL environment variable
    database_url: str = ""

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

    # Ollama Fallback
    ollama_fallback_enabled: bool = False
    ollama_endpoint: str = ""
    ollama_model: str = ""

    @model_validator(mode='after')
    def validate_ollama_config(self) -> 'Settings':
        if self.ollama_fallback_enabled:
            if not self.ollama_endpoint:
                raise ValueError("ollama_endpoint must be set when ollama_fallback_enabled is True")
            if not self.ollama_model:
                raise ValueError("ollama_model must be set when ollama_fallback_enabled is True")
        return self

    # Webhook authentication
    webhook_api_key: str = ""

    # App
    app_name: str = "InsightSQL"
    ws_heartbeat_interval: int = 15  # seconds
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
