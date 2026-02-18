"""Cloudflare 사용량 수집 및 모니터링 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import orjson
import pytest
from click.testing import CliRunner
from gharchive_etl.cli import main
from gharchive_etl.cloudflare_usage import (
    UsageMetric,
    _collect_d1_usage,
    _collect_r2_usage,
    _collect_workers_usage,
    _query_graphql,
    build_usage_report,
    check_and_alert_usage,
    collect_cloudflare_usage,
    evaluate_thresholds,
    format_bytes,
)


# ── 헬퍼 ──────────────────────────────────────────────


def _make_metric(
    service: str = "Requests (today)",
    current: int = 50_000,
    limit: int = 100_000,
    usage_rate: float = 0.5,
    exceeded: bool = False,
    group: str = "Workers",
    unit: str = "count",
) -> UsageMetric:
    return UsageMetric(
        service=service,
        current=current,
        limit=limit,
        usage_rate=usage_rate,
        exceeded_threshold=exceeded,
        group=group,
        unit=unit,
    )


def _mock_graphql_response(data: dict | None = None, errors: list | None = None) -> httpx.Response:
    """GraphQL API 응답 mock."""
    body: dict = {}
    if data is not None:
        body["data"] = data
    if errors is not None:
        body["errors"] = errors
    return httpx.Response(
        status_code=200,
        content=orjson.dumps(body),
        request=httpx.Request("POST", "https://api.cloudflare.com/client/v4/graphql"),
    )


def _mock_rest_response(result: list | dict | None = None, success: bool = True) -> httpx.Response:
    """REST API 응답 mock."""
    body = {"success": success, "result": result or []}
    return httpx.Response(
        status_code=200,
        content=orjson.dumps(body),
        request=httpx.Request("GET", "https://api.cloudflare.com/test"),
    )


# ── format_bytes 테스트 ──────────────────────────────


class TestFormatBytes:
    """바이트 포맷팅 테스트."""

    def test_gb(self) -> None:
        assert format_bytes(5_000_000_000) == "5.0 GB"

    def test_mb(self) -> None:
        assert format_bytes(3_500_000) == "3.5 MB"

    def test_kb(self) -> None:
        assert format_bytes(1_500) == "1.5 KB"

    def test_bytes(self) -> None:
        assert format_bytes(500) == "500 B"


# ── _query_graphql 테스트 ────────────────────────────


class TestQueryGraphql:
    """GraphQL 쿼리 헬퍼 테스트."""

    def test_success(self) -> None:
        """정상 응답 → data 반환."""
        expected = {"viewer": {"accounts": [{"foo": "bar"}]}}
        mock_client = MagicMock()
        mock_client.post.return_value = _mock_graphql_response(data=expected)

        result = _query_graphql(mock_client, "{ viewer { accounts { foo } } }")

        assert result == expected
        mock_client.post.assert_called_once()

    def test_graphql_errors(self) -> None:
        """GraphQL errors → None 반환."""
        mock_client = MagicMock()
        mock_client.post.return_value = _mock_graphql_response(
            data=None,
            errors=[{"message": "Some error"}],
        )

        result = _query_graphql(mock_client, "{ bad query }")
        assert result is None

    def test_http_error(self) -> None:
        """HTTP 에러 → None 반환."""
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        result = _query_graphql(mock_client, "{ query }")
        assert result is None


# ── _collect_workers_usage 테스트 ────────────────────


class TestCollectWorkersUsage:
    """Workers 사용량 수집 테스트."""

    def test_success(self) -> None:
        """정상 수집 → Requests 메트릭 반환."""
        gql_data = {
            "viewer": {
                "accounts": [{
                    "workersInvocationsAdaptive": [
                        {"sum": {"requests": 30_000, "subrequests": 100, "errors": 5}},
                        {"sum": {"requests": 20_000, "subrequests": 50, "errors": 2}},
                    ]
                }]
            }
        }
        mock_client = MagicMock()
        mock_client.post.return_value = _mock_graphql_response(data=gql_data)

        metrics = _collect_workers_usage(mock_client, "test-acc")

        assert len(metrics) == 1
        m = metrics[0]
        assert m.group == "Workers"
        assert m.service == "Requests (today)"
        assert m.current == 50_000
        assert m.limit == 100_000
        assert m.unit == "count"
        assert m.usage_rate == pytest.approx(0.5)

    def test_empty_accounts(self) -> None:
        """빈 accounts → 빈 리스트."""
        gql_data = {"viewer": {"accounts": []}}
        mock_client = MagicMock()
        mock_client.post.return_value = _mock_graphql_response(data=gql_data)

        metrics = _collect_workers_usage(mock_client, "test-acc")
        assert metrics == []

    def test_graphql_failure(self) -> None:
        """GraphQL 실패 → 빈 리스트."""
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("fail")

        metrics = _collect_workers_usage(mock_client, "test-acc")
        assert metrics == []


# ── _collect_d1_usage 테스트 ─────────────────────────


class TestCollectD1Usage:
    """D1 사용량 수집 테스트."""

    def test_success_all_metrics(self) -> None:
        """GraphQL(rows) + REST(storage) 모두 성공."""
        gql_data = {
            "viewer": {
                "accounts": [{
                    "d1AnalyticsAdaptiveGroups": [
                        {"sum": {"readQueries": 10, "writeQueries": 5, "rowsRead": 1_000_000, "rowsWritten": 20_000}},
                    ]
                }]
            }
        }
        rest_data = [
            {"uuid": "db1", "file_size": 500_000_000},
            {"uuid": "db2", "file_size": 200_000_000},
        ]

        mock_client = MagicMock()
        mock_client.post.return_value = _mock_graphql_response(data=gql_data)
        mock_client.get.return_value = _mock_rest_response(result=rest_data)

        metrics = _collect_d1_usage(mock_client, "test-acc")

        assert len(metrics) == 3
        by_service = {m.service: m for m in metrics}

        # Rows Read
        rr = by_service["Rows Read (today)"]
        assert rr.current == 1_000_000
        assert rr.limit == 5_000_000
        assert rr.group == "D1"
        assert rr.unit == "count"

        # Rows Written
        rw = by_service["Rows Written (today)"]
        assert rw.current == 20_000
        assert rw.limit == 100_000

        # Storage
        st = by_service["Storage"]
        assert st.current == 700_000_000
        assert st.limit == 5_000_000_000
        assert st.unit == "bytes"

    def test_graphql_failure_still_returns_storage(self) -> None:
        """GraphQL 실패해도 REST storage는 반환."""
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("fail")
        mock_client.get.return_value = _mock_rest_response(
            result=[{"uuid": "db1", "file_size": 100_000}]
        )

        metrics = _collect_d1_usage(mock_client, "test-acc")

        assert len(metrics) == 1
        assert metrics[0].service == "Storage"
        assert metrics[0].current == 100_000

    def test_rest_failure_still_returns_rows(self) -> None:
        """REST 실패해도 GraphQL rows는 반환."""
        gql_data = {
            "viewer": {
                "accounts": [{
                    "d1AnalyticsAdaptiveGroups": [
                        {"sum": {"readQueries": 1, "writeQueries": 1, "rowsRead": 500, "rowsWritten": 100}},
                    ]
                }]
            }
        }
        mock_client = MagicMock()
        mock_client.post.return_value = _mock_graphql_response(data=gql_data)
        mock_client.get.side_effect = httpx.ConnectError("fail")

        metrics = _collect_d1_usage(mock_client, "test-acc")

        assert len(metrics) == 2
        services = {m.service for m in metrics}
        assert services == {"Rows Read (today)", "Rows Written (today)"}


# ── _collect_r2_usage 테스트 ─────────────────────────


class TestCollectR2Usage:
    """R2 사용량 수집 테스트."""

    def test_success_all_metrics(self) -> None:
        """storage + operations 모두 성공."""
        storage_data = {
            "viewer": {
                "accounts": [{
                    "r2StorageAdaptiveGroups": [
                        {"max": {"payloadSize": 2_000_000_000, "objectCount": 500}}
                    ]
                }]
            }
        }
        ops_data = {
            "viewer": {
                "accounts": [{
                    "r2OperationsAdaptiveGroups": [
                        {"dimensions": {"actionType": "PutObject"}, "sum": {"requests": 50_000}},
                        {"dimensions": {"actionType": "GetObject"}, "sum": {"requests": 200_000}},
                        {"dimensions": {"actionType": "ListObjects"}, "sum": {"requests": 10_000}},
                        {"dimensions": {"actionType": "HeadObject"}, "sum": {"requests": 30_000}},
                    ]
                }]
            }
        }

        mock_client = MagicMock()
        mock_client.post.side_effect = [
            _mock_graphql_response(data=storage_data),
            _mock_graphql_response(data=ops_data),
        ]

        metrics = _collect_r2_usage(mock_client, "test-acc")

        assert len(metrics) == 3
        by_service = {m.service: m for m in metrics}

        # Storage
        st = by_service["Storage"]
        assert st.current == 2_000_000_000
        assert st.limit == 10_000_000_000
        assert st.unit == "bytes"
        assert st.group == "R2"

        # Class A (PutObject + ListObjects)
        ca = by_service["Class A Ops (month)"]
        assert ca.current == 60_000
        assert ca.limit == 1_000_000

        # Class B (GetObject + HeadObject)
        cb = by_service["Class B Ops (month)"]
        assert cb.current == 230_000
        assert cb.limit == 10_000_000

    def test_unknown_action_classified_as_class_a(self) -> None:
        """알 수 없는 actionType → Class A로 분류."""
        ops_data = {
            "viewer": {
                "accounts": [{
                    "r2OperationsAdaptiveGroups": [
                        {"dimensions": {"actionType": "UnknownAction"}, "sum": {"requests": 100}},
                    ]
                }]
            }
        }

        mock_client = MagicMock()
        mock_client.post.side_effect = [
            _mock_graphql_response(data={"viewer": {"accounts": [{"r2StorageAdaptiveGroups": []}]}}),
            _mock_graphql_response(data=ops_data),
        ]

        metrics = _collect_r2_usage(mock_client, "test-acc")

        by_service = {m.service: m for m in metrics}
        assert by_service["Class A Ops (month)"].current == 100
        assert by_service["Class B Ops (month)"].current == 0

    def test_empty_storage_groups(self) -> None:
        """r2StorageAdaptiveGroups 빈 리스트 → storage 메트릭 없음."""
        mock_client = MagicMock()
        mock_client.post.side_effect = [
            _mock_graphql_response(data={"viewer": {"accounts": [{"r2StorageAdaptiveGroups": []}]}}),
            _mock_graphql_response(data={"viewer": {"accounts": [{"r2OperationsAdaptiveGroups": []}]}}),
        ]

        metrics = _collect_r2_usage(mock_client, "test-acc")

        services = {m.service for m in metrics}
        assert "Storage" not in services
        # ops는 0이어도 반환
        assert "Class A Ops (month)" in services
        assert "Class B Ops (month)" in services


# ── collect_cloudflare_usage 테스트 ───────────────────


class TestCollectCloudflareUsage:
    """Cloudflare API 사용량 수집 통합 테스트."""

    def test_success_all_services(self) -> None:
        """모든 서비스 수집 성공."""
        with (
            patch(
                "gharchive_etl.cloudflare_usage._collect_workers_usage",
                return_value=[_make_metric(group="Workers", service="Requests (today)")],
            ),
            patch(
                "gharchive_etl.cloudflare_usage._collect_d1_usage",
                return_value=[
                    _make_metric(group="D1", service="Rows Read (today)"),
                    _make_metric(group="D1", service="Storage", unit="bytes", current=500_000_000, limit=5_000_000_000),
                ],
            ),
            patch(
                "gharchive_etl.cloudflare_usage._collect_r2_usage",
                return_value=[_make_metric(group="R2", service="Storage", unit="bytes", current=1_000_000_000, limit=10_000_000_000)],
            ),
        ):
            metrics = collect_cloudflare_usage("test-account", "test-token")

        assert len(metrics) == 4
        groups = {m.group for m in metrics}
        assert groups == {"Workers", "D1", "R2"}

    def test_partial_failure(self) -> None:
        """일부 서비스 수집 실패 → 나머지만 반환."""
        with (
            patch(
                "gharchive_etl.cloudflare_usage._collect_workers_usage",
                return_value=[_make_metric(group="Workers")],
            ),
            patch(
                "gharchive_etl.cloudflare_usage._collect_d1_usage",
                side_effect=Exception("D1 error"),
            ),
            patch(
                "gharchive_etl.cloudflare_usage._collect_r2_usage",
                return_value=[_make_metric(group="R2")],
            ),
        ):
            metrics = collect_cloudflare_usage("test-account", "test-token")

        assert len(metrics) == 2

    def test_total_failure(self) -> None:
        """HTTP 클라이언트 생성 실패 → 빈 리스트."""
        with patch("gharchive_etl.cloudflare_usage.httpx.Client") as mock_cls:
            mock_cls.side_effect = httpx.ConnectError("Connection refused")
            metrics = collect_cloudflare_usage("test-account", "test-token")

        assert metrics == []


# ── evaluate_thresholds 테스트 ────────────────────────


class TestEvaluateThresholds:
    """임계치 판정 테스트."""

    def test_no_exceeded(self) -> None:
        metrics = [
            _make_metric(service="Requests (today)", usage_rate=0.5),
            _make_metric(service="Rows Read (today)", group="D1", usage_rate=0.3),
        ]
        result = evaluate_thresholds(metrics, threshold=0.8)
        assert len(result) == 0

    def test_some_exceeded(self) -> None:
        metrics = [
            _make_metric(service="Requests (today)", usage_rate=0.9),
            _make_metric(service="Rows Read (today)", group="D1", usage_rate=0.3),
        ]
        result = evaluate_thresholds(metrics, threshold=0.8)
        assert len(result) == 1
        assert result[0].service == "Requests (today)"
        assert result[0].exceeded_threshold is True
        assert result[0].group == "Workers"  # group 보존 확인

    def test_boundary_value(self) -> None:
        metrics = [_make_metric(usage_rate=0.8)]
        result = evaluate_thresholds(metrics, threshold=0.8)
        assert len(result) == 1

    def test_empty_list(self) -> None:
        result = evaluate_thresholds([], threshold=0.8)
        assert result == []


# ── build_usage_report 테스트 ─────────────────────────


class TestBuildUsageReport:
    """사용량 리포트 생성 테스트."""

    def test_info_level_when_all_within_limits(self) -> None:
        """모든 서비스가 임계치 내 → INFO 레벨, 그룹별 표시."""
        metrics = [
            _make_metric(
                group="Workers", service="Requests (today)",
                current=45_000, limit=100_000, usage_rate=0.45,
            ),
            _make_metric(
                group="D1", service="Rows Read (today)",
                current=2_000_000, limit=5_000_000, usage_rate=0.4,
            ),
            _make_metric(
                group="D1", service="Storage",
                current=500_000_000, limit=5_000_000_000, usage_rate=0.1,
                unit="bytes",
            ),
            _make_metric(
                group="R2", service="Storage",
                current=1_000_000_000, limit=10_000_000_000, usage_rate=0.1,
                unit="bytes",
            ),
        ]
        report = build_usage_report(metrics, threshold=0.8)

        assert report.level == "INFO"
        assert "Cloudflare Usage Report" in report.title
        assert "All services within limits" in report.text
        # 그룹 헤더 확인
        assert "*Workers*" in report.text
        assert "*D1*" in report.text
        assert "*R2*" in report.text
        # 서비스 항목 확인
        assert "Requests (today)" in report.text
        assert "Rows Read (today)" in report.text
        # bytes 포맷
        assert "500.0 MB" in report.text
        assert "5.0 GB" in report.text
        assert report.context["exceeded_count"] == 0
        assert report.context["metrics_count"] == 4

    def test_warn_level_when_exceeded(self) -> None:
        """임계치 초과 항목 존재 → WARN 레벨."""
        metrics = [
            _make_metric(
                group="Workers", service="Requests (today)",
                current=90_000, limit=100_000, usage_rate=0.9,
            ),
            _make_metric(
                group="D1", service="Rows Read (today)",
                current=1_000, limit=5_000_000, usage_rate=0.0,
            ),
        ]
        report = build_usage_report(metrics, threshold=0.8)

        assert report.level == "WARN"
        assert ":warning:" in report.text
        assert "1 metric(s) exceeded" in report.text
        assert report.context["exceeded_count"] == 1

    def test_bytes_format_for_storage(self) -> None:
        """Storage 메트릭은 bytes 포맷."""
        metrics = [
            _make_metric(
                group="R2", service="Storage",
                current=2_500_000_000, limit=10_000_000_000, usage_rate=0.25,
                unit="bytes",
            ),
        ]
        report = build_usage_report(metrics, threshold=0.8)
        assert "2.5 GB / 10.0 GB" in report.text

    def test_count_format_for_ops(self) -> None:
        """count 메트릭은 콤마 구분 숫자 포맷."""
        metrics = [
            _make_metric(
                group="Workers", service="Requests (today)",
                current=45_000, limit=100_000, usage_rate=0.45,
            ),
        ]
        report = build_usage_report(metrics, threshold=0.8)
        assert "45,000 / 100,000" in report.text


# ── check_and_alert_usage 테스트 ──────────────────────


class TestCheckAndAlertUsage:
    """통합 함수 테스트."""

    def test_always_sends_report(self) -> None:
        """메트릭 수집 성공 시 항상 Slack 전송."""
        metrics = [_make_metric(group="Workers", usage_rate=0.3)]

        with (
            patch(
                "gharchive_etl.cloudflare_usage.collect_cloudflare_usage",
                return_value=metrics,
            ),
            patch("gharchive_etl.notify.send_slack_webhook") as mock_send,
        ):
            result = check_and_alert_usage(
                "acc", "token", webhook_url="https://hooks.slack.com/test"
            )

            mock_send.assert_called_once()
            assert len(result) == 1

    def test_skips_slack_when_no_webhook(self) -> None:
        """webhook_url 미설정 시 Slack 전송 스킵."""
        metrics = [_make_metric(group="Workers", usage_rate=0.3)]

        with (
            patch(
                "gharchive_etl.cloudflare_usage.collect_cloudflare_usage",
                return_value=metrics,
            ),
            patch("gharchive_etl.notify.send_slack_webhook") as mock_send,
        ):
            result = check_and_alert_usage("acc", "token", webhook_url=None)

            mock_send.assert_not_called()
            assert len(result) == 1

    def test_empty_metrics_returns_empty(self) -> None:
        """메트릭 수집 실패(빈 리스트) → 빈 리스트 반환, Slack 미전송."""
        with (
            patch(
                "gharchive_etl.cloudflare_usage.collect_cloudflare_usage",
                return_value=[],
            ),
            patch("gharchive_etl.notify.send_slack_webhook") as mock_send,
        ):
            result = check_and_alert_usage(
                "acc", "token", webhook_url="https://hooks.slack.com/test"
            )

            assert result == []
            mock_send.assert_not_called()


# ── CLI check-usage 테스트 ────────────────────────────


class TestCheckUsageCLI:
    """check-usage CLI 커맨드 테스트."""

    def test_success(self) -> None:
        """정상 실행 — 그룹별 출력 확인."""
        metrics = [
            _make_metric(
                group="Workers", service="Requests (today)",
                current=45_000, limit=100_000, usage_rate=0.45,
            ),
            _make_metric(
                group="D1", service="Rows Read (today)",
                current=2_000_000, limit=5_000_000, usage_rate=0.4,
            ),
            _make_metric(
                group="D1", service="Storage",
                current=500_000_000, limit=5_000_000_000, usage_rate=0.1,
                unit="bytes",
            ),
        ]
        env = {
            "CLOUDFLARE_ACCOUNT_ID": "test-acc",
            "CLOUDFLARE_API_TOKEN": "test-token",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
        }

        with patch(
            "gharchive_etl.cloudflare_usage.check_and_alert_usage",
            return_value=metrics,
        ):
            runner = CliRunner(env=env)
            result = runner.invoke(main, ["check-usage", "--no-json-log"])

            assert result.exit_code == 0, result.output
            assert "[Workers]" in result.output
            assert "[D1]" in result.output
            assert "Requests (today)" in result.output
            assert "3 metrics checked" in result.output

    def test_missing_auth_exits_1(self) -> None:
        """인증 환경변수 누락 시 exit 1."""
        env = {
            "CLOUDFLARE_ACCOUNT_ID": "",
            "CLOUDFLARE_API_TOKEN": "",
        }
        runner = CliRunner(env=env)
        result = runner.invoke(main, ["check-usage", "--no-json-log"])

        assert result.exit_code == 1
        assert "CLOUDFLARE_ACCOUNT_ID" in result.output

    def test_no_webhook_warns(self) -> None:
        """SLACK_WEBHOOK_URL 미설정 시 경고하지만 정상 실행."""
        metrics = [_make_metric(group="Workers", usage_rate=0.3)]
        env = {
            "CLOUDFLARE_ACCOUNT_ID": "test-acc",
            "CLOUDFLARE_API_TOKEN": "test-token",
            "SLACK_WEBHOOK_URL": "",
        }

        with patch(
            "gharchive_etl.cloudflare_usage.check_and_alert_usage",
            return_value=metrics,
        ):
            runner = CliRunner(env=env)
            result = runner.invoke(main, ["check-usage", "--no-json-log"])

            assert result.exit_code == 0, result.output

    def test_empty_metrics_exits_1(self) -> None:
        """메트릭 수집 실패 시 exit 1."""
        env = {
            "CLOUDFLARE_ACCOUNT_ID": "test-acc",
            "CLOUDFLARE_API_TOKEN": "test-token",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
        }

        with patch(
            "gharchive_etl.cloudflare_usage.check_and_alert_usage",
            return_value=[],
        ):
            runner = CliRunner(env=env)
            result = runner.invoke(main, ["check-usage", "--no-json-log"])

            assert result.exit_code == 1
            assert "Failed to collect" in result.output

    def test_help(self) -> None:
        """--help 출력 확인."""
        runner = CliRunner()
        result = runner.invoke(main, ["check-usage", "--help"])

        assert result.exit_code == 0
        assert "--threshold" in result.output
