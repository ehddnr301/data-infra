from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    slack_bot_token: str = Field(alias="SLACK_BOT_TOKEN")
    slack_signing_secret: str = Field(alias="SLACK_SIGNING_SECRET")
    slack_channel_id: str = Field(alias="SLACK_CHANNEL_ID")

    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-5-20250929", alias="ANTHROPIC_MODEL")
    anthropic_timeout_seconds: float = Field(
        default=30.0, alias="OPENCLAW_ANTHROPIC_TIMEOUT_SECONDS"
    )
    anthropic_max_retries: int = Field(default=2, alias="OPENCLAW_ANTHROPIC_MAX_RETRIES")
    anthropic_max_tokens: int = Field(default=1024, alias="OPENCLAW_ANTHROPIC_MAX_TOKENS")
    planner_prompt_max_columns: int = Field(default=80, alias="OPENCLAW_PLANNER_PROMPT_MAX_COLUMNS")
    planner_fallback_max_columns: int = Field(
        default=30, alias="OPENCLAW_PLANNER_FALLBACK_MAX_COLUMNS"
    )

    catalog_api_base_url: AnyHttpUrl = Field(alias="CATALOG_API_BASE_URL")
    catalog_internal_bearer: str = Field(alias="CATALOG_INTERNAL_BEARER")

    run_mode: Literal["dry-run", "apply"] = Field(default="dry-run", alias="OPENCLAW_RUN_MODE")
    write_enabled: bool = Field(default=False, alias="OPENCLAW_WRITE_ENABLED")
    approval_ttl_seconds: int = Field(default=300, alias="OPENCLAW_APPROVAL_TTL_SECONDS")

    max_retry_attempts: int = Field(default=3, alias="OPENCLAW_MAX_RETRY_ATTEMPTS")
    retry_backoff_ms: int = Field(default=1000, alias="OPENCLAW_RETRY_BACKOFF_MS")

    app_version: str = Field(default="0.1.0", alias="OPENCLAW_APP_VERSION")


def load_settings() -> Settings:
    return Settings()
