"""CLI enrich 명령 통합 테스트."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from gharchive_etl.cli import main


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    config = {
        "target_orgs": ["Pseudo-Lab"],
        "r2": {"bucket_name": "test-bucket"},
        "d1": {"database_id": "test-db"},
        "github_api": {
            "token_env_var": "GITHUB_TOKEN",
            "skip_existing": False,
            "max_retries": 1,
            "backoff_factor": 0.01,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    return path


class TestEnrichCli:
    def test_no_token_graceful_skip(self, runner: CliRunner, config_file: Path) -> None:
        """GITHUB_TOKEN 미설정 시 exit 0으로 graceful skip."""
        result = runner.invoke(
            main,
            ["enrich", "--config", str(config_file)],
            env={"GITHUB_TOKEN": ""},
        )
        assert result.exit_code == 0
        assert "미설정" in result.output or "스킵" in result.output

    def test_dry_run(self, runner: CliRunner, config_file: Path) -> None:
        """--dry-run 플래그 동작 확인."""
        with (
            patch("gharchive_etl.github_api.GitHubApiClient") as mock_cls,
            patch("gharchive_etl.enrichment.enrich_priority_1") as mock_p1,
            patch("gharchive_etl.enrichment.enrich_priority_2") as mock_p2,
            patch("gharchive_etl.enrichment.enrich_priority_3") as mock_p3,
        ):
            mock_instance = MagicMock()
            mock_instance.rate_remaining = 5000
            mock_cls.return_value = mock_instance
            mock_p1.return_value = []
            mock_p2.return_value = []
            mock_p3.return_value = []

            result = runner.invoke(
                main,
                ["enrich", "--dry-run", "--config", str(config_file)],
                env={"GITHUB_TOKEN": "ghp_test"},
            )
            assert result.exit_code == 0
            assert "DRY RUN" in result.output

    def test_priority_filter(self, runner: CliRunner, config_file: Path) -> None:
        """--priority 1 → P1만 실행."""
        with (
            patch("gharchive_etl.github_api.GitHubApiClient") as mock_cls,
            patch("gharchive_etl.enrichment.enrich_priority_1") as mock_p1,
            patch("gharchive_etl.enrichment.enrich_priority_2") as mock_p2,
            patch("gharchive_etl.enrichment.enrich_priority_3") as mock_p3,
            patch("gharchive_etl.cli._check_wrangler_installed"),
        ):
            mock_instance = MagicMock()
            mock_instance.rate_remaining = 5000
            mock_cls.return_value = mock_instance
            mock_p1.return_value = []

            result = runner.invoke(
                main,
                ["enrich", "--priority", "1", "--config", str(config_file)],
                env={"GITHUB_TOKEN": "ghp_test"},
            )
            assert result.exit_code == 0
            mock_p1.assert_called_once()
            mock_p2.assert_not_called()
            mock_p3.assert_not_called()

    def test_date_filter(self, runner: CliRunner, config_file: Path) -> None:
        """--date 옵션이 base_date로 전달된다."""
        with (
            patch("gharchive_etl.github_api.GitHubApiClient") as mock_cls,
            patch("gharchive_etl.enrichment.enrich_priority_1") as mock_p1,
            patch("gharchive_etl.enrichment.enrich_priority_2") as mock_p2,
            patch("gharchive_etl.enrichment.enrich_priority_3") as mock_p3,
            patch("gharchive_etl.cli._check_wrangler_installed"),
        ):
            mock_instance = MagicMock()
            mock_instance.rate_remaining = 5000
            mock_cls.return_value = mock_instance
            mock_p1.return_value = []
            mock_p2.return_value = []
            mock_p3.return_value = []

            result = runner.invoke(
                main,
                ["enrich", "--date", "2024-01-15", "--config", str(config_file)],
                env={"GITHUB_TOKEN": "ghp_test"},
            )
            assert result.exit_code == 0
            # P1과 P2는 base_date 파라미터를 받아야 함
            _, kwargs = mock_p1.call_args
            assert kwargs.get("base_date") == "2024-01-15"
