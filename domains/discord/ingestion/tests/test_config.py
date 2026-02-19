"""설정 로딩 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from discord_etl.config import load_config


class TestLoadConfig:
    """load_config 함수 테스트."""

    def test_normal_loading(self, tmp_config_file: Path) -> None:
        config = load_config(tmp_config_file)

        assert config.discord.limit == 50
        assert len(config.channels) == 1
        assert config.channels[0].name == "test-channel"
        assert config.channels[0].id == "944039671707607060"

    def test_empty_channels_error(self, tmp_path: Path) -> None:
        data = {
            "discord": {"limit": 50},
            "channels": [],
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(data), encoding="utf-8")

        with pytest.raises((ValueError, Exception)):
            load_config(config_path)

    def test_empty_file_error(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("", encoding="utf-8")

        with pytest.raises(ValueError, match="Empty config file"):
            load_config(config_path)

    def test_env_override_d1(
        self, tmp_config_file: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("D1_DATABASE_ID", "env-db-id")
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "env-account-id")
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "env-api-token")

        config = load_config(tmp_config_file)

        assert config.d1.database_id == "env-db-id"
        assert config.d1.account_id == "env-account-id"
        assert config.d1.api_token == "env-api-token"

    def test_limit_range_validation(self, tmp_path: Path) -> None:
        data = {
            "discord": {"limit": 200},  # 최대 100 초과
            "channels": [{"name": "test", "id": "123"}],
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(data), encoding="utf-8")

        with pytest.raises((ValueError, Exception)):
            load_config(config_path)

    def test_default_values(self, tmp_path: Path) -> None:
        data = {
            "channels": [{"name": "test", "id": "123"}],
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(data), encoding="utf-8")

        config = load_config(config_path)

        assert config.discord.api_base == "https://discord.com/api/v9"
        assert config.discord.limit == 50
        assert config.discord.delay_sec == 1.0
        assert config.discord.max_retries == 3
