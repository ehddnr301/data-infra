"""D1 저장 + watermark 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from discord_etl.config import D1Config
from discord_etl.d1 import (
    _build_batch_insert_sql,
    _build_message_batches,
    clear_scan_cursor,
    get_scan_cursor,
    get_watermark,
    insert_messages_batch,
    save_scan_cursor,
    save_watermark,
)
from discord_etl.models import DiscordMessage


@pytest.fixture()
def d1_config() -> D1Config:
    return D1Config(
        database_id="test-db",
        account_id="test-account",
        api_token="test-token",
    )


class TestBuildBatchInsertSql:
    """INSERT SQL 생성 테스트."""

    def test_single_row(self) -> None:
        sql = _build_batch_insert_sql("test_table", ["a", "b", "c"], 1)
        assert sql == "INSERT OR IGNORE INTO test_table (a, b, c) VALUES (?, ?, ?)"

    def test_multiple_rows(self) -> None:
        sql = _build_batch_insert_sql("test_table", ["a", "b"], 3)
        assert sql == (
            "INSERT OR IGNORE INTO test_table (a, b) VALUES (?, ?), (?, ?), (?, ?)"
        )


class TestBuildMessageBatches:
    """배치 분할 테스트."""

    def test_single_batch(self) -> None:
        rows = [{"a": "x", "b": "y"} for _ in range(3)]
        batches = _build_message_batches(rows, ["a", "b"], max_rows_per_batch=10)
        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_split_by_max_rows(self) -> None:
        rows = [{"a": "x", "b": "y"} for _ in range(5)]
        batches = _build_message_batches(rows, ["a", "b"], max_rows_per_batch=2)
        assert len(batches) == 3  # 2 + 2 + 1
        assert len(batches[0]) == 2
        assert len(batches[2]) == 1

    def test_empty_rows(self) -> None:
        batches = _build_message_batches([], ["a", "b"], max_rows_per_batch=10)
        assert batches == []


class TestWatermark:
    """watermark CRUD 테스트."""

    @patch("discord_etl.d1.query_rows")
    def test_get_watermark_exists(self, mock_query: MagicMock, d1_config: D1Config) -> None:
        mock_query.return_value = [{"last_message_id": "999"}]

        result = get_watermark("ch-1", d1_config)
        assert result == "999"

    @patch("discord_etl.d1.query_rows")
    def test_get_watermark_not_exists(self, mock_query: MagicMock, d1_config: D1Config) -> None:
        mock_query.return_value = []

        result = get_watermark("ch-1", d1_config)
        assert result == "0"

    @patch("discord_etl.d1._d1_query")
    def test_save_watermark(self, mock_query: MagicMock, d1_config: D1Config) -> None:
        save_watermark("ch-1", "12345", d1_config, channel_name="공지사항", total_collected=10)

        mock_query.assert_called_once()
        call_args = mock_query.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "INSERT INTO discord_watermarks" in sql
        assert "channel_name" in sql
        assert "last_collected_at" in sql
        assert "total_collected" in sql
        assert "ON CONFLICT(channel_id) DO UPDATE" in sql
        assert "ch-1" in params
        assert "12345" in params
        assert "공지사항" in params
        assert 10 in params

    @patch("discord_etl.d1._d1_query")
    def test_save_watermark_defaults(self, mock_query: MagicMock, d1_config: D1Config) -> None:
        save_watermark("ch-1", "12345", d1_config)

        mock_query.assert_called_once()
        call_args = mock_query.call_args
        params = call_args[0][1]
        assert "" in params  # default channel_name
        assert 0 in params   # default total_collected


class TestScanCursor:
    """scan_cursor CRUD 테스트."""

    @patch("discord_etl.d1.query_rows")
    def test_get_scan_cursor_exists(self, mock_query: MagicMock, d1_config: D1Config) -> None:
        mock_query.return_value = [{"scan_cursor": "cursor-abc"}]

        result = get_scan_cursor("ch-1", d1_config)
        assert result == "cursor-abc"

    @patch("discord_etl.d1.query_rows")
    def test_get_scan_cursor_none(self, mock_query: MagicMock, d1_config: D1Config) -> None:
        mock_query.return_value = [{"scan_cursor": None}]

        result = get_scan_cursor("ch-1", d1_config)
        assert result is None

    @patch("discord_etl.d1.query_rows")
    def test_get_scan_cursor_no_row(self, mock_query: MagicMock, d1_config: D1Config) -> None:
        mock_query.return_value = []

        result = get_scan_cursor("ch-1", d1_config)
        assert result is None

    @patch("discord_etl.d1._d1_query")
    def test_save_scan_cursor(self, mock_query: MagicMock, d1_config: D1Config) -> None:
        save_scan_cursor("ch-1", "cursor-xyz", d1_config)

        mock_query.assert_called_once()
        call_args = mock_query.call_args
        assert "UPDATE discord_watermarks SET scan_cursor" in call_args[0][0]
        assert "last_collected_at" in call_args[0][0]

    @patch("discord_etl.d1._d1_query")
    def test_clear_scan_cursor(self, mock_query: MagicMock, d1_config: D1Config) -> None:
        clear_scan_cursor("ch-1", d1_config)

        mock_query.assert_called_once()
        call_args = mock_query.call_args
        assert "scan_cursor = NULL" in call_args[0][0]
        assert "last_collected_at" in call_args[0][0]


class TestInsertMessagesBatch:
    """메시지 배치 INSERT 테스트."""

    @patch("discord_etl.d1._d1_query")
    def test_insert_messages(
        self, mock_query: MagicMock, d1_config: D1Config, sample_discord_message: dict,
    ) -> None:
        msg = DiscordMessage.from_api_response(
            sample_discord_message, channel_name="테스트", batch_date="2024-06-15",
        )
        result = insert_messages_batch([msg], d1_config)

        assert result.total_rows == 1
        assert result.rows_inserted == 1
        assert result.batches_executed == 1
        assert not result.errors

    def test_insert_empty(self, d1_config: D1Config) -> None:
        result = insert_messages_batch([], d1_config)

        assert result.total_rows == 0
        assert result.rows_inserted == 0

    @patch("discord_etl.d1._d1_query", side_effect=Exception("D1 error"))
    def test_insert_error(
        self, mock_query: MagicMock, d1_config: D1Config, sample_discord_message: dict,
    ) -> None:
        msg = DiscordMessage.from_api_response(
            sample_discord_message, channel_name="테스트", batch_date="2024-06-15",
        )
        result = insert_messages_batch([msg], d1_config)

        assert result.rows_inserted == 0
        assert len(result.errors) == 1
        assert "D1 error" in result.errors[0]
