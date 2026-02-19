"""YAML 설정 로딩 + Pydantic 모델."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


class DiscordApiConfig(BaseModel):
    api_base: str = "https://discord.com/api/v9"
    limit: int = Field(default=50, ge=1, le=100)
    delay_sec: float = 1.0
    max_retries: int = 3
    backoff_factor: float = 2.0
    chunk_pages: int = 100  # 청크당 페이지 수


class ChannelConfig(BaseModel):
    name: str
    id: str  # snowflake ID


class D1Config(BaseModel):
    database_id: str = ""
    account_id: str = ""
    api_token: str = ""


class AppConfig(BaseModel):
    discord: DiscordApiConfig = Field(default_factory=DiscordApiConfig)
    channels: list[ChannelConfig] = Field(min_length=1)
    d1: D1Config = Field(default_factory=D1Config)

    @field_validator("channels")
    @classmethod
    def channels_not_empty(cls, v: list[ChannelConfig]) -> list[ChannelConfig]:
        if not v:
            raise ValueError("channels must contain at least one channel")
        return v


def load_config(path: Path | None = None) -> AppConfig:
    """YAML 설정 파일을 로딩하고 Pydantic 모델로 검증한다."""
    config_path = path or _DEFAULT_CONFIG_PATH
    dotenv_path = config_path.parent / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Empty config file: {config_path}")

    # 환경변수 오버라이드 (D1)
    if d1_id := os.environ.get("D1_DATABASE_ID"):
        raw.setdefault("d1", {})
        raw["d1"]["database_id"] = d1_id
    if account_id := os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        raw.setdefault("d1", {})
        raw["d1"]["account_id"] = account_id
    if api_token := os.environ.get("CLOUDFLARE_API_TOKEN"):
        raw.setdefault("d1", {})
        raw["d1"]["api_token"] = api_token

    return AppConfig.model_validate(raw)
