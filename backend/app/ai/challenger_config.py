"""Configuration for DeepSeek-R1 Adversarial Challenger."""

from pydantic import BaseModel, Field


class DeepSeekR1Config(BaseModel):
    """Configuration parameters for DeepSeek-R1 challenger inference, timeouts, and retries."""

    endpoint: str = "http://localhost:11434/api/generate"
    model_name: str = "deepseek-r1:latest"
    model_version: str = "v1.0"
    prompt_version: str = "deepseek-r1-challenger-v1.0.0"
    timeout_seconds: float = Field(default=5.0, ge=0.1, le=60.0)
    max_retries: int = Field(default=2, ge=0, le=5)
    retry_backoff_seconds: float = Field(default=0.2, ge=0.001, le=10.0)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    format: str = "json"
