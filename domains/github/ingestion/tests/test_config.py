"""설정 로딩 테스트."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from gharchive_etl.config import AppConfig, load_config
from pydantic import ValidationError


class TestLoadConfig:
    """config.yaml 로딩 테스트."""

    def test_load_valid_config(self, tmp_config_file: Path) -> None:
        config = load_config(tmp_config_file)
        assert config.target_orgs == ["pseudolab"]
        assert config.gharchive.base_url == "https://data.gharchive.org"

    def test_load_config_with_defaults(self, tmp_path: Path) -> None:
        minimal = {"target_orgs": ["pseudolab"]}
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(minimal), encoding="utf-8")

        config = load_config(config_path)
        assert config.http.download_timeout_sec == 120
        assert config.http.max_retries == 3
        assert config.r2.bucket_name == "gharchive-raw"

    def test_load_empty_config_raises(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("", encoding="utf-8")

        with pytest.raises(ValueError, match="Empty config file"):
            load_config(config_path)

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("{{invalid: yaml: content", encoding="utf-8")

        with pytest.raises(yaml.YAMLError):
            load_config(config_path)

    def test_env_override_d1(self, tmp_config_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("D1_DATABASE_ID", "env-db-id")
        config = load_config(tmp_config_file)
        assert config.d1.database_id == "env-db-id"

    def test_env_override_cloudflare_account_id(
        self, tmp_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLOUDFLARE_ACCOUNT_ID → r2.endpoint 주입 검증."""
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "abc123")
        config = load_config(tmp_config_file)
        assert config.r2.endpoint == "https://abc123.r2.cloudflarestorage.com"

    def test_env_override_cloudflare_account_id_overwrites_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """환경변수가 config.yaml의 endpoint보다 우선한다."""
        data = {
            "target_orgs": ["pseudolab"],
            "r2": {
                "bucket_name": "gharchive-raw",
                "prefix": "raw/github-archive",
                "endpoint": "https://custom.endpoint.com",
            },
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(data), encoding="utf-8")
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "abc123")

        config = load_config(config_path)
        assert config.r2.endpoint == "https://abc123.r2.cloudflarestorage.com"

    def test_env_override_without_cloudflare_account_id(
        self, tmp_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLOUDFLARE_ACCOUNT_ID 미설정 시 endpoint는 기본값 None."""
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
        config = load_config(tmp_config_file)
        assert config.r2.endpoint is None


class TestAppConfigValidation:
    """Pydantic 모델 검증 테스트."""

    def test_target_orgs_required(self) -> None:
        with pytest.raises(ValidationError):
            AppConfig.model_validate({"target_orgs": []})

    def test_target_orgs_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            AppConfig(target_orgs=[])

    def test_valid_minimal_config(self) -> None:
        config = AppConfig(target_orgs=["pseudolab"])
        assert config.target_orgs == ["pseudolab"]
        assert config.event_types == []
        assert config.exclude_repos == []

    def test_unknown_fields_ignored(self) -> None:
        data: dict[str, Any] = {
            "target_orgs": ["pseudolab"],
            "unknown_field": "should be ignored",
        }
        # Pydantic v2 기본: extra fields are ignored
        config = AppConfig.model_validate(data)
        assert config.target_orgs == ["pseudolab"]

    def test_network_config_defaults(self) -> None:
        config = AppConfig(target_orgs=["pseudolab"])
        assert config.http.download_timeout_sec == 120
        assert config.http.max_retries == 3
        assert config.http.backoff_factor == 2.0
        assert config.http.max_concurrency == 4
