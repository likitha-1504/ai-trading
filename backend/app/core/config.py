"""Configuration settings for the AI Micro-Trading Agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Micro-Trading Agent"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_PATH: str = "trading_agent.db"

    # Capital limits
    INITIAL_CAPITAL: float = 100.0
    AUTONOMOUS_CAPITAL_THRESHOLD: float = 300.0

    # Environment
    ENVIRONMENT: str = "development"
    IS_PAPER_TRADING: bool = True

    model_config = SettingsConfigDict(
        case_sensitive=True, env_file=".env", extra="ignore"
    )


settings = Settings()
