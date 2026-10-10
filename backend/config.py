import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    Follows Pydantic Settings for strict typing and automated validation.
    """
    APP_NAME: str = "SentinelAI"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    # Database connection string
    # Defaults to PostgreSQL, but also supports SQLite for testing / offline development
    DATABASE_URL: str = "postgresql://sentinel_user:sentinel_pass@localhost:5432/sentinel_db"

    # Authentication & Security
    JWT_SECRET: str = "sentinel_dev_secret_key_random_at_least_32_bytes_long_string_soc"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # LLM & Threat Intelligence (Phase 5 & 6 placeholders)
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = "mock-key"
    LLM_MODEL: str = "gpt-4o-mini"
    THREAT_INTEL_API_KEY: str = "mock-key"

    # CORS origins allowed to communicate with backend
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        # Check both local backend directory and root directory for .env
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton settings instance
settings = Settings()
