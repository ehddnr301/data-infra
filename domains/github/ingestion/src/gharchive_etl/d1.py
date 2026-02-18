"""D1 HTTP API 클라이언트.

Cloudflare D1 HTTP API를 통해 DL 테이블 및 일별 통계를 적재한다.
- parameterized query만 사용 (SQL injection 방지)
- INSERT OR IGNORE로 멱등성 보장
- 바이트 기반 동적 배치 분할 (700KB + 동적 행 제한)
"""

from __future__ import annotations

import json
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

import httpx

from gharchive_etl.config import D1Config
from gharchive_etl.dl_models import DL_TABLE_COLUMNS, DL_TABLES, EXPLODED_TABLES, TABLE_TO_EVENT_TYPE
from gharchive_etl.transformer import DLRowsByTable, DailyStatsRow

logger = logging.getLogger(__name__)

_D1_API_BASE = "https://api.cloudflare.com/client/v4/accounts"
MAX_BATCH_BYTES = 700_000  # 700KB
# D1 HTTP API는 쿼리당 바인딩 파라미터 최대 100개 제한
# 테이블별 컬럼 수에 따라 동적 계산: floor(100 / len(columns))
MAX_BINDING_PARAMS = 100

T = TypeVar("T")


@dataclass
class D1InsertResult:
    """D1 적재 결과."""

    total_rows: int = 0
    rows_inserted: int = 0
    rows_skipped: int = 0
    batches_executed: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False


def _retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable: Callable[[Exception], bool] | None = None,
) -> T:
    """지수 백오프로 함수를 재시도한다."""
    if retryable is None:

        def retryable(e: Exception) -> bool:
            return False

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt >= max_retries or not retryable(e):
                raise
            delay = min(base_delay * (2**attempt), max_delay)
            jitter = delay * 0.2 * (2 * random.random() - 1)
            sleep_time = max(0.0, delay + jitter)
            logger.warning(
                "Retry %d/%d after %.1fs: %s",
                attempt + 1,
                max_retries,
                sleep_time,
                e,
            )
            time.sleep(sleep_time)

    raise last_exc  # type: ignore[misc]


def _is_retryable_http_error(e: Exception) -> bool:
    """재시도 가능한 HTTP 에러인지 판단한다."""
    if isinstance(e, httpx.TimeoutException):
        return True
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code >= 500 or e.response.status_code == 429
    return False


def _d1_query(
    sql: str,
    params: list[Any],
    config: D1Config,
    *,
    max_retries: int = 3,
) -> dict[str, Any]:
    """D1 HTTP API에 쿼리를 실행한다."""
    url = f"{_D1_API_BASE}/{config.account_id}/d1/database/{config.database_id}/query"
    headers = {
        "Authorization": f"Bearer {config.api_token}",
        "Content-Type": "application/json",
    }
    body = {"sql": sql, "params": params}

    def _do_request() -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    return _retry_with_backoff(
        _do_request,
        max_retries=max_retries,
        retryable=_is_retryable_http_error,
    )


def query_rows(sql: str, params: list[Any], config: D1Config) -> list[dict[str, Any]]:
    """D1에서 SELECT 결과를 dict 리스트로 반환한다."""
    resp = _d1_query(sql, params, config)
    try:
        results = resp["result"][0]["results"]
        return results if isinstance(results, list) else []
    except (KeyError, IndexError, TypeError):
        return []


def compute_daily_stats_from_dl(batch_date: str, config: D1Config) -> list[DailyStatsRow]:
    """D1에 저장된 DL 테이블 기준으로 daily_stats를 재계산한다.

    verify-aggregation과 동일한 집계 기준을 사용해 불일치를 방지한다.
    """
    counter: dict[tuple[str, str, str, str], int] = {}

    for table_name in DL_TABLES:
        event_type = TABLE_TO_EVENT_TYPE.get(table_name, table_name)
        if table_name in EXPLODED_TABLES:
            sql = (
                f"SELECT COALESCE(organization,'') AS org_name, repo_name, "
                f"COUNT(DISTINCT event_id) AS cnt FROM {table_name} "
                f"WHERE base_date = ? GROUP BY organization, repo_name"
            )
        else:
            sql = (
                f"SELECT COALESCE(organization,'') AS org_name, repo_name, "
                f"COUNT(*) AS cnt FROM {table_name} "
                f"WHERE base_date = ? GROUP BY organization, repo_name"
            )

        rows = query_rows(sql, [batch_date], config)
        for row in rows:
            key = (batch_date, row["org_name"], row["repo_name"], event_type)
            counter[key] = counter.get(key, 0) + row["cnt"]

    return [
        DailyStatsRow(date=k[0], org_name=k[1], repo_name=k[2], event_type=k[3], count=v)
        for k, v in sorted(counter.items())
    ]


def _build_batch_insert_sql(
    table: str,
    columns: list[str],
    row_count: int,
    *,
    conflict_action: str = "IGNORE",
) -> str:
    """다중 행 INSERT SQL을 생성한다."""
    cols = ", ".join(columns)
    placeholders = f"({', '.join('?' for _ in columns)})"
    values = ", ".join(placeholders for _ in range(row_count))
    return f"INSERT OR {conflict_action} INTO {table} ({cols}) VALUES {values}"


def _build_dl_batches(
    rows: list[dict[str, Any]],
    columns: list[str],
    max_rows_per_batch: int,
) -> tuple[list[list[dict[str, Any]]], int]:
    """바이트 기반으로 행을 배치로 분할한다."""
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_bytes = 0
    skipped_oversized = 0

    for row in rows:
        row_data = [row.get(c) for c in columns]
        row_bytes = len(json.dumps(row_data).encode())

        if row_bytes > MAX_BATCH_BYTES:
            logger.warning(
                "Oversized row skipped (%.1f KB): event_id=%s",
                row_bytes / 1024,
                row.get("event_id", "?"),
            )
            skipped_oversized += 1
            continue

        if current_batch and (
            current_bytes + row_bytes > MAX_BATCH_BYTES
            or len(current_batch) >= max_rows_per_batch
        ):
            batches.append(current_batch)
            current_batch = []
            current_bytes = 0

        current_batch.append(row)
        current_bytes += row_bytes

    if current_batch:
        batches.append(current_batch)

    return batches, skipped_oversized


def _validate_d1_auth(config: D1Config) -> None:
    """D1 인증 설정을 검증한다."""
    missing = []
    if not config.account_id:
        missing.append("account_id")
    if not config.database_id:
        missing.append("database_id")
    if not config.api_token:
        missing.append("api_token")
    if missing:
        raise RuntimeError(f"D1 auth config missing: {', '.join(missing)}")


def insert_dl_rows(
    table_name: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    config: D1Config,
    *,
    dry_run: bool = False,
    max_retries: int = 3,
    on_progress: Callable[[int, int], None] | None = None,
) -> D1InsertResult:
    """범용 DL 테이블 적재."""
    _validate_d1_auth(config)

    result = D1InsertResult(total_rows=len(rows), dry_run=dry_run)

    if not rows:
        return result

    # 컬럼 수 기반 동적 배치 크기 계산
    max_rows_per_batch = max(1, MAX_BINDING_PARAMS // len(columns))
    batches, skipped = _build_dl_batches(rows, columns, max_rows_per_batch)
    result.rows_skipped = skipped

    for i, batch in enumerate(batches):
        sql = _build_batch_insert_sql(table_name, columns, len(batch))
        params: list[Any] = []
        for row in batch:
            params.extend(row.get(c) for c in columns)

        if dry_run:
            logger.info(
                "Dry run batch %d/%d (%s): %d rows",
                i + 1, len(batches), table_name, len(batch),
            )
        else:
            try:
                _d1_query(sql, params, config, max_retries=max_retries)
                result.rows_inserted += len(batch)
            except Exception as e:
                error_msg = f"Batch {i + 1}/{len(batches)} ({table_name}) failed: {e}"
                result.errors.append(error_msg)
                logger.error(error_msg)

        result.batches_executed += 1

        if on_progress:
            on_progress(i + 1, len(batches))

    return result


def insert_all_dl_rows(
    rows_by_table: DLRowsByTable,
    config: D1Config,
    *,
    dry_run: bool = False,
    max_retries: int = 3,
) -> dict[str, D1InsertResult]:
    """DLRowsByTable 전체를 각 테이블에 적재한다."""
    results: dict[str, D1InsertResult] = {}
    for table_name, rows in rows_by_table.items():
        columns = DL_TABLE_COLUMNS[table_name]
        results[table_name] = insert_dl_rows(
            table_name, columns, rows, config,
            dry_run=dry_run, max_retries=max_retries,
        )
    return results


def insert_daily_stats(
    stats: list[DailyStatsRow],
    config: D1Config,
    *,
    dry_run: bool = False,
    max_retries: int = 3,
) -> D1InsertResult:
    """일별 통계를 D1에 적재한다 (DELETE + INSERT로 멱등성 보장).

    해당 날짜의 기존 행을 삭제한 뒤 새로 삽입하여,
    재실행 시 stale 행이 잔류하지 않도록 한다.
    """
    _validate_d1_auth(config)

    result = D1InsertResult(total_rows=len(stats), dry_run=dry_run)

    if not stats:
        return result

    # 해당 날짜의 기존 행 삭제 (멱등성 보장)
    dates = sorted({stat["date"] for stat in stats})  # type: ignore[literal-required]
    for d in dates:
        delete_sql = "DELETE FROM daily_stats WHERE date = ?"
        if dry_run:
            logger.info("Dry run delete: date=%s", d)
        else:
            try:
                _d1_query(delete_sql, [d], config, max_retries=max_retries)
            except Exception as e:
                error_msg = f"Delete failed for date={d}: {e}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                return result  # DELETE 실패 시 INSERT 진행 중단

    columns = ["date", "org_name", "repo_name", "event_type", "count"]

    for stat in stats:
        sql = (
            "INSERT INTO daily_stats (date, org_name, repo_name, event_type, count) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(date, org_name, repo_name, event_type) DO UPDATE SET count=excluded.count"
        )
        params: list[Any] = [stat[c] for c in columns]  # type: ignore[literal-required]

        if dry_run:
            logger.info("Dry run upsert: %s", stat)
        else:
            try:
                _d1_query(sql, params, config, max_retries=max_retries)
                result.rows_inserted += 1
            except Exception as e:
                error_msg = f"Upsert failed for {stat}: {e}"
                result.errors.append(error_msg)
                logger.error(error_msg)

        result.batches_executed += 1

    return result
