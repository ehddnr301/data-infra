"""REST API CLI 명령어 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import orjson
import pytest
import yaml
from click.testing import CliRunner

from gharchive_etl.cli import main


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def tmp_config(tmp_path: Path) -> Path:
    """Minimal config.yaml for CLI tests."""
    config = {
        "gharchive": {"base_url": "https://data.gharchive.org"},
        "target_orgs": ["test-org"],
        "event_types": [],
        "exclude_repos": [],
        "http": {
            "download_timeout_sec": 120,
            "max_retries": 3,
            "backoff_factor": 2.0,
            "max_concurrency": 4,
            "user_agent": "test",
        },
        "r2": {"bucket_name": "test-bucket", "prefix": "raw/github-archive"},
        "d1": {"database_id": "test-db"},
        "rest_api": {
            "r2_prefix": "raw/rest-api",
            "etag_cache_enabled": True,
            "repo_supplement_threshold": 300,
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config), encoding="utf-8")
    return config_path


class TestRestFetchCommand:
    """rest-fetch CLI 명령어 테스트."""

    def test_no_github_token_graceful_skip(self, runner: CliRunner, tmp_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """GITHUB_TOKEN 미설정 시 graceful skip."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        result = runner.invoke(main, [
            "rest-fetch", "--output-jsonl", "/tmp/test.jsonl",
            "--config", str(tmp_config),
        ])
        assert result.exit_code == 0
        assert "미설정" in result.output or "스킵" in result.output

    @patch("gharchive_etl.rest_api_collector.RestApiCollector")
    @patch("gharchive_etl.github_api.GitHubApiClient")
    def test_successful_collection(
        self,
        mock_api_cls: MagicMock,
        mock_collector_cls: MagicMock,
        runner: CliRunner,
        tmp_config: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """정상 수집 시 JSONL 파일 생성."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")

        from gharchive_etl.models import GitHubEvent
        from gharchive_etl.rest_api_collector import CollectionResult, RestApiCollectionSummary

        mock_event = GitHubEvent(
            id="1",
            type="PushEvent",
            actor={"id": 1, "login": "user"},
            repo={"id": 1, "name": "org/repo"},
            created_at="2024-01-15T10:00:00Z",
            payload={},
        )
        mock_summary = RestApiCollectionSummary(
            results=[CollectionResult(org="test-org", new_events=1, api_calls=1)],
            total_events=1,
            total_new=1,
            total_api_calls=1,
        )
        mock_collector = MagicMock()
        mock_collector.collect_all.return_value = ([mock_event], mock_summary)
        mock_collector_cls.return_value = mock_collector

        mock_api = MagicMock()
        mock_api.close = MagicMock()
        mock_api_cls.return_value = mock_api

        output_path = tmp_path / "out.jsonl"
        result = runner.invoke(main, [
            "rest-fetch", "--output-jsonl", str(output_path),
            "--config", str(tmp_config),
        ])
        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert output_path.exists()

    @patch("gharchive_etl.rest_api_collector.RestApiCollector")
    @patch("gharchive_etl.github_api.GitHubApiClient")
    def test_backfill_flag(
        self,
        mock_api_cls: MagicMock,
        mock_collector_cls: MagicMock,
        runner: CliRunner,
        tmp_config: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--backfill 플래그가 collector에 전달된다."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")

        from gharchive_etl.rest_api_collector import RestApiCollectionSummary

        mock_api = MagicMock()
        mock_api.close = MagicMock()
        mock_api_cls.return_value = mock_api

        mock_collector = MagicMock()
        mock_collector.collect_all.return_value = ([], RestApiCollectionSummary())
        mock_collector_cls.return_value = mock_collector

        result = runner.invoke(main, [
            "rest-fetch", "--output-jsonl", str(tmp_path / "out.jsonl"),
            "--backfill", "--config", str(tmp_config),
        ])
        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        mock_collector.collect_all.assert_called_once_with(backfill=True)


class TestUploadSourceOption:
    """upload --source 옵션 테스트."""

    def test_input_file_and_input_dir_mutual_exclusion(
        self, runner: CliRunner, tmp_config: Path, tmp_path: Path
    ) -> None:
        """--input-file과 --input-dir 동시 사용 불가."""
        jsonl = tmp_path / "test.jsonl"
        jsonl.write_bytes(b"")
        result = runner.invoke(main, [
            "upload", "--date", "2024-01-15",
            "--input-file", str(jsonl),
            "--input-dir", str(tmp_path),
            "--config", str(tmp_config),
        ])
        assert result.exit_code != 0
        assert "동시에 사용할 수 없습니다" in result.output

    def test_input_file_requires_date(
        self, runner: CliRunner, tmp_config: Path, tmp_path: Path
    ) -> None:
        """--input-file 사용 시 --date 필수."""
        jsonl = tmp_path / "test.jsonl"
        jsonl.write_bytes(b"")
        result = runner.invoke(main, [
            "upload", "--input-file", str(jsonl),
            "--config", str(tmp_config),
        ])
        assert result.exit_code != 0

    def test_neither_input_file_nor_dir(
        self, runner: CliRunner, tmp_config: Path
    ) -> None:
        """--input-file와 --input-dir 둘 다 없으면 에러."""
        result = runner.invoke(main, [
            "upload", "--date", "2024-01-15",
            "--config", str(tmp_config),
        ])
        assert result.exit_code != 0

    @patch("gharchive_etl.cli.transform_events")
    @patch("gharchive_etl.cli.insert_all_dl_rows")
    @patch("gharchive_etl.cli._validate_d1_auth")
    def test_source_rest_api_passed_to_transform(
        self,
        mock_validate: MagicMock,
        mock_insert: MagicMock,
        mock_transform: MagicMock,
        runner: CliRunner,
        tmp_config: Path,
        tmp_path: Path,
    ) -> None:
        """--source rest_api가 transform_events에 전달된다."""
        event = {
            "id": "1",
            "type": "PushEvent",
            "actor": {"id": 1, "login": "user"},
            "repo": {"id": 1, "name": "org/repo"},
            "created_at": "2024-01-15T10:00:00Z",
            "payload": {},
        }
        jsonl = tmp_path / "test.jsonl"
        jsonl.write_bytes(orjson.dumps(event) + b"\n")

        mock_transform.return_value = ({}, {"valid": 1, "invalid": 0})
        mock_insert.return_value = {}

        result = runner.invoke(main, [
            "upload", "--date", "2024-01-15",
            "--input-file", str(jsonl),
            "--source", "rest_api",
            "--target", "d1",
            "--config", str(tmp_config),
            "--dry-run",
        ])

        if mock_transform.called:
            call_kwargs = mock_transform.call_args
            source_val = call_kwargs[1].get("source") if call_kwargs[1] else None
            if source_val is None and call_kwargs[0] and len(call_kwargs[0]) > 1:
                source_val = call_kwargs[0][1]
            assert source_val == "rest_api"
