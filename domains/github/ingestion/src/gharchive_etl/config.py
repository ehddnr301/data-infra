"""YAML 설정 로딩 + Pydantic 모델."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


# ── 설정 모델 ──────────────────────────────────────────


class GharchiveConfig(BaseModel):
    base_url: str = "https://data.gharchive.org"


class HttpConfig(BaseModel):
    download_timeout_sec: int = 120
    max_retries: int = 3
    backoff_factor: float = 2.0
    max_concurrency: int = 4
    user_agent: str = "gharchive-etl/0.1.0 (pseudolab)"


class R2Config(BaseModel):
    bucket_name: str = "github-archive-raw"
    prefix: str = "raw/github-archive"
    endpoint: str | None = None


class D1Config(BaseModel):
    database_id: str = ""
    account_id: str = ""
    api_token: str = ""


class AppConfig(BaseModel):
    """애플리케이션 전체 설정."""

    gharchive: GharchiveConfig = Field(default_factory=GharchiveConfig)
    target_orgs: list[str] = Field(min_length=1)
    event_types: list[str] = Field(default_factory=list)
    exclude_repos: list[str] = Field(default_factory=list)
    http: HttpConfig = Field(default_factory=HttpConfig)
    r2: R2Config = Field(default_factory=R2Config)
    d1: D1Config = Field(default_factory=D1Config)

    @field_validator("target_orgs")
    @classmethod
    def target_orgs_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("target_orgs must contain at least one org")
        return v


# ── 로딩 ───────────────────────────────────────────────


def load_config(path: Path | None = None) -> AppConfig:
    """YAML 설정 파일을 로딩하고 Pydantic 모델로 검증한다.

    환경변수 우선순위: 시스템 환경변수 > .env 파일 > config.yaml 기본값
    """
    config_path = path or _DEFAULT_CONFIG_PATH

    # .env 파일 로딩: config.yaml과 같은 디렉터리의 .env를 탐색
    dotenv_path = config_path.parent / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Empty config file: {config_path}")

    # 환경변수 오버라이드
    if account_id := os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        raw.setdefault("r2", {})
        raw["r2"]["endpoint"] = f"https://{account_id}.r2.cloudflarestorage.com"

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
