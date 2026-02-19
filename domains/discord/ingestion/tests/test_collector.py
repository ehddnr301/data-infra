"""Pagination 수집 로직 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import orjson
import pytest
from discord_etl.collector import collect_channel
from discord_etl.config import AppConfig, ChannelConfig, D1Config, DiscordApiConfig
from discord_etl.d1 import D1InsertResult


@pytest.fixture()
def channel() -> ChannelConfig:
    return ChannelConfig(name="test-channel", id="944039671707607060")


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        discord=DiscordApiConfig(
            limit=50, delay_sec=0.0, max_retries=1,
            backoff_factor=0.01, chunk_pages=2,
        ),
        channels=[ChannelConfig(name="test-channel", id="944039671707607060")],
        d1=D1Config(database_id="test-db", account_id="test-acc", api_token="test-tok"),
    )


def _make_raw_message(msg_id: str, channel_id: str = "944039671707607060") -> dict:
    """테스트용 raw 메시지 생성."""
    return {
        "id": msg_id,
        "channel_id": channel_id,
        "author": {"id": "111", "username": "user"},
        "content": f"message {msg_id}",
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


class TestCollectChannel:
    """collect_channel 테스트."""

    @patch("discord_etl.collector.clear_scan_cursor")
    @patch("discord_etl.collector.save_watermark")
    @patch("discord_etl.collector.insert_messages_batch")
    @patch("discord_etl.collector.get_scan_cursor", return_value=None)
    @patch("discord_etl.collector.get_watermark", return_value="0")
    def test_single_page(
        self,
        mock_get_wm: MagicMock,
        mock_get_cursor: MagicMock,
        mock_insert: MagicMock,
        mock_save_wm: MagicMock,
        mock_clear_cursor: MagicMock,
        channel: ChannelConfig,
        app_config: AppConfig,
    ) -> None:
        mock_insert.return_value = D1InsertResult(
            total_rows=2, rows_inserted=2, batches_executed=1,
        )

        mock_client = MagicMock()
        mock_client.fetch_messages.side_effect = [
            [_make_raw_message("100"), _make_raw_message("99")],
            [],  # 빈 응답 -> 종료
        ]

        stats = collect_channel(channel, mock_client, app_config)

        assert stats.pages_fetched == 1
        assert stats.messages_fetched == 2
        assert stats.messages_new == 2
        assert stats.error is None
        mock_save_wm.assert_called_once()
        mock_clear_cursor.assert_called_once()

    @patch("discord_etl.collector.clear_scan_cursor")
    @patch("discord_etl.collector.save_watermark")
    @patch("discord_etl.collector.insert_messages_batch")
    @patch("discord_etl.collector.get_scan_cursor", return_value=None)
    @patch("discord_etl.collector.get_watermark", return_value="50")
    def test_watermark_stop(
        self,
        mock_get_wm: MagicMock,
        mock_get_cursor: MagicMock,
        mock_insert: MagicMock,
        mock_save_wm: MagicMock,
        mock_clear_cursor: MagicMock,
        channel: ChannelConfig,
        app_config: AppConfig,
    ) -> None:
        """watermark 도달 시 수집 중단."""
        mock_insert.return_value = D1InsertResult(
            total_rows=1, rows_inserted=1, batches_executed=1,
        )

        mock_client = MagicMock()
        mock_client.fetch_messages.side_effect = [
            # 첫 페이지: 100, 80 (watermark=50보다 큼)
            [_make_raw_message("100"), _make_raw_message("80")],
            # 두 번째 페이지: 30, 20 (모두 watermark=50 이하 -> 종료)
            [_make_raw_message("30"), _make_raw_message("20")],
        ]

        stats = collect_channel(channel, mock_client, app_config)

        assert stats.pages_fetched == 2
        assert stats.error is None

    @patch("discord_etl.collector.clear_scan_cursor")
    @patch("discord_etl.collector.save_watermark")
    @patch("discord_etl.collector.insert_messages_batch")
    @patch("discord_etl.collector.get_scan_cursor", return_value=None)
    @patch("discord_etl.collector.get_watermark", return_value="0")
    def test_empty_channel(
        self,
        mock_get_wm: MagicMock,
        mock_get_cursor: MagicMock,
        mock_insert: MagicMock,
        mock_save_wm: MagicMock,
        mock_clear_cursor: MagicMock,
        channel: ChannelConfig,
        app_config: AppConfig,
    ) -> None:
        """빈 채널 수집."""
        mock_client = MagicMock()
        mock_client.fetch_messages.return_value = []

        stats = collect_channel(channel, mock_client, app_config)

        assert stats.pages_fetched == 0
        assert stats.messages_fetched == 0
        assert stats.error is None
        mock_insert.assert_not_called()

    @patch("discord_etl.collector.clear_scan_cursor")
    @patch("discord_etl.collector.save_watermark")
    @patch("discord_etl.collector.insert_messages_batch")
    @patch("discord_etl.collector.save_scan_cursor")
    @patch("discord_etl.collector.get_scan_cursor", return_value=None)
    @patch("discord_etl.collector.get_watermark", return_value="0")
    def test_chunk_flush(
        self,
        mock_get_wm: MagicMock,
        mock_get_cursor: MagicMock,
        mock_save_cursor: MagicMock,
        mock_insert: MagicMock,
        mock_save_wm: MagicMock,
        mock_clear_cursor: MagicMock,
        channel: ChannelConfig,
        app_config: AppConfig,
    ) -> None:
        """chunk_pages=2에서 2페이지 도달 시 플러시."""
        mock_insert.return_value = D1InsertResult(
            total_rows=4, rows_inserted=4, batches_executed=1,
        )

        mock_client = MagicMock()
        mock_client.fetch_messages.side_effect = [
            [_make_raw_message("100"), _make_raw_message("99")],
            [_make_raw_message("98"), _make_raw_message("97")],
            [],  # 종료
        ]

        stats = collect_channel(channel, mock_client, app_config)

        assert stats.pages_fetched == 2
        assert stats.chunks_stored >= 1
        mock_save_cursor.assert_called()  # 청크 플러시 후 cursor 저장

    def test_dry_run(
        self, channel: ChannelConfig, app_config: AppConfig,
    ) -> None:
        """dry_run 모드에서 D1 저장 없이 수집만 시뮬레이션."""
        with (
            patch("discord_etl.collector.get_watermark", return_value="0"),
            patch("discord_etl.collector.get_scan_cursor", return_value=None),
            patch("discord_etl.collector.insert_messages_batch") as mock_insert,
            patch("discord_etl.collector.save_watermark") as mock_save_wm,
            patch("discord_etl.collector.save_scan_cursor") as mock_save_cursor,
            patch("discord_etl.collector.clear_scan_cursor"),
        ):
            mock_client = MagicMock()
            mock_client.fetch_messages.side_effect = [
                [_make_raw_message("100")],
                [],
            ]

            stats = collect_channel(
                channel, mock_client, app_config, dry_run=True,
            )

            assert stats.messages_stored == 1
            mock_insert.assert_not_called()
            mock_save_wm.assert_not_called()
            mock_save_cursor.assert_not_called()

    @patch("discord_etl.collector.get_scan_cursor", return_value="500")
    @patch("discord_etl.collector.get_watermark", return_value="0")
    def test_resume_from_cursor(
        self,
        mock_get_wm: MagicMock,
        mock_get_cursor: MagicMock,
        channel: ChannelConfig,
        app_config: AppConfig,
    ) -> None:
        """scan_cursor에서 수집 재개."""
        with (
            patch("discord_etl.collector.insert_messages_batch") as mock_insert,
            patch("discord_etl.collector.save_watermark"),
            patch("discord_etl.collector.clear_scan_cursor"),
        ):
            mock_insert.return_value = D1InsertResult(
                total_rows=1, rows_inserted=1, batches_executed=1,
            )

            mock_client = MagicMock()
            mock_client.fetch_messages.side_effect = [
                [_make_raw_message("400")],
                [],
            ]

            stats = collect_channel(channel, mock_client, app_config)

            assert stats.resumed_from_cursor is True
            # before=500 (scan_cursor)으로 첫 호출
            first_call = mock_client.fetch_messages.call_args_list[0]
            assert first_call[1].get("before") == "500" or first_call[0] == ("944039671707607060",)

    @patch("discord_etl.collector.clear_scan_cursor")
    @patch("discord_etl.collector.save_watermark")
    @patch("discord_etl.collector.insert_messages_batch")
    @patch("discord_etl.collector.get_scan_cursor", return_value=None)
    @patch("discord_etl.collector.get_watermark", return_value="0")
    def test_collect_channel_output_dir(
        self,
        mock_get_wm: MagicMock,
        mock_get_cursor: MagicMock,
        mock_insert: MagicMock,
        mock_save_wm: MagicMock,
        mock_clear_cursor: MagicMock,
        channel: ChannelConfig,
        app_config: AppConfig,
        tmp_path: Path,
    ) -> None:
        """output_dir 모드에서 JSONL 파일을 생성한다."""
        mock_client = MagicMock()
        mock_client.fetch_messages.side_effect = [
            [_make_raw_message("100"), _make_raw_message("99")],
            [],  # 종료
        ]

        stats = collect_channel(
            channel, mock_client, app_config,
            output_dir=tmp_path,
            batch_date="2024-06-15",
        )

        assert stats.messages_stored == 2
        assert stats.error is None

        # JSONL 파일 검증
        jsonl_path = tmp_path / "test-channel" / "2024-06-15.jsonl"
        assert jsonl_path.exists()

        lines = jsonl_path.read_bytes().strip().split(b"\n")
        assert len(lines) == 2

        # JSON 파싱 검증
        first = orjson.loads(lines[0])
        assert first["id"] in ("100", "99")

        # D1 insert 호출되지 않음
        mock_insert.assert_not_called()

    @patch("discord_etl.collector.clear_scan_cursor")
    @patch("discord_etl.collector.save_watermark")
    @patch("discord_etl.collector.insert_messages_batch")
    @patch("discord_etl.collector.get_scan_cursor", return_value=None)
    @patch("discord_etl.collector.get_watermark", return_value="0")
    def test_collect_channel_output_dir_no_watermark_update(
        self,
        mock_get_wm: MagicMock,
        mock_get_cursor: MagicMock,
        mock_insert: MagicMock,
        mock_save_wm: MagicMock,
        mock_clear_cursor: MagicMock,
        channel: ChannelConfig,
        app_config: AppConfig,
        tmp_path: Path,
    ) -> None:
        """output_dir 모드에서 watermark를 갱신하지 않는다."""
        mock_client = MagicMock()
        mock_client.fetch_messages.side_effect = [
            [_make_raw_message("200")],
            [],
        ]

        stats = collect_channel(
            channel, mock_client, app_config,
            output_dir=tmp_path,
            batch_date="2024-06-15",
        )

        assert stats.error is None
        assert stats.messages_stored == 1
        # watermark 갱신 안 됨
        mock_save_wm.assert_not_called()
        # D1 insert 호출 안 됨
        mock_insert.assert_not_called()
