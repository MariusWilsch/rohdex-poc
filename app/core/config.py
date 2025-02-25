from pydantic_settings import BaseSettings
from pydantic import SecretStr
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    # Email Configuration
    EMAIL_ADDRESS: str
    EMAIL_PASSWORD: SecretStr

    # Email Server Settings (with defaults)
    IMAP_SERVER: str = "imap.gmail.com"
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465

    # Email Polling Configuration
    EMAIL_POLLING_ENABLED: bool = True
    EMAIL_POLLING_INTERVAL: int = 30  # seconds (30 seconds)
    EMAIL_LABEL_FILTER: str = "Rohdex-Automation"
    EMAIL_MAX_FETCH: int = 2  # Max emails to process per polling cycle

    # Template Configuration
    TEMPLATE_PACKING_LIST_PATH: str = "template/template_packing_list.csv"

    # Logging Configuration
    LOG_LEVEL: str = "INFO"

    # AI Configuration
    # You can use either Anthropic or OpenAI API keys
    # If both are provided, the system will use the model specified in LITELLM_MODEL
    ANTHROPIC_API_KEY: Optional[SecretStr] = None
    OPENAI_API_KEY: Optional[SecretStr] = None

    # Default model (supports both Anthropic and OpenAI models)
    # For Anthropic: "anthropic/claude-3-5-sonnet-20240620"
    # For OpenAI: "gpt-4o", "gpt-4o-mini", etc.
    LITELLM_MODEL: str = "anthropic/claude-3-5-sonnet-20240620"

    LITELLM_BASE_URL: Optional[str] = None  # Optional proxy URL
    LITELLM_COST_TRACKING: bool = True  # Enable cost tracking

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()

    # Set environment variables for API keys
    if settings.ANTHROPIC_API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY.get_secret_value()
        print("Anthropic API key set in environment")

    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY.get_secret_value()
        print("OpenAI API key set in environment")

    return settings
