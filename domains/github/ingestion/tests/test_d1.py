"""D1 HTTP API 클라이언트 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from gharchive_etl.config import D1Config
from gharchive_etl.d1 import (
    MAX_BATCH_BYTES,
    MAX_BINDING_PARAMS,
    _build_batch_insert_sql,
    _build_dl_batches,
    _d1_query,
    _validate_d1_auth,
    compute_daily_stats_from_dl,
    insert_all_dl_rows,
    insert_daily_stats,
    insert_dl_rows,
)
from gharchive_etl.transformer import DailyStatsRow


def _make_config(**overrides: Any) -> D1Config:
    """테스트용 D1Config 헬퍼."""
    defaults = {
        "database_id": "test-db-id",
        "account_id": "test-account-id",
        "api_token": "test-api-token",
    }
    defaults.update(overrides)
    return D1Config(**defaults)


def _make_watch_row(**overrides: Any) -> dict[str, Any]:
    """테스트용 dl_watch_events 행 (6개 컬럼, 가장 단순)."""
    defaults: dict[str, Any] = {
        "event_id": "12345",
        "repo_name": "pseudolab/test-repo",
        "organization": "pseudolab",
        "user_login": "testuser",
        "ts_kst": "2024-01-15T19:30:00+09:00",
        "base_date": "2024-01-15",
    }
    defaults.update(overrides)
    return defaults


def _make_push_row(**overrides: Any) -> dict[str, Any]:
    """테스트용 dl_push_events 행 (18개 컬럼, 동적 배치 테스트용)."""
    defaults: dict[str, Any] = {
        "event_id": "12345",
        "repo_name": "pseudolab/test-repo",
        "organization": "pseudolab",
        "user_login": "testuser",
        "ref_full": "refs/heads/main",
        "ref_name": "main",
        "is_branch_ref": 1,
        "is_tag_ref": 0,
        "head_sha": "abc123",
        "before_sha": "def456",
        "commit_sha": "abc123",
        "commit_author_name": "Test User",
        "commit_author_email": "test@example.com",
        "commit_message": "test commit",
        "commit_distinct": 1,
        "commit_url": "https://github.com/...",
        "ts_kst": "2024-01-15T19:30:00+09:00",
        "base_date": "2024-01-15",
    }
    defaults.update(overrides)
    return defaults


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


# Watch 테이블: 6개 컬럼
_WATCH_COLUMNS = [
    "event_id", "repo_name", "organization", "user_login",
    "ts_kst", "base_date",
]

# Push 테이블: 18개 컬럼
_PUSH_COLUMNS = [
    "event_id", "repo_name", "organization", "user_login",
    "ref_full", "ref_name", "is_branch_ref", "is_tag_ref",
    "head_sha", "before_sha",
    "commit_sha", "commit_author_name", "commit_author_email",
    "commit_message", "commit_distinct", "commit_url",
    "ts_kst", "base_date",
]


class TestBuildDlBatches:
    """배치 분할 테스트."""

    def test_batch_split_by_max_rows(self) -> None:
        """max_rows_per_batch 기준 분할."""
        rows = [_make_watch_row(event_id=str(i)) for i in range(25)]
        max_rows = MAX_BINDING_PARAMS // len(_WATCH_COLUMNS)  # 100 // 6 = 16
        batches, skipped = _build_dl_batches(rows, _WATCH_COLUMNS, max_rows)
        assert len(batches) == 2
        assert len(batches[0]) == max_rows
        assert len(batches[1]) == 25 - max_rows
        assert skipped == 0

    def test_dynamic_batch_size_by_column_count(self) -> None:
        """컬럼 수에 따른 동적 배치 크기 계산."""
        max_watch = MAX_BINDING_PARAMS // len(_WATCH_COLUMNS)
        assert max_watch == 16  # 100 // 6

        max_push = MAX_BINDING_PARAMS // len(_PUSH_COLUMNS)
        assert max_push == 5  # 100 // 18

    def test_batch_split_by_bytes(self) -> None:
        """바이트 기반 분할."""
        large_payload = "x" * 10_000
        rows = [_make_push_row(event_id=str(i), commit_message=large_payload) for i in range(200)]
        max_rows = MAX_BINDING_PARAMS // len(_PUSH_COLUMNS)
        batches, skipped = _build_dl_batches(rows, _PUSH_COLUMNS, max_rows)
        assert len(batches) > 1
        assert skipped == 0
        total_rows = sum(len(b) for b in batches)
        assert total_rows == 200

    def test_batch_single_row(self) -> None:
        rows = [_make_watch_row(event_id="1")]
        max_rows = MAX_BINDING_PARAMS // len(_WATCH_COLUMNS)
        batches, skipped = _build_dl_batches(rows, _WATCH_COLUMNS, max_rows)
        assert len(batches) == 1
        assert len(batches[0]) == 1
        assert skipped == 0

    def test_batch_oversized_row_skipped(self) -> None:
        oversized = "x" * (MAX_BATCH_BYTES + 1000)
        rows = [
            _make_watch_row(event_id="1", user_login=oversized),
            _make_watch_row(event_id="2"),
        ]
        max_rows = MAX_BINDING_PARAMS // len(_WATCH_COLUMNS)
        batches, skipped = _build_dl_batches(rows, _WATCH_COLUMNS, max_rows)
        assert skipped == 1
        assert len(batches) == 1
        assert batches[0][0]["event_id"] == "2"

    def test_batch_empty_rows(self) -> None:
        max_rows = MAX_BINDING_PARAMS // len(_WATCH_COLUMNS)
        batches, skipped = _build_dl_batches([], _WATCH_COLUMNS, max_rows)
        assert batches == []
        assert skipped == 0


class TestBuildBatchSQL:
    """SQL 생성 테스트."""

    def test_single_row_sql(self) -> None:
        sql = _build_batch_insert_sql("dl_watch_events", ["event_id", "repo_name"], 1)
        assert sql == "INSERT OR IGNORE INTO dl_watch_events (event_id, repo_name) VALUES (?, ?)"

    def test_multi_row_sql(self) -> None:
        sql = _build_batch_insert_sql("dl_watch_events", ["event_id", "repo_name"], 3)
        assert sql == (
            "INSERT OR IGNORE INTO dl_watch_events (event_id, repo_name) "
            "VALUES (?, ?), (?, ?), (?, ?)"
        )

    def test_conflict_action_replace(self) -> None:
        sql = _build_batch_insert_sql("dl_watch_events", ["event_id"], 1, conflict_action="REPLACE")
        assert "INSERT OR REPLACE" in sql

    def test_params_flattening(self) -> None:
        columns = ["event_id", "repo_name"]
        rows = [
            _make_watch_row(event_id="1", repo_name="r1"),
            _make_watch_row(event_id="2", repo_name="r2"),
        ]
        params: list[Any] = []
        for row in rows:
            params.extend(row.get(c) for c in columns)
        assert params == ["1", "r1", "2", "r2"]


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


class TestInsertDlRows:
    """DL 테이블 적재 테스트."""

    def test_insert_success(self) -> None:
        config = _make_config()
        rows = [_make_watch_row(event_id="1"), _make_watch_row(event_id="2")]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            result = insert_dl_rows("dl_watch_events", _WATCH_COLUMNS, rows, config)
            assert result.total_rows == 2
            assert result.rows_inserted == 2
            assert result.batches_executed == 1
            assert not result.errors

    def test_insert_dynamic_batching_push(self) -> None:
        """push (18 cols) → max 5 rows/batch → 12 rows = 3 batches."""
        config = _make_config()
        rows = [_make_push_row(event_id=str(i), commit_sha=f"sha{i}") for i in range(12)]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            result = insert_dl_rows("dl_push_events", _PUSH_COLUMNS, rows, config)
            assert result.batches_executed == 3
            assert result.rows_inserted == 12
            assert mock_query.call_count == 3

    def test_insert_dynamic_batching_watch(self) -> None:
        """watch (6 cols) → max 16 rows/batch → 20 rows = 2 batches."""
        config = _make_config()
        rows = [_make_watch_row(event_id=str(i)) for i in range(20)]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            result = insert_dl_rows("dl_watch_events", _WATCH_COLUMNS, rows, config)
            assert result.batches_executed == 2
            assert result.rows_inserted == 20

    def test_insert_dry_run(self) -> None:
        config = _make_config()
        rows = [_make_watch_row(event_id="1")]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            result = insert_dl_rows(
                "dl_watch_events", _WATCH_COLUMNS, rows, config, dry_run=True
            )
            assert result.dry_run is True
            assert result.batches_executed == 1
            assert result.rows_inserted == 0
            mock_query.assert_not_called()

    def test_insert_error_handling(self) -> None:
        config = _make_config()
        rows = [_make_watch_row(event_id="1")]
        error_resp = httpx.Response(
            status_code=400,
            request=httpx.Request("POST", "https://api.cloudflare.com/test"),
        )
        http_error = httpx.HTTPStatusError(
            "Bad Request", request=error_resp.request, response=error_resp
        )
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.side_effect = http_error
            result = insert_dl_rows("dl_watch_events", _WATCH_COLUMNS, rows, config)
            assert len(result.errors) == 1
            assert result.rows_inserted == 0

    def test_insert_empty_rows(self) -> None:
        config = _make_config()
        result = insert_dl_rows("dl_watch_events", _WATCH_COLUMNS, [], config)
        assert result.total_rows == 0
        assert result.rows_inserted == 0
        assert result.batches_executed == 0

    def test_insert_progress_callback(self) -> None:
        config = _make_config()
        rows = [_make_watch_row(event_id="1"), _make_watch_row(event_id="2")]
        progress_calls: list[tuple[int, int]] = []

        def on_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            insert_dl_rows(
                "dl_watch_events", _WATCH_COLUMNS, rows, config,
                on_progress=on_progress,
            )
            assert len(progress_calls) == 1
            assert progress_calls[0] == (1, 1)

    def test_insert_auth_validation(self) -> None:
        config = _make_config(account_id="")
        rows = [_make_watch_row(event_id="1")]
        with pytest.raises(RuntimeError, match="account_id"):
            insert_dl_rows("dl_watch_events", _WATCH_COLUMNS, rows, config)


class TestInsertAllDlRows:
    """전체 DL 테이블 일괄 적재 테스트."""

    def test_insert_multiple_tables(self) -> None:
        config = _make_config()
        rows_by_table = {
            "dl_watch_events": [_make_watch_row(event_id="1")],
            "dl_push_events": [_make_push_row(event_id="2", commit_sha="sha1")],
        }
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            results = insert_all_dl_rows(rows_by_table, config)
            assert "dl_watch_events" in results
            assert "dl_push_events" in results
            assert results["dl_watch_events"].rows_inserted == 1
            assert results["dl_push_events"].rows_inserted == 1

    def test_insert_all_empty(self) -> None:
        config = _make_config()
        results = insert_all_dl_rows({}, config)
        assert results == {}

    def test_insert_all_dry_run(self) -> None:
        config = _make_config()
        rows_by_table = {
            "dl_watch_events": [_make_watch_row(event_id="1")],
        }
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            results = insert_all_dl_rows(rows_by_table, config, dry_run=True)
            assert results["dl_watch_events"].dry_run is True
            assert results["dl_watch_events"].rows_inserted == 0
            mock_query.assert_not_called()


class TestComputeDailyStatsFromDL:
    """D1 저장 기준 daily_stats 재계산 테스트."""

    def test_compute_from_db_rows(self) -> None:
        config = _make_config()

        def mock_query_rows(sql: str, params: list[Any], cfg: D1Config) -> list[dict[str, Any]]:
            if "dl_watch_events" in sql and "GROUP BY" in sql:
                return [{"org_name": "pseudolab", "repo_name": "pseudolab/repo", "cnt": 2}]
            if "dl_push_events" in sql and "GROUP BY" in sql:
                return [{"org_name": "pseudolab", "repo_name": "pseudolab/repo", "cnt": 3}]
            return []

        with patch("gharchive_etl.d1.query_rows", side_effect=mock_query_rows):
            stats = compute_daily_stats_from_dl("2024-01-15", config)

        by_type = {row["event_type"]: row["count"] for row in stats}
        assert by_type["WatchEvent"] == 2
        assert by_type["PushEvent"] == 3

    def test_compute_empty(self) -> None:
        config = _make_config()
        with patch("gharchive_etl.d1.query_rows", return_value=[]):
            stats = compute_daily_stats_from_dl("2024-01-15", config)
        assert stats == []


class TestInsertDailyStats:
    """일별 통계 DELETE + UPSERT 테스트."""

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

            # 첫 번째 호출: DELETE, 두 번째 호출: UPSERT
            assert mock_query.call_count == 2
            upsert_call = mock_query.call_args_list[1]
            sql = upsert_call[0][0]
            assert "ON CONFLICT" in sql
            assert "DO UPDATE SET count=excluded.count" in sql

    def test_upsert_empty(self) -> None:
        config = _make_config()
        result = insert_daily_stats([], config)
        assert result.total_rows == 0
        assert result.batches_executed == 0

    def test_delete_before_upsert(self) -> None:
        """DELETE가 UPSERT 이전에 호출되는지 검증."""
        config = _make_config()
        stats = [_make_daily_stats_row(date="2024-01-15")]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            insert_daily_stats(stats, config)

            assert mock_query.call_count == 2
            delete_sql = mock_query.call_args_list[0][0][0]
            delete_params = mock_query.call_args_list[0][0][1]
            assert "DELETE FROM daily_stats WHERE date = ?" in delete_sql
            assert delete_params == ["2024-01-15"]

            upsert_sql = mock_query.call_args_list[1][0][0]
            assert "INSERT INTO daily_stats" in upsert_sql

    def test_idempotent_rerun(self) -> None:
        """같은 날짜로 2회 호출 시 매번 DELETE가 실행되는지 검증."""
        config = _make_config()
        stats = [_make_daily_stats_row(date="2024-01-15")]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.return_value = {"success": True}
            insert_daily_stats(stats, config)
            insert_daily_stats(stats, config)

            # 각 호출마다 DELETE 1회 + UPSERT 1회 = 4회
            assert mock_query.call_count == 4
            # 첫 번째 호출의 DELETE
            assert "DELETE" in mock_query.call_args_list[0][0][0]
            # 두 번째 호출의 DELETE
            assert "DELETE" in mock_query.call_args_list[2][0][0]

    def test_delete_failure_aborts_insert(self) -> None:
        """DELETE 실패 시 INSERT가 진행되지 않는지 검증."""
        config = _make_config()
        stats = [_make_daily_stats_row()]
        with patch("gharchive_etl.d1._d1_query") as mock_query:
            mock_query.side_effect = RuntimeError("D1 error")
            result = insert_daily_stats(stats, config)
            assert len(result.errors) == 1
            assert result.rows_inserted == 0
            assert mock_query.call_count == 1  # DELETE만 호출됨
