"""pseudolab-etl 테스트 공통 fixture."""

from __future__ import annotations

import pytest

from pseudolab_etl.config import AppConfig, D1Config, PiiConfig, R2Config, SupabaseConfig


@pytest.fixture()
def d1_config() -> D1Config:
    return D1Config(
        database_id="test-db-id",
        account_id="test-account-id",
        api_token="test-token",
    )


@pytest.fixture()
def supabase_config() -> SupabaseConfig:
    return SupabaseConfig(
        host="localhost",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass",
    )


@pytest.fixture()
def pii_salt() -> str:
    return "test-salt-for-unit-tests-only"


@pytest.fixture()
def app_config(d1_config: D1Config, supabase_config: SupabaseConfig, pii_salt: str) -> AppConfig:
    return AppConfig(
        supabase=supabase_config,
        d1=d1_config,
        r2=R2Config(),
        pii=PiiConfig(hash_salt=pii_salt),
    )
