from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import orjson
import yaml
from click.testing import CliRunner

from gharchive_etl.catalog_sync import SyncSummary
from gharchive_etl.cli import main


def _write_config(tmp_path: Path) -> Path:
    config_data = {
        "gharchive": {"base_url": "https://data.gharchive.org"},
        "target_orgs": ["pseudolab"],
        "event_types": [],
        "exclude_repos": [],
        "http": {
            "download_timeout_sec": 10,
            "max_retries": 1,
            "backoff_factor": 0.01,
            "max_concurrency": 1,
            "user_agent": "test/1.0",
        },
        "r2": {"bucket_name": "test-bucket", "prefix": "raw/github-archive"},
        "d1": {
            "database_id": "test-db-id",
            "account_id": "test-account-id",
            "api_token": "test-api-token",
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config_data), encoding="utf-8")
    return config_path


def test_sync_catalog_dry_run_success(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    status_file = tmp_path / "status.json"
    runner = CliRunner()

    with patch(
        "gharchive_etl.cli.run_catalog_sync",
        return_value=SyncSummary(datasets_total=2, datasets_succeeded=2),
    ):
        result = runner.invoke(
            main,
            [
                "sync-catalog",
                "--date",
                "2025-01-15",
                "--dry-run",
                "--status-file",
                str(status_file),
                "--config",
                str(config_path),
                "--no-json-log",
            ],
            env={"CATALOG_API_BASE_URL": "http://example.com/api"},
        )

    assert result.exit_code == 0
    assert "errors=0" in result.output
    assert status_file.exists()

    payload = orjson.loads(status_file.read_bytes())
    assert payload["datasets_total"] == 2
    assert payload["datasets_succeeded"] == 2
    assert payload["errors"] == []


def test_sync_catalog_missing_env_is_soft_fail(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "sync-catalog",
            "--date",
            "2025-01-15",
            "--config",
            str(config_path),
            "--no-json-log",
        ],
    )

    assert result.exit_code == 0
    assert "CATALOG_API_BASE_URL is not set" in result.output
    assert "CATALOG_API_TOKEN is not set" in result.output


def test_sync_catalog_execution_exception_is_soft_fail(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    with patch("gharchive_etl.cli.run_catalog_sync", side_effect=RuntimeError("boom")):
        result = runner.invoke(
            main,
            [
                "sync-catalog",
                "--date",
                "2025-01-15",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
            env={
                "CATALOG_API_BASE_URL": "http://example.com/api",
                "CATALOG_API_TOKEN": "token",
            },
        )

    assert result.exit_code == 0
    assert "sync-catalog execution error: boom" in result.output


def test_sync_catalog_invalid_date_is_soft_fail(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "sync-catalog",
            "--date",
            "2025-99-99",
            "--config",
            str(config_path),
            "--no-json-log",
        ],
        env={
            "CATALOG_API_BASE_URL": "http://example.com/api",
            "CATALOG_API_TOKEN": "token",
        },
    )

    assert result.exit_code == 0
    assert "sync-catalog execution error:" in result.output
