"""D1 HTTP API 클라이언트 (Discord 메시지 저장 + watermark 관리).

GitHub ETL d1.py 패턴:
- parameterized query (SQL injection 방지)
- INSERT OR IGNORE (멱등성)
- 바이트 기반 배치 분할 (700KB)
- 지수 백오프 재시도
"""

from __future__ import annotations

import json
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar

import httpx

from discord_etl.config import D1Config
from discord_etl.models import (
    DISCORD_MESSAGES_COLUMNS,
    DISCORD_MESSAGES_TABLE,
    DiscordMessage,
)

logger = logging.getLogger(__name__)

_D1_API_BASE = "https://api.cloudflare.com/client/v4/accounts"
MAX_BATCH_BYTES = 700_000
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
                attempt + 1, max_retries, sleep_time, e,
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


# ── Watermark 관리 ──────────────────────────────────────


def get_watermark(channel_id: str, config: D1Config) -> str:
    """채널별 last_message_id를 조회한다 (없으면 '0')."""
    rows = query_rows(
        "SELECT last_message_id FROM discord_watermarks WHERE channel_id = ?",
        [channel_id], config,
    )
    return rows[0]["last_message_id"] if rows else "0"


def save_watermark(
    channel_id: str,
    message_id: str,
    config: D1Config,
    *,
    channel_name: str = "",
    total_collected: int = 0,
) -> None:
    """watermark를 UPSERT한다 (027 스키마)."""
    now = datetime.now(tz=UTC).isoformat()
    _d1_query(
        "INSERT INTO discord_watermarks "
        "(channel_id, channel_name, last_message_id, last_collected_at, total_collected) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(channel_id) DO UPDATE SET "
        "channel_name = excluded.channel_name, "
        "last_message_id = excluded.last_message_id, "
        "last_collected_at = excluded.last_collected_at, "
        "total_collected = excluded.total_collected",
        [channel_id, channel_name, message_id, now, total_collected],
        config,
    )


# ── Scan Cursor 관리 ────────────────────────────────────


def get_scan_cursor(channel_id: str, config: D1Config) -> str | None:
    """scan_cursor를 조회한다."""
    rows = query_rows(
        "SELECT scan_cursor FROM discord_watermarks WHERE channel_id = ?",
        [channel_id], config,
    )
    if rows and rows[0].get("scan_cursor"):
        return rows[0]["scan_cursor"]
    return None


def save_scan_cursor(channel_id: str, cursor: str, config: D1Config) -> None:
    """scan_cursor를 UPDATE한다."""
    _d1_query(
        "UPDATE discord_watermarks SET scan_cursor = ?, last_collected_at = ? "
        "WHERE channel_id = ?",
        [cursor, datetime.now(tz=UTC).isoformat(), channel_id],
        config,
    )


def clear_scan_cursor(channel_id: str, config: D1Config) -> None:
    """scan_cursor를 NULL로 클리어한다."""
    _d1_query(
        "UPDATE discord_watermarks SET scan_cursor = NULL, last_collected_at = ? "
        "WHERE channel_id = ?",
        [datetime.now(tz=UTC).isoformat(), channel_id],
        config,
    )


# ── 메시지 배치 INSERT ──────────────────────────────────


def _build_batch_insert_sql(
    table: str,
    columns: list[str],
    row_count: int,
) -> str:
    """다중 행 INSERT OR IGNORE SQL을 생성한다."""
    cols = ", ".join(columns)
    placeholders = f"({', '.join('?' for _ in columns)})"
    values = ", ".join(placeholders for _ in range(row_count))
    return f"INSERT OR IGNORE INTO {table} ({cols}) VALUES {values}"


def _build_message_batches(
    rows: list[dict[str, Any]],
    columns: list[str],
    max_rows_per_batch: int,
) -> list[list[dict[str, Any]]]:
    """바이트 기반으로 행을 배치로 분할한다."""
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_bytes = 0

    for row in rows:
        row_data = [row.get(c) for c in columns]
        row_bytes = len(json.dumps(row_data).encode())

        if row_bytes > MAX_BATCH_BYTES:
            logger.warning(
                "Oversized row skipped (%.1f KB): id=%s",
                row_bytes / 1024,
                row.get("id", "?"),
            )
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

    return batches


def insert_messages_batch(
    messages: list[DiscordMessage],
    config: D1Config,
) -> D1InsertResult:
    """메시지 리스트를 D1에 배치 INSERT OR IGNORE한다."""
    result = D1InsertResult(total_rows=len(messages))

    if not messages:
        return result

    rows = [msg.to_d1_row() for msg in messages]
    columns = DISCORD_MESSAGES_COLUMNS

    max_rows_per_batch = max(1, MAX_BINDING_PARAMS // len(columns))
    batches = _build_message_batches(rows, columns, max_rows_per_batch)

    for i, batch in enumerate(batches):
        sql = _build_batch_insert_sql(DISCORD_MESSAGES_TABLE, columns, len(batch))
        params: list[Any] = []
        for row in batch:
            params.extend(row.get(c) for c in columns)

        try:
            _d1_query(sql, params, config)
            result.rows_inserted += len(batch)
        except Exception as e:
            error_msg = f"Batch {i + 1}/{len(batches)} failed: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)

        result.batches_executed += 1

    return result
