"""Cloudflare 사용량 매시 모니터링 DAG.

매시 정각에 Workers/D1/R2 사용량을 확인하고 Slack으로 리포트를 전송한다.

Task 흐름:
  check_usage (단일 태스크)
"""

from __future__ import annotations

import os

import pendulum
from airflow.operators.bash import BashOperator
from airflow.sdk import dag

# ─── Slack 실패 알림 (Airflow 3.0+ Notifier 패턴) ──────
_slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")

try:
    from gharchive_etl.notify import SlackWebhookNotifier

    _failure_notifier = SlackWebhookNotifier(webhook_url=_slack_url) if _slack_url else None
except ImportError:
    _failure_notifier = None

# ─── DAG 정의 ───────────────────────────────────────────

DEFAULT_ARGS = {
    "owner": "pseudolab",
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=2),
    **({"on_failure_callback": _failure_notifier} if _failure_notifier else {}),
}


@dag(
    dag_id="cloudflare_usage_hourly",
    description="Cloudflare 사용량 매시 모니터링: Workers/D1/R2 리포트",
    schedule="0 * * * *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["monitoring", "cloudflare", "pseudolab"],
    default_args=DEFAULT_ARGS,
)
def cloudflare_usage_hourly():

    BashOperator(
        task_id="check_usage",
        bash_command="gharchive-etl check-usage --threshold 0.8 --json-log",
    )


# DAG 인스턴스 생성
cloudflare_usage_hourly()
