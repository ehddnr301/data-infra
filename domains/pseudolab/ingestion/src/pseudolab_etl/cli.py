"""Click CLI — pseudolab-etl."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import click

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def _setup(json_log: bool, config_path: str | None) -> Any:
    """공통 초기화: 로깅 + 설정 로딩."""
    from pseudolab_etl.logging_config import setup_logging

    setup_logging(json_log=json_log)

    from pseudolab_etl.config import load_config

    path = Path(config_path) if config_path else None
    return load_config(path)


@click.group()
def main() -> None:
    """Supabase → D1 일별 배치 ETL."""


@main.command()
@click.option("--date", "base_date", required=True, help="KST 기준 적재일 (YYYY-MM-DD)")
@click.option("--tables", default=None, help="콤마 구분 테이블 필터")
@click.option("--mode", type=click.Choice(["incremental", "snapshot", "all"]), default="all")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--config", "config_path", default=None)
@click.option("--json-log", is_flag=True, default=False)
def run(
    base_date: str,
    tables: str | None,
    mode: str,
    dry_run: bool,
    config_path: str | None,
    json_log: bool,
) -> None:
    """일별 ETL 실행: extract → PII hash → D1 적재."""
    cfg = _setup(json_log, config_path)

    from pseudolab_etl.d1 import insert_table_rows
    from pseudolab_etl.extractor import extract_table, get_connection
    from pseudolab_etl.pii import apply_pii_hashing
    from pseudolab_etl.table_registry import ALL_TABLES

    # 테이블 필터링
    target_tables = _filter_tables(ALL_TABLES, tables, mode)

    if not target_tables:
        logger.warning("No tables matched filters")
        return

    load_dt = datetime.now(KST).isoformat()

    # PII salt 검증
    salt = cfg.pii.hash_salt
    if not salt:
        logger.error("PII_HASH_SALT is not set")
        sys.exit(1)

    conn = get_connection(cfg.supabase)
    success_count = 0
    fail_count = 0
    total_rows = 0

    try:
        for table in target_tables.values():
            try:
                # 1. 추출
                rows = extract_table(conn, table, base_date)

                # 2. PII 해싱
                apply_pii_hashing(rows, table.name, salt)

                # 3. 공통 칼럼 추가
                for row in rows:
                    row["base_date"] = base_date
                    row["load_dt"] = load_dt

                # 4. D1 적재
                dl_columns = table.column_names + ["base_date", "load_dt"]
                result = insert_table_rows(
                    table.dl_name, dl_columns, rows, base_date, cfg.d1,
                    dry_run=dry_run,
                )

                if result.errors:
                    fail_count += 1
                    for err in result.errors:
                        logger.error(err)
                else:
                    success_count += 1
                    total_rows += result.rows_inserted

                logger.info(
                    "%s: %d rows extracted, %d inserted",
                    table.name, len(rows), result.rows_inserted,
                )

            except Exception as e:
                fail_count += 1
                logger.error("Failed to process %s: %s", table.name, e)

    finally:
        conn.close()

    logger.info(
        "ETL complete: %d/%d tables succeeded, %d total rows, %d failed",
        success_count, len(target_tables), total_rows, fail_count,
    )

    if fail_count > 0:
        sys.exit(1)


@main.command()
@click.option("--start-date", default=None, help="시작일 (YYYY-MM-DD)")
@click.option("--end-date", default=None, help="종료일 (YYYY-MM-DD)")
@click.option("--full", is_flag=True, default=False, help="전체 1회 적재 (SELECT * → base_date 자동 계산)")
@click.option("--tables", default=None, help="콤마 구분 테이블 필터")
@click.option("--mode", type=click.Choice(["incremental", "snapshot", "all"]), default="all")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--config", "config_path", default=None)
@click.option("--json-log", is_flag=True, default=False)
def backfill(
    start_date: str | None,
    end_date: str | None,
    full: bool,
    tables: str | None,
    mode: str,
    dry_run: bool,
    config_path: str | None,
    json_log: bool,
) -> None:
    """백필 실행. --full이면 전체 1회 적재, 아니면 날짜 범위 반복."""
    cfg = _setup(json_log, config_path)

    from pseudolab_etl.d1 import insert_table_rows
    from pseudolab_etl.extractor import extract_table, get_connection
    from pseudolab_etl.pii import apply_pii_hashing
    from pseudolab_etl.table_registry import ALL_TABLES

    target_tables = _filter_tables(ALL_TABLES, tables, mode)
    salt = cfg.pii.hash_salt
    if not salt:
        logger.error("PII_HASH_SALT is not set")
        sys.exit(1)

    if full:
        _backfill_full(cfg, target_tables, salt, dry_run)
    else:
        if not start_date or not end_date:
            logger.error("--start-date and --end-date required (or use --full)")
            sys.exit(1)
        _backfill_range(cfg, target_tables, salt, start_date, end_date, dry_run)


def _backfill_full(cfg: Any, target_tables: dict, salt: str, dry_run: bool) -> None:
    """전체 1회 적재: SELECT * → PII 해싱 → base_date 자동 계산 → D1."""
    from collections import defaultdict

    from pseudolab_etl.d1 import insert_table_rows
    from pseudolab_etl.extractor import derive_base_date, extract_full, get_connection
    from pseudolab_etl.pii import apply_pii_hashing

    load_dt = datetime.now(KST).isoformat()
    fallback_date = datetime.now(KST).strftime("%Y-%m-%d")

    logger.info("Full backfill: %d tables", len(target_tables))

    conn = get_connection(cfg.supabase)
    success_count = 0
    fail_count = 0
    total_rows = 0

    try:
        for table in target_tables.values():
            try:
                # 1. 전체 추출
                rows = extract_full(conn, table)

                if not rows:
                    logger.info("%s: 0 rows, skipping", table.name)
                    success_count += 1
                    continue

                # 2. PII 해싱
                apply_pii_hashing(rows, table.name, salt)

                # 3. base_date 계산 + 공통 칼럼
                for row in rows:
                    row["base_date"] = derive_base_date(row, table, fallback_date)
                    row["load_dt"] = load_dt

                # 4. base_date별 그룹핑 → 각 그룹을 D1에 적재
                by_date: dict[str, list[dict]] = defaultdict(list)
                for row in rows:
                    by_date[row["base_date"]].append(row)

                dl_columns = table.column_names + ["base_date", "load_dt"]
                table_inserted = 0

                for base_date, date_rows in sorted(by_date.items()):
                    result = insert_table_rows(
                        table.dl_name, dl_columns, date_rows, base_date, cfg.d1,
                        dry_run=dry_run,
                    )
                    if result.errors:
                        for err in result.errors:
                            logger.error(err)
                    table_inserted += result.rows_inserted

                success_count += 1
                total_rows += table_inserted
                logger.info(
                    "%s: %d rows extracted, %d dates, %d inserted",
                    table.name, len(rows), len(by_date), table_inserted,
                )

            except Exception as e:
                fail_count += 1
                logger.error("Failed to process %s: %s", table.name, e)

    finally:
        conn.close()

    logger.info(
        "Full backfill complete: %d/%d tables succeeded, %d total rows, %d failed",
        success_count, len(target_tables), total_rows, fail_count,
    )

    if fail_count > 0:
        sys.exit(1)


def _backfill_range(
    cfg: Any, target_tables: dict, salt: str,
    start_date: str, end_date: str, dry_run: bool,
) -> None:
    """날짜 범위 반복 백필."""
    from pseudolab_etl.d1 import insert_table_rows
    from pseudolab_etl.extractor import extract_table, get_connection
    from pseudolab_etl.pii import apply_pii_hashing

    dates = _date_range(start_date, end_date)
    logger.info("Backfill: %d dates, %d tables", len(dates), len(target_tables))

    conn = get_connection(cfg.supabase)
    try:
        for base_date in dates:
            load_dt = datetime.now(KST).isoformat()
            logger.info("Processing date: %s", base_date)

            for table in target_tables.values():
                try:
                    rows = extract_table(conn, table, base_date)
                    apply_pii_hashing(rows, table.name, salt)
                    for row in rows:
                        row["base_date"] = base_date
                        row["load_dt"] = load_dt

                    dl_columns = table.column_names + ["base_date", "load_dt"]
                    insert_table_rows(
                        table.dl_name, dl_columns, rows, base_date, cfg.d1,
                        dry_run=dry_run,
                    )
                except Exception as e:
                    logger.error("Failed: %s/%s: %s", table.name, base_date, e)
    finally:
        conn.close()


@main.command("create-schema")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--config", "config_path", default=None)
@click.option("--json-log", is_flag=True, default=False)
def create_schema(dry_run: bool, config_path: str | None, json_log: bool) -> None:
    """D1에 dl_* 테이블을 생성한다."""
    cfg = _setup(json_log, config_path)
    from pseudolab_etl.schema import ensure_schema

    errors = ensure_schema(cfg.d1, dry_run=dry_run)
    if errors:
        for err in errors:
            logger.error(err)
        sys.exit(1)
    logger.info("Schema creation complete")


@main.command()
@click.option("--retention-days", default=30, type=int)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--config", "config_path", default=None)
@click.option("--json-log", is_flag=True, default=False)
def archive(
    retention_days: int,
    dry_run: bool,
    config_path: str | None,
    json_log: bool,
) -> None:
    """30일 초과 snapshot 데이터를 R2로 이관한다."""
    cfg = _setup(json_log, config_path)
    from pseudolab_etl.r2_archive import archive_all_expired

    results = archive_all_expired(
        cfg.d1, cfg.r2, retention_days=retention_days, dry_run=dry_run,
    )

    if results:
        for table_name, count in results.items():
            logger.info("Archived %s: %d rows", table_name, count)
    else:
        logger.info("No data to archive")


@main.command("generate-ddl")
def generate_ddl() -> None:
    """79개 dl_* 테이블 DDL을 stdout에 출력한다."""
    from pseudolab_etl.schema import generate_all_ddl

    click.echo(generate_all_ddl())


# ── 헬퍼 ─────────────────────────────────────────────────


def _filter_tables(
    all_tables: dict[str, Any],
    table_filter: str | None,
    mode: str,
) -> dict[str, Any]:
    """테이블 이름/모드 필터링."""
    tables = dict(all_tables)

    if table_filter:
        names = {n.strip() for n in table_filter.split(",")}
        tables = {k: v for k, v in tables.items() if k in names}

    if mode != "all":
        tables = {k: v for k, v in tables.items() if v.mode == mode}

    return tables


def _date_range(start: str, end: str) -> list[str]:
    """시작일~종료일 리스트를 생성한다 (양쪽 포함)."""
    from datetime import datetime as dt

    dates = []
    current = dt.strptime(start, "%Y-%m-%d")
    end_dt = dt.strptime(end, "%Y-%m-%d")
    while current <= end_dt:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates
