"""데이터 품질 검증 모듈.

D1에 적재된 DL 테이블 및 일별 통계의 품질을 규칙 기반으로 검증한다.
- DQ001: 공통 필수 필드 검사 (event_id, user_login, repo_name, ts_kst)
- DQ002: PK 중복 검사 (단일 PK + push/gollum 복합 PK)
- DQ003: 날짜 정합성 (substr(ts_kst,1,10) == base_date)
- DQ005: org/repo 범위 검증
- DQ006: DL 테이블 집계 vs daily_stats 정합성 검증

DQ004 (이벤트 타입 유효성)는 테이블 자체가 타입이므로 제거됨.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from gharchive_etl.config import AppConfig, D1Config
from gharchive_etl.d1 import query_rows
from gharchive_etl.dl_models import DL_TABLES, EXPLODED_TABLES, TABLE_TO_EVENT_TYPE

logger = logging.getLogger(__name__)

# ── Rule ID 상수 ──────────────────────────────────────────
DQ001 = "DQ001"
DQ002 = "DQ002"
DQ003 = "DQ003"
DQ005 = "DQ005"
DQ006 = "DQ006"


# ── 결과 데이터 클래스 ───────────────────────────────────

@dataclass
class QualityRuleResult:
    """개별 품질 규칙 실행 결과."""

    rule_id: str
    severity: Literal["WARN", "ERROR"]
    passed: bool
    checked_rows: int
    failed_rows: int
    samples: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""


@dataclass
class QualityReport:
    """전체 품질 검증 리포트."""

    batch_date: str
    passed: bool
    total_rules: int
    failed_rules: int
    results: list[QualityRuleResult] = field(default_factory=list)
    reason: str | None = None


@dataclass
class ConsistencyReport:
    """DL 테이블 집계와 daily_stats 정합성 리포트."""

    batch_date: str
    total_event_rows: int
    total_daily_stats: int
    mismatched_keys: int
    missing_in_stats: int
    extra_in_stats: int
    passed: bool


# ── 헬퍼 ─────────────────────────────────────────────────

def _count_all_dl_rows(base_date: str, config: D1Config) -> int:
    """모든 DL 테이블의 base_date 기준 행 수 합계."""
    total = 0
    for table in DL_TABLES:
        sql = f"SELECT COUNT(*) AS cnt FROM {table} WHERE base_date = ?"
        result = query_rows(sql, [base_date], config)
        total += result[0]["cnt"] if result else 0
    return total


# ── 개별 품질 규칙 ───────────────────────────────────────

def check_required_fields(batch_date: str, config: D1Config) -> QualityRuleResult:
    """DQ001: DL 테이블 공통 필수 필드(event_id, user_login, repo_name, ts_kst) null/empty 검사."""
    total = 0
    all_failed: list[dict[str, Any]] = []

    for table in DL_TABLES:
        count_sql = f"SELECT COUNT(*) AS cnt FROM {table} WHERE base_date = ?"
        count_result = query_rows(count_sql, [batch_date], config)
        total += count_result[0]["cnt"] if count_result else 0

        fail_sql = (
            f"SELECT event_id, user_login, repo_name, ts_kst FROM {table} "
            f"WHERE base_date = ? AND ("
            f"event_id IS NULL OR event_id = '' OR "
            f"user_login IS NULL OR user_login = '' OR "
            f"repo_name IS NULL OR repo_name = '' OR "
            f"ts_kst IS NULL OR ts_kst = ''"
            f")"
        )
        failed = query_rows(fail_sql, [batch_date], config)
        for row in failed:
            row["_table"] = table
        all_failed.extend(failed)

    passed = len(all_failed) == 0
    return QualityRuleResult(
        rule_id=DQ001,
        severity="ERROR",
        passed=passed,
        checked_rows=total,
        failed_rows=len(all_failed),
        samples=all_failed[:5],
        message=f"필수 필드 null/empty 검사: {len(all_failed)}건 실패" if not passed else "필수 필드 검사 통과",
    )


def check_duplicates(batch_date: str, config: D1Config) -> QualityRuleResult:
    """DQ002: DL 테이블 PK 중복 검사.

    단일 PK 테이블: event_id 중복
    복합 PK 테이블 (push/gollum): (event_id, commit_sha/page_name) 중복
    """
    total = 0
    all_duplicates: list[dict[str, Any]] = []

    for table in DL_TABLES:
        count_sql = f"SELECT COUNT(*) AS cnt FROM {table} WHERE base_date = ?"
        count_result = query_rows(count_sql, [batch_date], config)
        total += count_result[0]["cnt"] if count_result else 0

        if table == "dl_push_events":
            dup_sql = (
                "SELECT event_id, commit_sha, COUNT(*) AS cnt FROM dl_push_events "
                "WHERE base_date = ? GROUP BY event_id, commit_sha HAVING cnt > 1"
            )
        elif table == "dl_gollum_events":
            dup_sql = (
                "SELECT event_id, page_name, COUNT(*) AS cnt FROM dl_gollum_events "
                "WHERE base_date = ? GROUP BY event_id, page_name HAVING cnt > 1"
            )
        else:
            dup_sql = (
                f"SELECT event_id, COUNT(*) AS cnt FROM {table} "
                f"WHERE base_date = ? GROUP BY event_id HAVING cnt > 1"
            )
        duplicates = query_rows(dup_sql, [batch_date], config)
        for row in duplicates:
            row["_table"] = table
        all_duplicates.extend(duplicates)

    passed = len(all_duplicates) == 0
    return QualityRuleResult(
        rule_id=DQ002,
        severity="ERROR",
        passed=passed,
        checked_rows=total,
        failed_rows=len(all_duplicates),
        samples=all_duplicates[:5],
        message=f"중복 PK 검사: {len(all_duplicates)}건 중복" if not passed else "중복 PK 없음",
    )


def check_date_consistency(batch_date: str, config: D1Config) -> QualityRuleResult:
    """DQ003: substr(ts_kst,1,10) vs base_date 비교.

    주의: SQLite date() 함수는 KST 오프셋을 UTC로 변환하므로 사용 불가.
    문자열 추출 substr(ts_kst, 1, 10)으로 KST 기준 날짜를 비교한다.
    """
    total = 0
    all_mismatched: list[dict[str, Any]] = []

    for table in DL_TABLES:
        count_sql = f"SELECT COUNT(*) AS cnt FROM {table} WHERE base_date = ?"
        count_result = query_rows(count_sql, [batch_date], config)
        total += count_result[0]["cnt"] if count_result else 0

        mismatch_sql = (
            f"SELECT event_id, ts_kst, base_date FROM {table} "
            f"WHERE base_date = ? AND substr(ts_kst, 1, 10) != base_date"
        )
        mismatched = query_rows(mismatch_sql, [batch_date], config)
        for row in mismatched:
            row["_table"] = table
        all_mismatched.extend(mismatched)

    passed = len(all_mismatched) == 0
    return QualityRuleResult(
        rule_id=DQ003,
        severity="WARN",
        passed=passed,
        checked_rows=total,
        failed_rows=len(all_mismatched),
        samples=all_mismatched[:5],
        message=f"날짜 정합성 검사: {len(all_mismatched)}건 불일치" if not passed else "날짜 정합성 통과",
    )


def check_org_repo_scope(batch_date: str, config: AppConfig) -> QualityRuleResult:
    """DQ005: target_orgs 외 org, repo 범위 검증."""
    orgs = config.target_orgs
    org_placeholders = ", ".join("?" for _ in orgs)
    repo_prefixes = [f"{org}/%" for org in orgs]
    repo_conditions = " AND ".join("repo_name NOT LIKE ?" for _ in repo_prefixes)

    total = 0
    all_out_of_scope: list[dict[str, Any]] = []

    for table in DL_TABLES:
        count_sql = f"SELECT COUNT(*) AS cnt FROM {table} WHERE base_date = ?"
        count_result = query_rows(count_sql, [batch_date], config.d1)
        total += count_result[0]["cnt"] if count_result else 0

        scope_sql = (
            f"SELECT event_id, organization, repo_name FROM {table} "
            f"WHERE base_date = ? AND "
            f"(organization IS NOT NULL AND organization != '' AND organization NOT IN ({org_placeholders})) "
            f"AND ({repo_conditions})"
        )
        params: list[Any] = [batch_date, *orgs, *repo_prefixes]
        out_of_scope = query_rows(scope_sql, params, config.d1)
        for row in out_of_scope:
            row["_table"] = table
        all_out_of_scope.extend(out_of_scope)

    passed = len(all_out_of_scope) == 0
    return QualityRuleResult(
        rule_id=DQ005,
        severity="WARN",
        passed=passed,
        checked_rows=total,
        failed_rows=len(all_out_of_scope),
        samples=all_out_of_scope[:5],
        message=f"범위 검사: {len(all_out_of_scope)}건 범위 밖" if not passed else "범위 검사 통과",
    )


def check_daily_stats_consistency(batch_date: str, config: D1Config) -> ConsistencyReport:
    """DL 테이블 집계와 daily_stats 비교.

    각 DL 테이블의 (base_date, organization, repo_name) 별 이벤트 수와
    daily_stats 테이블의 값을 비교하여 누락/초과/불일치를 검출한다.
    push/gollum은 펼침 테이블이므로 COUNT(DISTINCT event_id) 사용.
    """
    event_map: dict[tuple[str, str, str], int] = {}
    total_agg_rows = 0

    for table_name in DL_TABLES:
        event_type = TABLE_TO_EVENT_TYPE.get(table_name, table_name)
        if table_name in EXPLODED_TABLES:
            sql = (
                f"SELECT COALESCE(organization,'') AS org, repo_name, "
                f"COUNT(DISTINCT event_id) AS cnt FROM {table_name} "
                f"WHERE base_date = ? GROUP BY organization, repo_name"
            )
        else:
            sql = (
                f"SELECT COALESCE(organization,'') AS org, repo_name, "
                f"COUNT(*) AS cnt FROM {table_name} "
                f"WHERE base_date = ? GROUP BY organization, repo_name"
            )
        rows = query_rows(sql, [batch_date], config)
        total_agg_rows += len(rows)
        for row in rows:
            key = (row["org"], row["repo_name"], event_type)
            event_map[key] = event_map.get(key, 0) + row["cnt"]

    stats_sql = (
        "SELECT org_name, repo_name, event_type, count FROM daily_stats "
        "WHERE date = ?"
    )
    stats_rows = query_rows(stats_sql, [batch_date], config)

    stats_map: dict[tuple[str, str, str], int] = {}
    for row in stats_rows:
        key = (row["org_name"], row["repo_name"], row["event_type"])
        stats_map[key] = row["count"]

    all_keys = set(event_map.keys()) | set(stats_map.keys())
    missing_in_stats = 0
    extra_in_stats = 0
    mismatched = 0

    for key in all_keys:
        in_events = key in event_map
        in_stats = key in stats_map
        if in_events and not in_stats:
            missing_in_stats += 1
        elif not in_events and in_stats:
            extra_in_stats += 1
        elif event_map.get(key) != stats_map.get(key):
            mismatched += 1

    total_mismatched = missing_in_stats + extra_in_stats + mismatched
    return ConsistencyReport(
        batch_date=batch_date,
        total_event_rows=total_agg_rows,
        total_daily_stats=len(stats_rows),
        mismatched_keys=mismatched,
        missing_in_stats=missing_in_stats,
        extra_in_stats=extra_in_stats,
        passed=total_mismatched == 0,
    )


def _run_dq006(batch_date: str, config: D1Config) -> QualityRuleResult:
    """DQ006: daily_stats 정합성을 QualityRuleResult로 래핑."""
    report = check_daily_stats_consistency(batch_date, config)
    total_mismatched = report.mismatched_keys + report.missing_in_stats + report.extra_in_stats
    passed = report.passed
    return QualityRuleResult(
        rule_id=DQ006,
        severity="ERROR",
        passed=passed,
        checked_rows=report.total_event_rows + report.total_daily_stats,
        failed_rows=total_mismatched,
        samples=[],
        message=(
            f"daily_stats 정합성: mismatch={report.mismatched_keys}, "
            f"missing={report.missing_in_stats}, extra={report.extra_in_stats}"
            if not passed
            else "daily_stats 정합성 통과"
        ),
    )


# ── 통합 실행 ─────────────────────────────────────────────

def run_quality_checks(batch_date: str, config: AppConfig) -> QualityReport:
    """모든 품질 규칙을 실행하고 리포트를 반환.

    - DL 테이블 전체 행 수 == 0 이면 reason="NO_DATA"로 pass 반환
    - DQ001, DQ002, DQ003, DQ005, DQ006 실행 (DQ004 제거됨)
    - ERROR severity 규칙 하나라도 실패 시 passed=False
    """
    d1 = config.d1

    total_events = _count_all_dl_rows(batch_date, d1)

    if total_events == 0:
        return QualityReport(
            batch_date=batch_date,
            passed=True,
            total_rules=5,
            failed_rules=0,
            results=[],
            reason="NO_DATA",
        )

    results: list[QualityRuleResult] = [
        check_required_fields(batch_date, d1),
        check_duplicates(batch_date, d1),
        check_date_consistency(batch_date, d1),
        check_org_repo_scope(batch_date, config),
        _run_dq006(batch_date, d1),
    ]

    failed_rules = sum(1 for r in results if not r.passed)
    has_error_failure = any(
        not r.passed and r.severity == "ERROR" for r in results
    )

    return QualityReport(
        batch_date=batch_date,
        passed=not has_error_failure,
        total_rules=len(results),
        failed_rules=failed_rules,
        results=results,
    )
