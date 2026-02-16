"""D1 HTTP API 클라이언트.

Cloudflare D1 HTTP API를 통해 이벤트 및 일별 통계를 적재한다.
- parameterized query만 사용 (SQL injection 방지)
- INSERT OR IGNORE로 멱등성 보장 (event.id PRIMARY KEY)
- 바이트 기반 동적 배치 분할 (700KB + 500행 제한)
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
from gharchive_etl.transformer import DailyStatsRow, EventRow

logger = logging.getLogger(__name__)

_D1_API_BASE = "https://api.cloudflare.com/client/v4/accounts"
MAX_BATCH_BYTES = 700_000  # 700KB
MAX_BATCH_ROWS = 500

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


def _build_batches(
    rows: list[EventRow],
    columns: list[str],
) -> tuple[list[list[EventRow]], int]:
    """바이트 기반으로 행을 배치로 분할한다."""
    batches: list[list[EventRow]] = []
    current_batch: list[EventRow] = []
    current_bytes = 0
    skipped_oversized = 0

    for row in rows:
        row_data = [row[c] for c in columns]  # type: ignore[literal-required]
        row_bytes = len(json.dumps(row_data).encode())

        if row_bytes > MAX_BATCH_BYTES:
            logger.warning(
                "Oversized row skipped (%.1f KB): id=%s", row_bytes / 1024, row.get("id", "?")
            )
            skipped_oversized += 1
            continue

        if current_batch and (
            current_bytes + row_bytes > MAX_BATCH_BYTES or len(current_batch) >= MAX_BATCH_ROWS
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


def insert_events(
    rows: list[EventRow],
    config: D1Config,
    *,
    dry_run: bool = False,
    max_retries: int = 3,
    on_progress: Callable[[int, int], None] | None = None,
) -> D1InsertResult:
    """이벤트를 D1에 적재한다."""
    _validate_d1_auth(config)

    result = D1InsertResult(total_rows=len(rows), dry_run=dry_run)

    if not rows:
        return result

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
    result.rows_skipped = skipped

    for i, batch in enumerate(batches):
        sql = _build_batch_insert_sql("events", columns, len(batch))
        params: list[Any] = []
        for row in batch:
            params.extend(row[c] for c in columns)  # type: ignore[literal-required]

        if dry_run:
            logger.info("Dry run batch %d/%d: %d rows", i + 1, len(batches), len(batch))
        else:
            try:
                _d1_query(sql, params, config, max_retries=max_retries)
                result.rows_inserted += len(batch)
            except Exception as e:
                error_msg = f"Batch {i + 1}/{len(batches)} failed: {e}"
                result.errors.append(error_msg)
                logger.error(error_msg)

        result.batches_executed += 1

        if on_progress:
            on_progress(i + 1, len(batches))

    return result


def insert_daily_stats(
    stats: list[DailyStatsRow],
    config: D1Config,
    *,
    dry_run: bool = False,
    max_retries: int = 3,
) -> D1InsertResult:
    """일별 통계를 D1에 UPSERT한다."""
    _validate_d1_auth(config)

    result = D1InsertResult(total_rows=len(stats), dry_run=dry_run)

    if not stats:
        return result

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
