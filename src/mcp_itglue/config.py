"""Configuration management for MCP IT Glue server."""

import logging
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="ITGLUE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # IT Glue API configuration
    api_key: str = ""
    api_url: str = "https://api.itglue.com"

    # Request configuration
    timeout: float = 30.0
    max_retries: int = 3

    # Pagination defaults
    default_page_size: int = 50
    max_page_size: int = 1000

    def is_configured(self) -> bool:
        """Check if the API key is configured."""
        return bool(self.api_key)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def setup_logging() -> logging.Logger:
    """Set up logging to stderr (required for stdio MCP transport)."""
    logger = logging.getLogger("mcp_itglue")
    logger.setLevel(logging.INFO)

    # Use stderr for logging (stdout is reserved for MCP protocol)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger


logger = setup_logging()
