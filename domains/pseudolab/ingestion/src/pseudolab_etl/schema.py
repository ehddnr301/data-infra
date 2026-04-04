"""D1 DDL 생성 — 79개 dl_* 테이블 CREATE TABLE."""

from __future__ import annotations

import logging
from typing import Any

from pseudolab_etl.config import D1Config
from pseudolab_etl.d1 import _d1_query
from pseudolab_etl.table_registry import ALL_TABLES, TableDef
from pseudolab_etl.type_mapping import pg_to_d1_type

logger = logging.getLogger(__name__)


def generate_create_table(table: TableDef) -> str:
    """단일 테이블의 CREATE TABLE IF NOT EXISTS DDL을 생성한다."""
    lines = []
    for col in table.columns:
        d1_type = pg_to_d1_type(col.pg_type)
        nullable = "" if col.nullable else " NOT NULL"
        lines.append(f"    {col.name} {d1_type}{nullable}")

    # 공통 칼럼 추가
    lines.append("    base_date TEXT NOT NULL")
    lines.append("    load_dt TEXT NOT NULL")

    columns_sql = ",\n".join(lines)
    return f"CREATE TABLE IF NOT EXISTS {table.dl_name} (\n{columns_sql}\n);"


def generate_create_index(table: TableDef) -> str:
    """base_date 인덱스 DDL을 생성한다."""
    return (
        f"CREATE INDEX IF NOT EXISTS idx_{table.dl_name}_base_date "
        f"ON {table.dl_name} (base_date);"
    )


def generate_all_ddl() -> str:
    """79개 테이블 전체 DDL을 생성한다."""
    parts = []
    for table in sorted(ALL_TABLES.values(), key=lambda t: t.name):
        parts.append(generate_create_table(table))
        parts.append(generate_create_index(table))
        parts.append("")
    return "\n".join(parts)


def ensure_schema(
    config: D1Config,
    *,
    dry_run: bool = False,
    tables: dict[str, TableDef] | None = None,
) -> list[str]:
    """D1에 모든 dl_* 테이블을 생성한다 (idempotent).

    Returns:
        실행 에러 목록 (빈 리스트 = 성공)
    """
    target_tables = tables or ALL_TABLES
    errors: list[str] = []

    for table in sorted(target_tables.values(), key=lambda t: t.name):
        create_sql = generate_create_table(table)
        index_sql = generate_create_index(table)

        if dry_run:
            logger.info("Dry run CREATE TABLE: %s", table.dl_name)
            continue

        try:
            _d1_query(create_sql, [], config)
            _d1_query(index_sql, [], config)
            logger.info("Created table: %s", table.dl_name)
        except Exception as e:
            error_msg = f"Failed to create {table.dl_name}: {e}"
            errors.append(error_msg)
            logger.error(error_msg)

    return errors
