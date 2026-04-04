"""R2 아카이브 — 30일 초과 snapshot 데이터 이관."""

from __future__ import annotations

import json
import logging
import random
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from pseudolab_etl.config import D1Config, R2Config
from pseudolab_etl.d1 import _d1_query, query_rows
from pseudolab_etl.table_registry import SNAPSHOT_TABLES, TableDef

logger = logging.getLogger(__name__)


# ── wrangler CLI ─────────────────────────────────────────

_wrangler_bin: str | None = None


def _find_wrangler() -> str:
    global _wrangler_bin  # noqa: PLW0603
    if _wrangler_bin is not None:
        return _wrangler_bin

    found = shutil.which("wrangler")
    if found:
        _wrangler_bin = found
        return _wrangler_bin

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "node_modules" / ".bin" / "wrangler"
        if candidate.is_file():
            _wrangler_bin = str(candidate)
            return _wrangler_bin

    raise RuntimeError("wrangler CLI not found. Install with: pnpm add -D wrangler")


def _wrangler_r2_put(
    bucket: str, key: str, file_path: Path, *, max_retries: int = 3,
) -> None:
    wrangler = _find_wrangler()
    for attempt in range(1, max_retries + 1):
        try:
            subprocess.run(
                [wrangler, "r2", "object", "put", f"{bucket}/{key}",
                 "--file", str(file_path), "--remote"],
                capture_output=True, check=True, text=True,
            )
            return
        except subprocess.CalledProcessError as exc:
            if attempt == max_retries:
                raise RuntimeError(
                    f"wrangler r2 put failed after {max_retries} retries: {exc.stderr}"
                ) from exc
            wait = (2**attempt) + random.uniform(0, 1)
            logger.warning(
                "wrangler r2 put attempt %d/%d failed, retrying in %.1fs",
                attempt, max_retries, wait,
            )
            time.sleep(wait)


# ── 아카이브 로직 ────────────────────────────────────────


def find_archivable_dates(
    table: TableDef,
    retention_days: int,
    config: D1Config,
) -> list[str]:
    """D1에서 retention_days보다 오래된 base_date를 조회한다."""
    sql = (
        f"SELECT DISTINCT base_date FROM {table.dl_name} "
        f"WHERE base_date < date('now', '-{retention_days} days') "
        f"ORDER BY base_date"
    )
    rows = query_rows(sql, [], config)
    return [row["base_date"] for row in rows]


def archive_table_date(
    table: TableDef,
    base_date: str,
    d1_config: D1Config,
    r2_config: R2Config,
    *,
    dry_run: bool = False,
) -> int:
    """특정 테이블+날짜 데이터를 R2로 이관 후 D1에서 삭제한다.

    Returns:
        이관된 행 수
    """
    # 1. D1에서 데이터 조회
    sql = f"SELECT * FROM {table.dl_name} WHERE base_date = ?"
    rows = query_rows(sql, [base_date], d1_config)

    if not rows:
        return 0

    # 2. JSONL 파일로 작성
    r2_key = f"{r2_config.prefix}/{table.name}/{base_date}.jsonl"

    if dry_run:
        logger.info("Dry run: would archive %d rows to %s", len(rows), r2_key)
        return len(rows)

    with tempfile.TemporaryDirectory() as tmp_dir:
        jsonl_path = Path(tmp_dir) / "archive.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        # 3. R2에 업로드
        _wrangler_r2_put(r2_config.bucket_name, r2_key, jsonl_path)

    # 4. D1에서 삭제
    delete_sql = f"DELETE FROM {table.dl_name} WHERE base_date = ?"
    _d1_query(delete_sql, [base_date], d1_config)

    logger.info("Archived %d rows: %s → %s", len(rows), table.dl_name, r2_key)
    return len(rows)


def archive_all_expired(
    d1_config: D1Config,
    r2_config: R2Config,
    *,
    retention_days: int = 30,
    dry_run: bool = False,
) -> dict[str, int]:
    """모든 snapshot 테이블에서 만료 데이터를 R2로 이관한다.

    Returns:
        {table_name: archived_row_count}
    """
    results: dict[str, int] = {}

    for table in SNAPSHOT_TABLES.values():
        dates = find_archivable_dates(table, retention_days, d1_config)
        if not dates:
            continue

        total = 0
        for base_date in dates:
            try:
                count = archive_table_date(
                    table, base_date, d1_config, r2_config, dry_run=dry_run,
                )
                total += count
            except Exception as e:
                logger.error("Archive failed: %s/%s: %s", table.name, base_date, e)

        if total > 0:
            results[table.name] = total

    return results
