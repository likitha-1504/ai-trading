"""Configuration for Qwen3 Primary Market Analyst."""

from decimal import Decimal

from pydantic import BaseModel, Field


class Qwen3Config(BaseModel):
    """Configuration parameters for Qwen3 analyst inference, timeouts, and retries."""

    endpoint: str = "http://localhost:11434/api/generate"
    model_name: str = "qwen3:latest"
    model_version: str = "v1.0"
    prompt_version: str = "qwen3-analyst-v1.0.0"
    timeout_seconds: float = Field(default=3.0, ge=0.1, le=60.0)
    max_retries: int = Field(default=2, ge=0, le=5)
    retry_backoff_seconds: float = Field(default=0.2, ge=0.001, le=10.0)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    format: str = "json"
    min_confidence_for_proceed: Decimal = Field(default=Decimal("0.60"), ge=Decimal("0.0"), le=Decimal("1.0"))
