"""Cloudflare 서비스 사용량 수집 및 임계치 판정 모듈.

Workers, D1, R2 사용량을 Cloudflare GraphQL Analytics API + REST API로 수집하고
임계치 초과 시 알림을 전송한다.

Free tier 한도 기준:
- Workers: 100,000 requests/day
- D1: 5,000,000 rows read/day, 100,000 rows written/day, 5GB storage
- R2: 10GB storage, 1,000,000 Class A ops/month, 10,000,000 Class B ops/month
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_CF_API_BASE = "https://api.cloudflare.com/client/v4/accounts"
_CF_GRAPHQL = "https://api.cloudflare.com/client/v4/graphql"

# R2 operation classification (Cloudflare pricing 기준)
_R2_CLASS_B_ACTIONS = frozenset({
    "GetObject", "HeadObject", "HeadBucket", "GetBucketLocation",
})


@dataclass
class UsageMetric:
    """Cloudflare 서비스 사용량 메트릭."""

    service: str
    current: int
    limit: int
    usage_rate: float  # 0.0 ~ 1.0
    exceeded_threshold: bool
    group: str = ""       # "Workers", "D1", "R2"
    unit: str = "count"   # "count" | "bytes"


def format_bytes(b: int) -> str:
    """바이트 값을 읽기 쉬운 단위로 변환."""
    if b >= 1_000_000_000:
        return f"{b / 1_000_000_000:.1f} GB"
    if b >= 1_000_000:
        return f"{b / 1_000_000:.1f} MB"
    if b >= 1_000:
        return f"{b / 1_000:.1f} KB"
    return f"{b} B"


def _format_metric_value(m: UsageMetric) -> str:
    """메트릭 값을 표시 문자열로 변환."""
    if m.unit == "bytes":
        return f"{format_bytes(m.current)} / {format_bytes(m.limit)}"
    return f"{m.current:,} / {m.limit:,}"


def _query_graphql(
    client: httpx.Client,
    query: str,
) -> dict[str, Any] | None:
    """Cloudflare GraphQL Analytics API 쿼리."""
    try:
        resp = client.post(_CF_GRAPHQL, json={"query": query})
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors"):
            logger.warning("GraphQL errors: %s", data["errors"])
            return None
        return data.get("data")
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning("GraphQL query failed: %s", e)
        return None


def _collect_workers_usage(
    client: httpx.Client,
    account_id: str,
) -> list[UsageMetric]:
    """Workers 사용량 수집: 오늘 요청 수."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    query = (
        '{ viewer { accounts(filter: {accountTag: "%s"}) {'
        " workersInvocationsAdaptive("
        '   filter: {datetime_geq: "%s", datetime_leq: "%s"}'
        "   limit: 10000"
        " ) { sum { requests subrequests errors } }"
        "}}}"
    ) % (account_id, today_start.isoformat(), now.isoformat())

    data = _query_graphql(client, query)
    if not data:
        return []

    try:
        accounts = data["viewer"]["accounts"]
        if not accounts:
            return []
        invocations = accounts[0].get("workersInvocationsAdaptive", [])
        total_requests = sum(inv["sum"]["requests"] for inv in invocations)
    except (KeyError, IndexError, TypeError) as e:
        logger.warning("Failed to parse Workers usage: %s", e)
        return []

    limit = 100_000
    return [
        UsageMetric(
            service="Requests (today)",
            current=total_requests,
            limit=limit,
            usage_rate=total_requests / limit,
            exceeded_threshold=False,
            group="Workers",
            unit="count",
        )
    ]


def _collect_d1_usage(
    client: httpx.Client,
    account_id: str,
) -> list[UsageMetric]:
    """D1 사용량 수집: rows read/written (오늘), storage (REST)."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    metrics: list[UsageMetric] = []

    # GraphQL: rows read / written (today)
    query = (
        '{ viewer { accounts(filter: {accountTag: "%s"}) {'
        " d1AnalyticsAdaptiveGroups("
        '   filter: {date_geq: "%s", date_leq: "%s"}'
        "   limit: 10000"
        " ) { sum { readQueries writeQueries rowsRead rowsWritten } }"
        "}}}"
    ) % (account_id, today_str, today_str)

    data = _query_graphql(client, query)
    if data:
        try:
            accounts = data["viewer"]["accounts"]
            if accounts:
                groups = accounts[0].get("d1AnalyticsAdaptiveGroups", [])
                total_rows_read = sum(g["sum"]["rowsRead"] for g in groups)
                total_rows_written = sum(g["sum"]["rowsWritten"] for g in groups)

                read_limit = 5_000_000
                write_limit = 100_000
                metrics.extend([
                    UsageMetric(
                        service="Rows Read (today)",
                        current=total_rows_read,
                        limit=read_limit,
                        usage_rate=total_rows_read / read_limit,
                        exceeded_threshold=False,
                        group="D1",
                        unit="count",
                    ),
                    UsageMetric(
                        service="Rows Written (today)",
                        current=total_rows_written,
                        limit=write_limit,
                        usage_rate=total_rows_written / write_limit,
                        exceeded_threshold=False,
                        group="D1",
                        unit="count",
                    ),
                ])
        except (KeyError, IndexError, TypeError) as e:
            logger.warning("Failed to parse D1 analytics: %s", e)

    # REST: D1 storage (file_size 합산)
    try:
        url = f"{_CF_API_BASE}/{account_id}/d1/database"
        resp = client.get(url)
        resp.raise_for_status()
        body = resp.json()
        if body.get("success") and isinstance(body.get("result"), list):
            total_size = sum(db.get("file_size", 0) for db in body["result"])
            storage_limit = 5_000_000_000  # 5GB
            metrics.append(
                UsageMetric(
                    service="Storage",
                    current=total_size,
                    limit=storage_limit,
                    usage_rate=total_size / storage_limit,
                    exceeded_threshold=False,
                    group="D1",
                    unit="bytes",
                )
            )
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning("Failed to collect D1 storage: %s", e)

    return metrics


def _collect_r2_usage(
    client: httpx.Client,
    account_id: str,
) -> list[UsageMetric]:
    """R2 사용량 수집: storage, Class A/B operations."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    metrics: list[UsageMetric] = []

    # GraphQL: storage
    storage_query = (
        '{ viewer { accounts(filter: {accountTag: "%s"}) {'
        " r2StorageAdaptiveGroups("
        '   filter: {date_geq: "%s", date_leq: "%s"}'
        "   limit: 1"
        " ) { max { payloadSize objectCount } }"
        "}}}"
    ) % (account_id, today_str, today_str)

    data = _query_graphql(client, storage_query)
    if data:
        try:
            accounts = data["viewer"]["accounts"]
            if accounts:
                groups = accounts[0].get("r2StorageAdaptiveGroups", [])
                if groups:
                    payload_size = groups[0]["max"]["payloadSize"]
                    storage_limit = 10_000_000_000  # 10GB
                    metrics.append(
                        UsageMetric(
                            service="Storage",
                            current=payload_size,
                            limit=storage_limit,
                            usage_rate=payload_size / storage_limit,
                            exceeded_threshold=False,
                            group="R2",
                            unit="bytes",
                        )
                    )
        except (KeyError, IndexError, TypeError) as e:
            logger.warning("Failed to parse R2 storage: %s", e)

    # GraphQL: operations by actionType (this month)
    ops_query = (
        '{ viewer { accounts(filter: {accountTag: "%s"}) {'
        " r2OperationsAdaptiveGroups("
        '   filter: {datetime_geq: "%s", datetime_leq: "%s"}'
        "   limit: 10000"
        " ) { dimensions { actionType } sum { requests } }"
        "}}}"
    ) % (account_id, month_start.isoformat(), now.isoformat())

    data = _query_graphql(client, ops_query)
    if data:
        try:
            accounts = data["viewer"]["accounts"]
            if accounts:
                groups = accounts[0].get("r2OperationsAdaptiveGroups", [])
                class_a_total = 0
                class_b_total = 0
                for g in groups:
                    action = g["dimensions"]["actionType"]
                    reqs = g["sum"]["requests"]
                    if action in _R2_CLASS_B_ACTIONS:
                        class_b_total += reqs
                    else:
                        # Class B 외 모든 액션 → Class A (보수적 추정)
                        class_a_total += reqs

                class_a_limit = 1_000_000
                class_b_limit = 10_000_000
                metrics.extend([
                    UsageMetric(
                        service="Class A Ops (month)",
                        current=class_a_total,
                        limit=class_a_limit,
                        usage_rate=class_a_total / class_a_limit,
                        exceeded_threshold=False,
                        group="R2",
                        unit="count",
                    ),
                    UsageMetric(
                        service="Class B Ops (month)",
                        current=class_b_total,
                        limit=class_b_limit,
                        usage_rate=class_b_total / class_b_limit,
                        exceeded_threshold=False,
                        group="R2",
                        unit="count",
                    ),
                ])
        except (KeyError, IndexError, TypeError) as e:
            logger.warning("Failed to parse R2 operations: %s", e)

    return metrics


def collect_cloudflare_usage(
    account_id: str,
    api_token: str,
) -> list[UsageMetric]:
    """Cloudflare GraphQL/REST API로 Workers/D1/R2 사용량 수집.

    실패 시 빈 리스트 반환 + 로그 기록.
    """
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    metrics: list[UsageMetric] = []

    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            for collector in (_collect_workers_usage, _collect_d1_usage, _collect_r2_usage):
                try:
                    metrics.extend(collector(client, account_id))
                except Exception as e:
                    logger.warning("Failed in %s: %s", getattr(collector, "__name__", "collector"), e)

    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error("Failed to create HTTP client for usage collection: %s", e)

    return metrics


def evaluate_thresholds(
    metrics: list[UsageMetric],
    threshold: float = 0.8,
) -> list[UsageMetric]:
    """임계치(기본 80%) 초과 항목 필터링."""
    exceeded: list[UsageMetric] = []
    for m in metrics:
        if m.usage_rate >= threshold:
            exceeded.append(
                UsageMetric(
                    service=m.service,
                    current=m.current,
                    limit=m.limit,
                    usage_rate=m.usage_rate,
                    exceeded_threshold=True,
                    group=m.group,
                    unit=m.unit,
                )
            )
    return exceeded


def build_usage_report(
    metrics: list[UsageMetric],
    threshold: float = 0.8,
) -> "AlertMessage":
    """모든 서비스 사용량을 서비스 그룹별로 정리한 리포트 생성.

    초과 항목이 있으면 WARN, 없으면 INFO 레벨.
    """
    from gharchive_etl.notify import AlertMessage

    exceeded = evaluate_thresholds(metrics, threshold)
    level: str = "WARN" if exceeded else "INFO"

    # 그룹별 정리
    groups: dict[str, list[UsageMetric]] = {}
    for m in metrics:
        groups.setdefault(m.group or "Other", []).append(m)

    lines: list[str] = []
    for group_name, group_metrics in groups.items():
        lines.append(f"*{group_name}*")
        for m in group_metrics:
            marker = " :warning:" if m.usage_rate >= threshold else ""
            value_str = _format_metric_value(m)
            lines.append(f"  {m.service}: {value_str} ({m.usage_rate:.1%}){marker}")

    if exceeded:
        lines.append(
            f"\n{len(exceeded)} metric(s) exceeded threshold ({threshold:.0%})"
        )
    else:
        lines.append(f"\nAll services within limits (threshold: {threshold:.0%})")

    return AlertMessage(
        level=level,
        title="Cloudflare Usage Report (Hourly)",
        text="\n".join(lines),
        context={
            "threshold": threshold,
            "exceeded_count": len(exceeded),
            "metrics_count": len(metrics),
        },
    )


def check_and_alert_usage(
    account_id: str,
    api_token: str,
    webhook_url: str | None = None,
    threshold: float = 0.8,
) -> list[UsageMetric]:
    """사용량 수집 -> 리포트 생성 -> 항상 알림 전송 통합 함수."""
    from gharchive_etl.notify import send_slack_webhook

    metrics = collect_cloudflare_usage(account_id, api_token)

    if not metrics:
        logger.warning("No metrics collected — skipping report")
        return []

    report = build_usage_report(metrics, threshold)

    if webhook_url:
        send_slack_webhook(report, webhook_url)
    else:
        logger.info("No webhook URL — skipping Slack notification")

    return metrics
