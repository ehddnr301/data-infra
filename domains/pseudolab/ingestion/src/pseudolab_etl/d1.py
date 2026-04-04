"""D1 HTTP API 클라이언트 — DELETE + INSERT 멱등성.

Cloudflare D1 HTTP API를 통해 dl_* 테이블을 적재한다.
- parameterized query만 사용 (SQL injection 방지)
- DELETE WHERE base_date = ? → INSERT로 멱등성 보장
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

from pseudolab_etl.config import D1Config

logger = logging.getLogger(__name__)

_D1_API_BASE = "https://api.cloudflare.com/client/v4/accounts"
MAX_BATCH_BYTES = 700_000
MAX_BINDING_PARAMS = 100

T = TypeVar("T")


@dataclass
class D1InsertResult:
    """D1 적재 결과."""

    table_name: str = ""
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
                "Retry %d/%d after %.1fs: %s", attempt + 1, max_retries, sleep_time, e,
            )
            time.sleep(sleep_time)

    raise last_exc  # type: ignore[misc]


def _is_retryable_http_error(e: Exception) -> bool:
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
            return resp.json()

    return _retry_with_backoff(
        _do_request, max_retries=max_retries, retryable=_is_retryable_http_error,
    )


def query_rows(sql: str, params: list[Any], config: D1Config) -> list[dict[str, Any]]:
    """D1에서 SELECT 결과를 dict 리스트로 반환한다."""
    resp = _d1_query(sql, params, config)
    try:
        results = resp["result"][0]["results"]
        return results if isinstance(results, list) else []
    except (KeyError, IndexError, TypeError):
        return []


def _validate_d1_auth(config: D1Config) -> None:
    missing = []
    if not config.account_id:
        missing.append("account_id")
    if not config.database_id:
        missing.append("database_id")
    if not config.api_token:
        missing.append("api_token")
    if missing:
        raise RuntimeError(f"D1 auth config missing: {', '.join(missing)}")


def _build_batch_insert_sql(table: str, columns: list[str], row_count: int) -> str:
    """다중 행 INSERT SQL을 생성한다."""
    cols = ", ".join(columns)
    placeholders = f"({', '.join('?' for _ in columns)})"
    values = ", ".join(placeholders for _ in range(row_count))
    return f"INSERT INTO {table} ({cols}) VALUES {values}"


def _build_batches(
    rows: list[dict[str, Any]],
    columns: list[str],
    max_rows_per_batch: int,
) -> tuple[list[list[dict[str, Any]]], int]:
    """바이트 기반으로 행을 배치로 분할한다."""
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_bytes = 0
    skipped = 0

    for row in rows:
        row_data = [row.get(c) for c in columns]
        row_bytes = len(json.dumps(row_data).encode())

        if row_bytes > MAX_BATCH_BYTES:
            logger.warning("Oversized row skipped (%.1f KB)", row_bytes / 1024)
            skipped += 1
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

    return batches, skipped


def delete_by_base_date(
    dl_table: str,
    base_date: str,
    config: D1Config,
    *,
    dry_run: bool = False,
    max_retries: int = 3,
) -> None:
    """base_date 기준으로 기존 행을 삭제한다 (멱등성 보장)."""
    sql = f"DELETE FROM {dl_table} WHERE base_date = ?"
    if dry_run:
        logger.info("Dry run DELETE: %s WHERE base_date = %s", dl_table, base_date)
        return
    _d1_query(sql, [base_date], config, max_retries=max_retries)
    logger.info("Deleted existing rows: %s WHERE base_date = %s", dl_table, base_date)


def insert_table_rows(
    dl_table: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    base_date: str,
    config: D1Config,
    *,
    dry_run: bool = False,
    max_retries: int = 3,
) -> D1InsertResult:
    """테이블 행을 D1에 적재한다 (DELETE + INSERT 멱등성)."""
    _validate_d1_auth(config)

    result = D1InsertResult(
        table_name=dl_table, total_rows=len(rows), dry_run=dry_run,
    )

    # 1. 기존 행 삭제
    try:
        delete_by_base_date(dl_table, base_date, config, dry_run=dry_run, max_retries=max_retries)
    except Exception as e:
        error_msg = f"DELETE failed for {dl_table}: {e}"
        result.errors.append(error_msg)
        logger.error(error_msg)
        return result

    if not rows:
        return result

    # 2. 행 삽입
    max_rows_per_batch = max(1, MAX_BINDING_PARAMS // len(columns))
    batches, skipped = _build_batches(rows, columns, max_rows_per_batch)
    result.rows_skipped = skipped

    for i, batch in enumerate(batches):
        sql = _build_batch_insert_sql(dl_table, columns, len(batch))
        params: list[Any] = []
        for row in batch:
            params.extend(row.get(c) for c in columns)

        if dry_run:
            logger.info(
                "Dry run batch %d/%d (%s): %d rows",
                i + 1, len(batches), dl_table, len(batch),
            )
        else:
            try:
                _d1_query(sql, params, config, max_retries=max_retries)
                result.rows_inserted += len(batch)
            except Exception as e:
                error_msg = f"Batch {i + 1}/{len(batches)} ({dl_table}) failed: {e}"
                result.errors.append(error_msg)
                logger.error(error_msg)

        result.batches_executed += 1

    return result
