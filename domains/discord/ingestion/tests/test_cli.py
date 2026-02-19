"""CLI 통합 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import orjson
import pytest
from click.testing import CliRunner
from discord_etl.cli import main
from discord_etl.collector import CollectStats


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


class TestFetchCommand:
    """fetch 명령 테스트."""

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    @patch("discord_etl.cli.collect_channel")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_fetch_success(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_collect: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="test", id="123")],
            d1=D1Config(),
        )
        mock_collect.return_value = CollectStats(
            channel_name="test", channel_id="123",
            messages_fetched=10, messages_new=5, messages_stored=5,
        )

        result = runner.invoke(main, ["fetch", "--config", str(tmp_config_file)])

        assert result.exit_code == 0
        mock_collect.assert_called_once()

    @patch("discord_etl.cli.collect_channel")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_fetch_with_channel_id(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_collect: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[
                ChannelConfig(name="ch1", id="111"),
                ChannelConfig(name="ch2", id="222"),
            ],
            d1=D1Config(),
        )
        mock_collect.return_value = CollectStats(
            channel_name="ch2", channel_id="222",
        )

        result = runner.invoke(
            main, ["fetch", "--config", str(tmp_config_file), "--channel-id", "222"],
        )

        assert result.exit_code == 0
        mock_collect.assert_called_once()
        call_args = mock_collect.call_args
        assert call_args[0][0].id == "222"

    @patch("discord_etl.cli.collect_channel")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_fetch_invalid_channel_id(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_collect: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="ch1", id="111")],
            d1=D1Config(),
        )

        result = runner.invoke(
            main, ["fetch", "--config", str(tmp_config_file), "--channel-id", "999"],
        )

        assert result.exit_code != 0

    @patch("discord_etl.cli.collect_channel")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_fetch_with_error_exit_code(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_collect: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="test", id="123")],
            d1=D1Config(),
        )
        mock_collect.return_value = CollectStats(
            channel_name="test", channel_id="123",
            error="API error",
        )

        result = runner.invoke(main, ["fetch", "--config", str(tmp_config_file)])

        assert result.exit_code == 1

    @patch("discord_etl.cli.collect_channel")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_fetch_dry_run(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_collect: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="test", id="123")],
            d1=D1Config(),
        )
        mock_collect.return_value = CollectStats(
            channel_name="test", channel_id="123",
        )

        result = runner.invoke(
            main, ["fetch", "--config", str(tmp_config_file), "--dry-run"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_collect.call_args[1]
        assert call_kwargs["dry_run"] is True

    @patch("discord_etl.cli.collect_channel")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_fetch_with_output_dir(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_collect: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
        tmp_path: Path,
    ) -> None:
        """fetch --output-dir 옵션이 collect_channel에 전달된다."""
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="test", id="123")],
            d1=D1Config(),
        )
        mock_collect.return_value = CollectStats(
            channel_name="test", channel_id="123",
        )

        out_dir = tmp_path / "output"
        result = runner.invoke(
            main, ["fetch", "--config", str(tmp_config_file), "--output-dir", str(out_dir)],
        )

        assert result.exit_code == 0
        call_kwargs = mock_collect.call_args[1]
        assert call_kwargs["output_dir"] == out_dir


def _make_jsonl_fixture(tmp_path: Path, channel_name: str, date: str) -> Path:
    """테스트용 JSONL 파일 생성."""
    channel_dir = tmp_path / channel_name
    channel_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = channel_dir / f"{date}.jsonl"
    raw_msg = {
        "id": "100",
        "channel_id": "944039671707607060",
        "author": {"id": "111", "username": "user"},
        "content": "hello",
        "timestamp": "2024-06-15T10:30:00.000000+00:00",
        "edited_timestamp": None,
        "type": 0,
        "referenced_message": None,
        "attachments": [],
        "embeds": [],
        "reactions": [],
        "mentions": [],
        "pinned": False,
    }
    jsonl_path.write_bytes(orjson.dumps(raw_msg) + b"\n")
    return jsonl_path


class TestUploadCommand:
    """upload 명령 테스트."""

    @patch("discord_etl.cli.save_watermark")
    @patch("discord_etl.cli.insert_messages_batch")
    @patch("discord_etl.cli.upload_to_r2", return_value=True)
    @patch("discord_etl.cli.load_config")
    def test_upload_all(
        self,
        mock_load_config: MagicMock,
        mock_r2: MagicMock,
        mock_insert: MagicMock,
        mock_save_wm: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
        tmp_path: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig
        from discord_etl.d1 import D1InsertResult

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="test-channel", id="123")],
            d1=D1Config(),
        )
        mock_insert.return_value = D1InsertResult(
            total_rows=1, rows_inserted=1, batches_executed=1,
        )

        _make_jsonl_fixture(tmp_path, "test-channel", "2024-06-15")

        result = runner.invoke(main, [
            "upload", "--date", "2024-06-15",
            "--input-dir", str(tmp_path),
            "--target", "all",
            "--config", str(tmp_config_file),
        ])

        assert result.exit_code == 0
        mock_r2.assert_called_once()
        mock_insert.assert_called_once()
        mock_save_wm.assert_called_once()

    @patch("discord_etl.cli.upload_to_r2", return_value=True)
    @patch("discord_etl.cli.load_config")
    def test_upload_r2(
        self,
        mock_load_config: MagicMock,
        mock_r2: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
        tmp_path: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="test-channel", id="123")],
            d1=D1Config(),
        )

        _make_jsonl_fixture(tmp_path, "test-channel", "2024-06-15")

        result = runner.invoke(main, [
            "upload", "--date", "2024-06-15",
            "--input-dir", str(tmp_path),
            "--target", "r2",
            "--config", str(tmp_config_file),
        ])

        assert result.exit_code == 0
        mock_r2.assert_called_once()

    @patch("discord_etl.cli.save_watermark")
    @patch("discord_etl.cli.insert_messages_batch")
    @patch("discord_etl.cli.load_config")
    def test_upload_d1(
        self,
        mock_load_config: MagicMock,
        mock_insert: MagicMock,
        mock_save_wm: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
        tmp_path: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig
        from discord_etl.d1 import D1InsertResult

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="test-channel", id="123")],
            d1=D1Config(),
        )
        mock_insert.return_value = D1InsertResult(
            total_rows=1, rows_inserted=1, batches_executed=1,
        )

        _make_jsonl_fixture(tmp_path, "test-channel", "2024-06-15")

        result = runner.invoke(main, [
            "upload", "--date", "2024-06-15",
            "--input-dir", str(tmp_path),
            "--target", "d1",
            "--config", str(tmp_config_file),
        ])

        assert result.exit_code == 0
        mock_insert.assert_called_once()
        mock_save_wm.assert_called_once()


class TestQualityCheckCommand:
    """quality-check 명령 테스트."""

    @patch("discord_etl.cli.query_rows")
    @patch("discord_etl.cli.load_config")
    def test_quality_check_pass(
        self,
        mock_load_config: MagicMock,
        mock_query: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="test", id="123")],
            d1=D1Config(),
        )
        # 첫 호출: message count, 두 번째: watermark
        mock_query.side_effect = [
            [{"channel_name": "test-channel", "cnt": 10}],
            [{"channel_id": "123", "channel_name": "test-channel", "last_message_id": "100"}],
        ]

        result = runner.invoke(main, [
            "quality-check", "--date", "2024-06-15",
            "--config", str(tmp_config_file),
        ])

        assert result.exit_code == 0
        assert "Quality check passed" in result.output

    @patch("discord_etl.cli.query_rows")
    @patch("discord_etl.cli.load_config")
    def test_quality_check_fail(
        self,
        mock_load_config: MagicMock,
        mock_query: MagicMock,
        runner: CliRunner,
        tmp_config_file: Path,
    ) -> None:
        from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig

        mock_load_config.return_value = AppConfig(
            discord=DiscordApiConfig(),
            channels=[ChannelConfig(name="test", id="123")],
            d1=D1Config(),
        )
        # 빈 결과 -> fail
        mock_query.return_value = []

        result = runner.invoke(main, [
            "quality-check", "--date", "2024-06-15",
            "--config", str(tmp_config_file),
        ])

        assert result.exit_code == 1
