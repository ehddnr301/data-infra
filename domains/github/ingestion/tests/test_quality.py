"""데이터 품질 검증 모듈 테스트.

14개 DL 테이블 기반 품질 규칙 검증.
각 규칙이 모든 DL 테이블을 순회하므로, SQL 패턴 기반 mock 함수를 사용한다.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from gharchive_etl.config import AppConfig, D1Config
from gharchive_etl.dl_models import DL_TABLES
from gharchive_etl.quality import (
    DQ001,
    DQ002,
    DQ003,
    DQ005,
    DQ006,
    check_daily_stats_consistency,
    check_date_consistency,
    check_duplicates,
    check_org_repo_scope,
    check_required_fields,
    run_quality_checks,
)


def _make_d1_config(**overrides: Any) -> D1Config:
    """테스트용 D1Config 헬퍼."""
    defaults = {
        "database_id": "test-db-id",
        "account_id": "test-account-id",
        "api_token": "test-api-token",
    }
    defaults.update(overrides)
    return D1Config(**defaults)


def _make_app_config(**overrides: Any) -> AppConfig:
    """테스트용 AppConfig 헬퍼."""
    defaults: dict[str, Any] = {
        "target_orgs": ["pseudolab"],
        "d1": {
            "database_id": "test-db-id",
            "account_id": "test-account-id",
            "api_token": "test-api-token",
        },
    }
    defaults.update(overrides)
    return AppConfig(**defaults)


_PATCH_QUERY = "gharchive_etl.quality.query_rows"


def _mock_count_only(sql: str, params: list, config: Any) -> list[dict[str, Any]]:
    """COUNT 쿼리만 응답하고 나머지는 빈 리스트 (모든 규칙 통과)."""
    if sql.strip().startswith("SELECT COUNT(*)"):
        return [{"cnt": 10}]
    return []


def _mock_zero_count(sql: str, params: list, config: Any) -> list[dict[str, Any]]:
    """모든 테이블 행 수 0 (NO_DATA 트리거)."""
    if sql.strip().startswith("SELECT COUNT(*)"):
        return [{"cnt": 0}]
    return []


def _mock_all_pass(sql: str, params: list, config: Any) -> list[dict[str, Any]]:
    """모든 규칙 통과 + DQ006 daily_stats 정합성도 통과."""
    if sql.strip().startswith("SELECT COUNT(*)"):
        return [{"cnt": 10}]
    if "daily_stats" in sql:
        return []
    if "GROUP BY" in sql:
        return []
    return []


class TestDQ001RequiredFields:
    """DQ001: 필수 필드 null/empty 검사 (14개 DL 테이블)."""

    def test_pass_no_failures(self) -> None:
        config = _make_d1_config()
        with patch(_PATCH_QUERY, side_effect=_mock_count_only):
            result = check_required_fields("2024-01-15", config)
            assert result.rule_id == DQ001
            assert result.passed is True
            assert result.checked_rows == 10 * len(DL_TABLES)
            assert result.failed_rows == 0

    def test_fail_with_null_fields(self) -> None:
        config = _make_d1_config()
        call_count = 0

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            if sql.strip().startswith("SELECT COUNT(*)"):
                return [{"cnt": 10}]
            # 첫 번째 테이블의 fail 쿼리에서만 실패 행 반환
            if call_count == 2:
                return [
                    {"event_id": "", "user_login": "user", "repo_name": "r", "ts_kst": "t"},
                    {"event_id": "2", "user_login": "", "repo_name": "r", "ts_kst": "t"},
                ]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            result = check_required_fields("2024-01-15", config)
            assert result.passed is False
            assert result.failed_rows == 2
            assert result.severity == "ERROR"
            assert len(result.samples) == 2


class TestDQ002Duplicates:
    """DQ002: DL 테이블 PK 중복 검사 (단일 PK + 복합 PK)."""

    def test_pass_no_duplicates(self) -> None:
        config = _make_d1_config()
        with patch(_PATCH_QUERY, side_effect=_mock_count_only):
            result = check_duplicates("2024-01-15", config)
            assert result.rule_id == DQ002
            assert result.passed is True
            assert result.failed_rows == 0

    def test_fail_with_duplicates_single_pk(self) -> None:
        """단일 PK 테이블 (event_id) 중복."""
        config = _make_d1_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if sql.strip().startswith("SELECT COUNT(*)"):
                return [{"cnt": 10}]
            # dl_watch_events는 단일 PK → event_id GROUP BY
            if "dl_watch_events" in sql and "GROUP BY event_id HAVING" in sql:
                return [{"event_id": "1", "cnt": 3}]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            result = check_duplicates("2024-01-15", config)
            assert result.passed is False
            assert result.failed_rows >= 1
            assert result.severity == "ERROR"

    def test_fail_with_duplicates_composite_pk(self) -> None:
        """복합 PK 테이블 (push: event_id + commit_sha) 중복."""
        config = _make_d1_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if sql.strip().startswith("SELECT COUNT(*)"):
                return [{"cnt": 10}]
            if "dl_push_events" in sql and "commit_sha" in sql and "GROUP BY" in sql:
                return [{"event_id": "1", "commit_sha": "abc", "cnt": 2}]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            result = check_duplicates("2024-01-15", config)
            assert result.passed is False
            assert result.failed_rows >= 1


class TestDQ003DateConsistency:
    """DQ003: substr(ts_kst,1,10) vs base_date 비교."""

    def test_pass_all_consistent(self) -> None:
        config = _make_d1_config()
        with patch(_PATCH_QUERY, side_effect=_mock_count_only):
            result = check_date_consistency("2024-01-15", config)
            assert result.rule_id == DQ003
            assert result.passed is True
            assert result.failed_rows == 0

    def test_fail_with_mismatched_dates(self) -> None:
        config = _make_d1_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if sql.strip().startswith("SELECT COUNT(*)"):
                return [{"cnt": 10}]
            if "substr" in sql and "dl_watch_events" in sql:
                return [
                    {"event_id": "1", "ts_kst": "2024-01-14T23:59:00+09:00", "base_date": "2024-01-15"},
                ]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            result = check_date_consistency("2024-01-15", config)
            assert result.passed is False
            assert result.failed_rows >= 1
            assert result.severity == "WARN"


class TestDQ005OrgRepoScope:
    """DQ005: target_orgs 외 범위 검증."""

    def test_pass_all_in_scope(self) -> None:
        config = _make_app_config()
        with patch(_PATCH_QUERY, side_effect=_mock_count_only):
            result = check_org_repo_scope("2024-01-15", config)
            assert result.rule_id == DQ005
            assert result.passed is True
            assert result.failed_rows == 0

    def test_fail_with_out_of_scope(self) -> None:
        config = _make_app_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if sql.strip().startswith("SELECT COUNT(*)"):
                return [{"cnt": 10}]
            if "organization" in sql and "NOT IN" in sql and "dl_watch_events" in sql:
                return [
                    {"event_id": "1", "organization": "other-org", "repo_name": "other-org/repo"},
                ]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            result = check_org_repo_scope("2024-01-15", config)
            assert result.passed is False
            assert result.failed_rows >= 1
            assert result.severity == "WARN"


class TestDQ006DailyStatsConsistency:
    """DQ006: DL 테이블 집계 vs daily_stats 정합성."""

    def test_pass_consistent(self) -> None:
        config = _make_d1_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if "daily_stats" in sql:
                return [
                    {"org_name": "pseudolab", "repo_name": "pseudolab/repo",
                     "event_type": "WatchEvent", "count": 5},
                ]
            if "dl_watch_events" in sql and "GROUP BY" in sql:
                return [{"org": "pseudolab", "repo_name": "pseudolab/repo", "cnt": 5}]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            report = check_daily_stats_consistency("2024-01-15", config)
            assert report.passed is True
            assert report.mismatched_keys == 0
            assert report.missing_in_stats == 0
            assert report.extra_in_stats == 0

    def test_fail_missing_in_stats(self) -> None:
        """DL 테이블에 있지만 daily_stats에 없는 경우."""
        config = _make_d1_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if "daily_stats" in sql:
                return [
                    {"org_name": "pseudolab", "repo_name": "pseudolab/repo",
                     "event_type": "WatchEvent", "count": 5},
                ]
            if "dl_watch_events" in sql and "GROUP BY" in sql:
                return [{"org": "pseudolab", "repo_name": "pseudolab/repo", "cnt": 5}]
            if "dl_fork_events" in sql and "GROUP BY" in sql:
                return [{"org": "pseudolab", "repo_name": "pseudolab/repo", "cnt": 2}]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            report = check_daily_stats_consistency("2024-01-15", config)
            assert report.passed is False
            assert report.missing_in_stats == 1

    def test_fail_extra_in_stats(self) -> None:
        """daily_stats에 있지만 DL 테이블에 없는 경우."""
        config = _make_d1_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if "daily_stats" in sql:
                return [
                    {"org_name": "pseudolab", "repo_name": "pseudolab/repo",
                     "event_type": "WatchEvent", "count": 5},
                    {"org_name": "pseudolab", "repo_name": "pseudolab/repo",
                     "event_type": "ForkEvent", "count": 1},
                ]
            if "dl_watch_events" in sql and "GROUP BY" in sql:
                return [{"org": "pseudolab", "repo_name": "pseudolab/repo", "cnt": 5}]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            report = check_daily_stats_consistency("2024-01-15", config)
            assert report.passed is False
            assert report.extra_in_stats == 1

    def test_fail_count_mismatch(self) -> None:
        """DL 집계와 daily_stats 카운트 불일치."""
        config = _make_d1_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if "daily_stats" in sql:
                return [
                    {"org_name": "pseudolab", "repo_name": "pseudolab/repo",
                     "event_type": "WatchEvent", "count": 3},
                ]
            if "dl_watch_events" in sql and "GROUP BY" in sql:
                return [{"org": "pseudolab", "repo_name": "pseudolab/repo", "cnt": 5}]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            report = check_daily_stats_consistency("2024-01-15", config)
            assert report.passed is False
            assert report.mismatched_keys == 1

    def test_push_uses_distinct_count(self) -> None:
        """push 테이블은 COUNT(DISTINCT event_id) 사용 확인."""
        config = _make_d1_config()
        sqls_captured: list[str] = []

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            sqls_captured.append(sql)
            if "daily_stats" in sql:
                return []
            if "dl_push_events" in sql and "GROUP BY" in sql:
                return [{"org": "pseudolab", "repo_name": "pseudolab/repo", "cnt": 5}]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            check_daily_stats_consistency("2024-01-15", config)

        push_sqls = [s for s in sqls_captured if "dl_push_events" in s]
        assert any("COUNT(DISTINCT event_id)" in s for s in push_sqls)


class TestRunQualityChecks:
    """run_quality_checks 통합 테스트."""

    def test_zero_events_returns_no_data(self) -> None:
        config = _make_app_config()
        with patch(_PATCH_QUERY, side_effect=_mock_zero_count):
            report = run_quality_checks("2024-01-15", config)
            assert report.passed is True
            assert report.reason == "NO_DATA"
            assert report.total_rules == 5
            assert report.failed_rules == 0

    def test_all_pass(self) -> None:
        config = _make_app_config()
        with patch(_PATCH_QUERY, side_effect=_mock_all_pass):
            report = run_quality_checks("2024-01-15", config)
            assert report.passed is True
            assert report.failed_rules == 0
            assert report.total_rules == 5

    def test_error_failure_makes_report_fail(self) -> None:
        """ERROR severity 규칙 실패 시 report.passed=False."""
        config = _make_app_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if sql.strip().startswith("SELECT COUNT(*)"):
                return [{"cnt": 10}]
            # DQ001 첫 번째 테이블에서 실패 행 반환 (ERROR severity)
            if "event_id IS NULL" in sql and DL_TABLES[0] in sql:
                return [
                    {"event_id": "", "user_login": "u", "repo_name": "r", "ts_kst": "t"},
                ]
            if "daily_stats" in sql:
                return []
            if "GROUP BY" in sql:
                return []
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            report = run_quality_checks("2024-01-15", config)
            assert report.passed is False
            assert report.failed_rules >= 1

    def test_warn_failure_does_not_fail_report(self) -> None:
        """WARN severity 규칙만 실패 시 report.passed=True."""
        config = _make_app_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if sql.strip().startswith("SELECT COUNT(*)"):
                return [{"cnt": 10}]
            # DQ003만 실패 (WARN severity)
            if "substr" in sql and "dl_watch_events" in sql:
                return [
                    {"event_id": "1", "ts_kst": "2024-01-14T23:59:00+09:00",
                     "base_date": "2024-01-15"},
                ]
            if "daily_stats" in sql:
                return []
            if "GROUP BY" in sql:
                return []
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            report = run_quality_checks("2024-01-15", config)
            assert report.passed is True  # WARN doesn't fail the report
            assert report.failed_rules >= 1

    def test_five_rules_executed(self) -> None:
        """DQ004 제거 후 5개 규칙만 실행 확인."""
        config = _make_app_config()
        with patch(_PATCH_QUERY, side_effect=_mock_all_pass):
            report = run_quality_checks("2024-01-15", config)
            assert report.total_rules == 5
            rule_ids = [r.rule_id for r in report.results]
            assert DQ001 in rule_ids
            assert DQ002 in rule_ids
            assert DQ003 in rule_ids
            assert DQ005 in rule_ids
            assert DQ006 in rule_ids


class TestConsistencyReport:
    """ConsistencyReport 결과 검증."""

    def test_no_mismatch_passed_true(self) -> None:
        config = _make_d1_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if "daily_stats" in sql:
                return [
                    {"org_name": "o", "repo_name": "r", "event_type": "WatchEvent", "count": 5},
                ]
            if "dl_watch_events" in sql and "GROUP BY" in sql:
                return [{"org": "o", "repo_name": "r", "cnt": 5}]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            report = check_daily_stats_consistency("2024-01-15", config)
            assert report.passed is True

    def test_mismatch_passed_false(self) -> None:
        config = _make_d1_config()

        def mock_qr(sql: str, params: list, cfg: Any) -> list[dict[str, Any]]:
            if "daily_stats" in sql:
                return [
                    {"org_name": "o", "repo_name": "r", "event_type": "WatchEvent", "count": 99},
                ]
            if "dl_watch_events" in sql and "GROUP BY" in sql:
                return [{"org": "o", "repo_name": "r", "cnt": 5}]
            return []

        with patch(_PATCH_QUERY, side_effect=mock_qr):
            report = check_daily_stats_consistency("2024-01-15", config)
            assert report.passed is False
            assert report.mismatched_keys == 1
