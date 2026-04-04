"""Supabase PostgreSQL 데이터 추출기."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
import psycopg2.extras

from pseudolab_etl.config import SupabaseConfig
from pseudolab_etl.table_registry import TableDef
from pseudolab_etl.type_mapping import convert_value

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def get_connection(config: SupabaseConfig) -> psycopg2.extensions.connection:
    """Supabase PostgreSQL 연결을 생성한다."""
    return psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.user,
        password=config.password,
        sslmode=config.sslmode,
        options="-c statement_timeout=120000",  # 2분 타임아웃
    )


def _kst_boundaries(base_date: str) -> tuple[str, str]:
    """KST 기준일의 UTC 시작/종료 시각을 반환한다.

    base_date '2026-04-03' →
      start: '2026-04-02T15:00:00+00:00' (KST 0시 = UTC 전날 15시)
      end:   '2026-04-03T15:00:00+00:00' (KST 다음날 0시)
    """
    dt = datetime.strptime(base_date, "%Y-%m-%d")
    kst_start = dt.replace(tzinfo=KST)
    utc_start = kst_start.astimezone(timezone.utc)
    utc_end = utc_start + timedelta(days=1)
    return utc_start.isoformat(), utc_end.isoformat()


def _convert_row(row: dict[str, Any], table: TableDef) -> dict[str, Any]:
    """행의 값을 D1 호환 타입으로 변환한다."""
    col_types = {c.name: c.pg_type for c in table.columns}
    converted = {}
    for key, value in row.items():
        pg_type = col_types.get(key, "text")
        converted[key] = convert_value(value, pg_type)
    return converted


def extract_incremental(
    conn: psycopg2.extensions.connection,
    table: TableDef,
    base_date: str,
) -> list[dict[str, Any]]:
    """Incremental 추출: timestamp_column 기준 KST 1일분."""
    ts_col = table.timestamp_column
    if ts_col is None:
        raise ValueError(f"Incremental table {table.name} has no timestamp column")

    utc_start, utc_end = _kst_boundaries(base_date)

    sql = f'SELECT * FROM "{table.name}" WHERE "{ts_col}" >= %s AND "{ts_col}" < %s'
    logger.info("Extracting %s: %s in [%s, %s)", table.name, ts_col, utc_start, utc_end)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (utc_start, utc_end))
        rows = [dict(row) for row in cur.fetchall()]

    logger.info("Extracted %d rows from %s", len(rows), table.name)
    return [_convert_row(row, table) for row in rows]


def extract_snapshot(
    conn: psycopg2.extensions.connection,
    table: TableDef,
) -> list[dict[str, Any]]:
    """Snapshot 추출: 전체 데이터."""
    sql = f'SELECT * FROM "{table.name}"'
    logger.info("Extracting snapshot: %s", table.name)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        rows = [dict(row) for row in cur.fetchall()]

    logger.info("Extracted %d rows from %s", len(rows), table.name)
    return [_convert_row(row, table) for row in rows]


def extract_full(
    conn: psycopg2.extensions.connection,
    table: TableDef,
) -> list[dict[str, Any]]:
    """전체 추출 (초기 적재용): SELECT * + timestamp → KST base_date 변환."""
    sql = f'SELECT * FROM "{table.name}"'
    logger.info("Extracting full: %s", table.name)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        rows = [dict(row) for row in cur.fetchall()]

    logger.info("Extracted %d rows from %s", len(rows), table.name)
    return [_convert_row(row, table) for row in rows]


def derive_base_date(row: dict[str, Any], table: TableDef, fallback_date: str) -> str:
    """행의 timestamp_column에서 KST 기준 base_date를 도출한다."""
    ts_col = table.timestamp_column
    if ts_col is None or ts_col not in row or row[ts_col] is None:
        return fallback_date

    ts_val = row[ts_col]
    # convert_value가 이미 isoformat 문자열로 변환했을 수 있음
    if isinstance(ts_val, str):
        try:
            dt = datetime.fromisoformat(ts_val)
        except ValueError:
            return fallback_date
    elif isinstance(ts_val, datetime):
        dt = ts_val
    else:
        return fallback_date

    # timezone-naive면 UTC로 간주
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(KST).strftime("%Y-%m-%d")


def extract_table(
    conn: psycopg2.extensions.connection,
    table: TableDef,
    base_date: str,
) -> list[dict[str, Any]]:
    """테이블 모드에 따라 적절한 추출 함수를 호출한다."""
    if table.mode == "incremental":
        return extract_incremental(conn, table, base_date)
    return extract_snapshot(conn, table)
