import os
import sys
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "YouTube Discovery Engine (German Trading Communities)"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database URLs
    DATABASE_URL: str = "postgresql://postgres:postgres@127.0.0.1:5432/trading_discovery"
    ASYNC_DATABASE_URL: Optional[str] = None

    # Redis / Celery
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/0"

    # YouTube API Configuration
    YOUTUBE_API_KEY: str = "mock_api_key_for_now"

    # Crawler Settings
    SCHEDULER_FREQUENCY: int = 30  # in minutes
    MAX_RESULTS: int = 50
    LANGUAGE_THRESHOLD: float = 0.8
    MIN_SUBSCRIBER_COUNT: int = 100
    MAX_SUBSCRIBER_COUNT: int = 10000000
    MAX_SEARCH_DEPTH: int = 3
    TRANSCRIPT_TIMEOUT: int = 30

    model_config = SettingsConfigDict(
        env_file=[
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
            os.path.join(os.getcwd(), ".env"),
            ".env"
        ],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def model_post_init(self, __context) -> None:
        # Prioritize absolute system environment variables over Pydantic file defaults
        env_db_url = os.getenv("DATABASE_URL")
        if env_db_url:
            self.DATABASE_URL = env_db_url

        env_redis_url = os.getenv("REDIS_URL")
        if env_redis_url:
            self.REDIS_URL = env_redis_url
            self.CELERY_BROKER_URL = env_redis_url
            self.CELERY_RESULT_BACKEND = env_redis_url

        # Detect pytest and override defaults
        is_testing = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)
        if is_testing:
            self.DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5432/trading_discovery_test"

        if not self.ASYNC_DATABASE_URL:
            # Auto-build async db url from database url if not specified
            self.ASYNC_DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


settings = Settings()
