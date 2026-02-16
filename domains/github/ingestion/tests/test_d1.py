"""D1 HTTP API 클라이언트 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from gharchive_etl.config import D1Config
from gharchive_etl.d1 import (
    MAX_BATCH_BYTES,
    MAX_BATCH_ROWS,
    _build_batch_insert_sql,
    _build_batches,
    _d1_query,
    _validate_d1_auth,
    insert_daily_stats,
    insert_events,
)
from gharchive_etl.transformer import DailyStatsRow, EventRow


def _make_config(**overrides: Any) -> D1Config:
    """테스트용 D1Config 헬퍼."""
    defaults = {
        "database_id": "test-db-id",
        "account_id": "test-account-id",
        "api_token": "test-api-token",
    }
    defaults.update(overrides)
    return D1Config(**defaults)


def _make_event_row(**overrides: Any) -> EventRow:
    """테스트용 EventRow 헬퍼."""
    defaults: dict[str, Any] = {
        "id": "1",
        "type": "PushEvent",
        "actor_login": "testuser",
        "repo_name": "pseudolab/test-repo",
        "org_name": "pseudolab",
        "payload": "{}",
        "created_at": "2024-01-15T10:30:00",
        "batch_date": "2024-01-15",
    }
    defaults.update(overrides)
    return defaults  # type: ignore[return-value]


def _make_daily_stats_row(**overrides: Any) -> DailyStatsRow:
    """테스트용 DailyStatsRow 헬퍼."""
    defaults: dict[str, Any] = {
        "date": "2024-01-15",
        "org_name": "pseudolab",
        "repo_name": "pseudolab/test-repo",
        "event_type": "PushEvent",
        "count": 5,
    }
    defaults.update(overrides)
    return defaults  # type: ignore[return-value]


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> httpx.Response:
    """테스트용 httpx.Response 생성."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data or {"success": True, "result": []},
        request=httpx.Request("POST", "https://api.cloudflare.com/test"),
    )
    return resp


class TestBuildBatches:
    """배치 분할 테스트."""

    def test_batch_split_by_rows(self) -> None:
        rows = [_make_event_row(id=str(i)) for i in range(MAX_BATCH_ROWS + 10)]
        columns = [
            "id",
            "type",
            "actor_login",
            "repo_name",
            "org_name",
            "payload",
            "created_at",
            "batch_date",
        ]
        batches, skipped = _build_batches(rows, columns)
        assert len(batches) == 2
        assert len(batches[0]) == MAX_BATCH_ROWS
        assert len(batches[1]) == 10
        assert skipped == 0

    def test_batch_split_by_bytes(self) -> None:
        large_payload = "x" * 10_000
        rows = [_make_event_row(id=str(i), payload=large_payload) for i in range(200)]
        columns = [
            "id",
            "type",
            "actor_login",
            "repo_name",
            "org_name",
            "payload",
            "created_at",
            "batch_date",
        ]
        batches, skipped = _build_batches(rows, columns)
        assert len(batches) > 1
        assert skipped == 0
        total_rows = sum(len(b) for b in batches)
        assert total_rows == 200

    def test_batch_single_large_row(self) -> None:
        rows = [_make_event_row(id="1", payload="x" * 100)]
        columns = [
            "id",
            "type",
            "actor_login",
            "repo_name",
            "org_name",
            "payload",
            "created_at",
            "batch_date",
        ]
        batches, skipped = _build_batches(rows, columns)
        assert len(batches) == 1
        assert len(batches[0]) == 1
        assert skipped == 0

    def test_batch_oversized_row_skipped(self) -> None:
        oversized_payload = "x" * (MAX_BATCH_BYTES + 1000)
        rows = [
            _make_event_row(id="1", payload=oversized_payload),
            _make_event_row(id="2"),
        ]
        columns = [
            "id",
            "type",
            "actor_login",
            "repo_name",
            "org_name",
            "payload",
            "created_at",
            "batch_date",
        ]
        batches, skipped = _build_batches(rows, columns)
        assert skipped == 1
        assert len(batches) == 1
        assert batches[0][0]["id"] == "2"

    def test_batch_empty_rows(self) -> None:
        columns = [
            "id",
            "type",
            "actor_login",
            "repo_name",
            "org_name",
            "payload",
            "created_at",
            "batch_date",
        ]
        batches, skipped = _build_batches([], columns)
        assert batches == []
        assert skipped == 0


class TestBuildBatchSQL:
    """SQL 생성 테스트."""

    def test_single_row_sql(self) -> None:
        sql = _build_batch_insert_sql("events", ["id", "type"], 1)
        assert sql == "INSERT OR IGNORE INTO events (id, type) VALUES (?, ?)"

    def test_multi_row_sql(self) -> None:
        sql = _build_batch_insert_sql("events", ["id", "type"], 3)
        assert sql == "INSERT OR IGNORE INTO events (id, type) VALUES (?, ?), (?, ?), (?, ?)"

    def test_params_flattening(self) -> None:
        columns = ["id", "type"]
        rows = [
            _make_event_row(id="1", type="PushEvent"),
            _make_event_row(id="2", type="IssuesEvent"),
        ]
        params: list[Any] = []
        for row in rows:
            params.extend(row[c] for c in columns)  # type: ignore[literal-required]
        assert params == ["1", "PushEvent", "2", "IssuesEvent"]


class TestValidateD1Auth:
    """인증 검증 테스트."""

    def test_valid_config(self) -> None:
        config = _make_config()
        _validate_d1_auth(config)  # should not raise

    def test_missing_account_id(self) -> None:
        config = _make_config(account_id="")
        with pytest.raises(RuntimeError, match="account_id"):
            _validate_d1_auth(config)

    def test_missing_all(self) -> None:
        config = _make_config(account_id="", database_id="", api_token="")
        with pytest.raises(RuntimeError, match="account_id"):
            _validate_d1_auth(config)


class TestD1Query:
    """D1 HTTP API 호출 테스트."""

    def test_d1_query_headers(self) -> None:
        config = _make_config()
        mock_resp = _mock_response()
        with patch("gharchive_etl.d1.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            _d1_query("SELECT 1", [], config, max_retries=0)

            call_kwargs = mock_client.post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
            assert headers["Authorization"] == "Bearer test-api-token"
            assert headers["Content-Type"] == "application/json"

    def test_d1_query_endpoint(self) -> None:
        config = _make_config(account_id="my-acct", database_id="my-db")
        mock_resp = _mock_response()
        with patch("gharchive_etl.d1.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            _d1_query("SELECT 1", [], config, max_retries=0)

            call_args = mock_client.post.call_args
            url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url")
            assert "my-acct" in url
            assert "my-db" in url
            assert url.endswith("/query")


class TestInsertEvents:
    """이벤트 적재 테스트."""

    def test_insert_success(self) -> None:
        config = _make_config()
        rows = [_make_event_row(id="1"), _make_event_row(id="2")]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            result = insert_events(rows, config)
            assert result.total_rows == 2
            assert result.rows_inserted == 2
            assert result.batches_executed == 1
            assert not result.errors

    def test_insert_batching(self) -> None:
        config = _make_config()
        rows = [_make_event_row(id=str(i)) for i in range(MAX_BATCH_ROWS + 10)]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            result = insert_events(rows, config)
            assert result.batches_executed == 2
            assert result.rows_inserted == MAX_BATCH_ROWS + 10
            assert mock_query.call_count == 2

    def test_insert_dry_run(self) -> None:
        config = _make_config()
        rows = [_make_event_row(id="1")]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            result = insert_events(rows, config, dry_run=True)
            assert result.dry_run is True
            assert result.batches_executed == 1
            assert result.rows_inserted == 0
            mock_query.assert_not_called()

    def test_insert_retry_on_5xx(self) -> None:
        config = _make_config()
        rows = [_make_event_row(id="1")]

        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            result = insert_events(rows, config)
            assert result.rows_inserted == 1

    def test_insert_no_retry_on_4xx(self) -> None:
        config = _make_config()
        rows = [_make_event_row(id="1")]

        error_resp = httpx.Response(
            status_code=400,
            request=httpx.Request("POST", "https://api.cloudflare.com/test"),
        )
        http_error = httpx.HTTPStatusError(
            "Bad Request", request=error_resp.request, response=error_resp
        )

        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.side_effect = http_error
            result = insert_events(rows, config)
            assert len(result.errors) == 1
            assert result.rows_inserted == 0

    def test_insert_empty_rows(self) -> None:
        config = _make_config()
        result = insert_events([], config)
        assert result.total_rows == 0
        assert result.rows_inserted == 0
        assert result.batches_executed == 0

    def test_insert_progress_callback(self) -> None:
        config = _make_config()
        rows = [_make_event_row(id="1"), _make_event_row(id="2")]
        progress_calls: list[tuple[int, int]] = []

        def on_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            insert_events(rows, config, on_progress=on_progress)
            assert len(progress_calls) == 1
            assert progress_calls[0] == (1, 1)

    def test_insert_auth_validation(self) -> None:
        config = _make_config(account_id="")
        rows = [_make_event_row(id="1")]
        with pytest.raises(RuntimeError, match="account_id"):
            insert_events(rows, config)


class TestInsertDailyStats:
    """일별 통계 UPSERT 테스트."""

    def test_upsert_success(self) -> None:
        config = _make_config()
        stats = [_make_daily_stats_row(), _make_daily_stats_row(event_type="IssuesEvent")]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            result = insert_daily_stats(stats, config)
            assert result.total_rows == 2
            assert result.rows_inserted == 2
            assert result.batches_executed == 2
            assert not result.errors

    def test_upsert_dry_run(self) -> None:
        config = _make_config()
        stats = [_make_daily_stats_row()]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            result = insert_daily_stats(stats, config, dry_run=True)
            assert result.dry_run is True
            assert result.rows_inserted == 0
            assert result.batches_executed == 1
            mock_query.assert_not_called()

    def test_upsert_conflict_update(self) -> None:
        config = _make_config()
        stats = [_make_daily_stats_row()]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            insert_daily_stats(stats, config)

            call_args = mock_query.call_args
            sql = call_args[0][0]
            assert "ON CONFLICT" in sql
            assert "DO UPDATE SET count=excluded.count" in sql

    def test_upsert_empty(self) -> None:
        config = _make_config()
        result = insert_daily_stats([], config)
        assert result.total_rows == 0
        assert result.batches_executed == 0
