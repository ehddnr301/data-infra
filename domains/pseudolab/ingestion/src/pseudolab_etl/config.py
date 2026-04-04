"""YAML 설정 로딩 + Pydantic 모델."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


class SupabaseConfig(BaseModel):
    host: str = ""
    port: int = 5432
    database: str = "postgres"
    user: str = ""
    password: str = ""
    sslmode: str = "require"


class D1Config(BaseModel):
    database_id: str = ""
    account_id: str = ""
    api_token: str = ""


class R2Config(BaseModel):
    bucket_name: str = "github-archive-raw"
    prefix: str = "pseudolab/dl"


class PiiConfig(BaseModel):
    hash_salt: str = ""


class AppConfig(BaseModel):
    supabase: SupabaseConfig = Field(default_factory=SupabaseConfig)
    d1: D1Config = Field(default_factory=D1Config)
    r2: R2Config = Field(default_factory=R2Config)
    pii: PiiConfig = Field(default_factory=PiiConfig)
    snapshot_retention_days: int = 30
    parallel_tasks: int = 10


def load_config(path: Path | None = None) -> AppConfig:
    """YAML 설정 파일을 로딩하고 Pydantic 모델로 검증한다."""
    config_path = path or _DEFAULT_CONFIG_PATH

    dotenv_path = config_path.parent / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)

    raw: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

    # 환경변수 오버라이드: Supabase
    raw.setdefault("supabase", {})
    if v := os.environ.get("SUPABASE_HOST"):
        raw["supabase"]["host"] = v
    if v := os.environ.get("SUPABASE_PORT"):
        raw["supabase"]["port"] = int(v)
    if v := os.environ.get("SUPABASE_DATABASE"):
        raw["supabase"]["database"] = v
    if v := os.environ.get("SUPABASE_USER"):
        raw["supabase"]["user"] = v
    if v := os.environ.get("SUPABASE_PASSWORD"):
        raw["supabase"]["password"] = v

    # 환경변수 오버라이드: D1
    raw.setdefault("d1", {})
    if v := os.environ.get("D1_DATABASE_ID"):
        raw["d1"]["database_id"] = v
    if v := os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        raw["d1"]["account_id"] = v
    if v := os.environ.get("CLOUDFLARE_API_TOKEN"):
        raw["d1"]["api_token"] = v

    # 환경변수 오버라이드: PII
    raw.setdefault("pii", {})
    if v := os.environ.get("PII_HASH_SALT"):
        raw["pii"]["hash_salt"] = v

    return AppConfig.model_validate(raw)
