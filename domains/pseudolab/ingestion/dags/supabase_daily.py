"""Supabase → D1 일일 배치 ETL DAG.

매일 KST 02:00 (UTC 17:00)에 Supabase 데이터를 D1으로 적재한다.

Task 흐름:
  resolve_batch_date → create_schema
    → [snapshot_tables TaskGroup, incremental_tables TaskGroup]
    → archive_to_r2 → daily_summary
"""

from __future__ import annotations

import os
from pathlib import Path

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task
from airflow.utils.task_group import TaskGroup

# ─── 상수 ───────────────────────────────────────────────
_domain_root = os.environ.get("PSEUDOLAB_INGESTION_ROOT")
PROJECT_ROOT = Path(_domain_root) if _domain_root else Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# ─── Slack 실패 알림 ────────────────────────────────────
_slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")
_failure_notifier = None

try:
    from pseudolab_etl.notify import build_slack_message, send_slack_webhook
except ImportError:
    pass

# ─── 테이블 목록 ────────────────────────────────────────
# DAG 파싱 시점에 레지스트리를 참조
try:
    from pseudolab_etl.table_registry import INCREMENTAL_TABLES, SNAPSHOT_TABLES
    _snapshot_names = sorted(SNAPSHOT_TABLES.keys())
    _incremental_names = sorted(INCREMENTAL_TABLES.keys())
except ImportError:
    _snapshot_names = []
    _incremental_names = []


# ─── DAG 정의 ───────────────────────────────────────────

DEFAULT_ARGS = {
    "owner": "pseudolab",
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
}


@dag(
    dag_id="supabase_daily",
    description="Supabase → D1 일일 ETL: 79개 테이블 수집",
    schedule="0 17 * * *",  # UTC 17:00 = KST 02:00
    start_date=pendulum.datetime(2026, 4, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["etl", "supabase", "pseudolab"],
    default_args=DEFAULT_ARGS,
)
def supabase_daily():

    @task(task_id="resolve_batch_date")
    def resolve_batch_date(**context) -> str:
        """전날 KST 기준일을 결정한다."""
        anchor_date = context.get("logical_date")

        if anchor_date is None:
            dag_run = context.get("dag_run")
            anchor_date = getattr(dag_run, "logical_date", None)

        if anchor_date is None:
            raise ValueError("batch date를 결정할 수 없습니다")

        return pendulum.instance(anchor_date).subtract(days=1).strftime("%Y-%m-%d")

    batch_date_template = "{{ ti.xcom_pull(task_ids='resolve_batch_date') }}"
    batch_date = resolve_batch_date()

    # ── create_schema (idempotent) ──
    create_schema = BashOperator(
        task_id="create_schema",
        bash_command=(
            f"pseudolab-etl create-schema --config {CONFIG_PATH} --json-log"
        ),
    )

    # ── TaskGroup: snapshot_tables (44개) ──
    with TaskGroup("snapshot_tables") as snapshot_group:
        for table_name in _snapshot_names:
            BashOperator(
                task_id=f"snapshot_{table_name}",
                bash_command=(
                    f"pseudolab-etl run "
                    f"--date {batch_date_template} "
                    f"--tables {table_name} "
                    f"--mode snapshot "
                    f"--config {CONFIG_PATH} "
                    f"--json-log"
                ),
                trigger_rule="all_done",
                retries=2,
                retry_delay=pendulum.duration(minutes=3),
            )

    # ── TaskGroup: incremental_tables (35개) ──
    with TaskGroup("incremental_tables") as incremental_group:
        for table_name in _incremental_names:
            BashOperator(
                task_id=f"incr_{table_name}",
                bash_command=(
                    f"pseudolab-etl run "
                    f"--date {batch_date_template} "
                    f"--tables {table_name} "
                    f"--mode incremental "
                    f"--config {CONFIG_PATH} "
                    f"--json-log"
                ),
                trigger_rule="all_done",
                retries=2,
                retry_delay=pendulum.duration(minutes=3),
            )

    # ── archive_to_r2 ──
    archive_to_r2 = BashOperator(
        task_id="archive_to_r2",
        bash_command=(
            f"pseudolab-etl archive --config {CONFIG_PATH} --json-log"
        ),
        trigger_rule="all_done",
    )

    # ── daily_summary ──
    @task(trigger_rule="all_done")
    def daily_summary(batch_date: str) -> None:
        """일일 실행 요약을 Slack으로 전송."""
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        if not webhook_url:
            print("[daily_summary] SLACK_WEBHOOK_URL 미설정 — 스킵")
            return

        from pseudolab_etl.notify import DailySummary, build_slack_message, send_slack_webhook

        summary = DailySummary(
            batch_date=batch_date,
            tables_total=len(_snapshot_names) + len(_incremental_names),
        )
        message = build_slack_message(summary)
        send_slack_webhook(message, webhook_url)
        print(f"[daily_summary] {batch_date}: Slack 전송 완료")

    summary_task = daily_summary(batch_date)

    # ── 의존성 그래프 ──
    batch_date >> create_schema
    create_schema >> [snapshot_group, incremental_group]
    [snapshot_group, incremental_group] >> archive_to_r2 >> summary_task


# DAG 인스턴스 생성
supabase_daily()
