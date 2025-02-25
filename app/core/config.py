from pydantic_settings import BaseSettings
from pydantic import SecretStr
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Email Configuration
    EMAIL_ADDRESS: str
    EMAIL_PASSWORD: SecretStr

    # Email Server Settings (with defaults)
    IMAP_SERVER: str = "imap.gmail.com"
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465

    # AI Configuration
    ANTHROPIC_API_KEY: SecretStr = None
    LITELLM_MODEL: str = (
        "anthropic/claude-3-5-sonnet-20240620"  # Latest Claude 3.5 Sonnet model
    )
    LITELLM_BASE_URL: Optional[str] = None  # Optional proxy URL
    LITELLM_COST_TRACKING: bool = True  # Enable cost tracking

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
