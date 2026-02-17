"""GitHub Archive 일일 ETL DAG.

매일 UTC 02:00에 전날의 GitHub Archive 데이터를 수집, 검증, 업로드한다.

Task 흐름:
  fetch → validate → [upload_r2, upload_d1] (병렬) → cleanup
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import pendulum
from airflow.sdk import dag, task
from airflow.operators.bash import BashOperator


# ─── 상수 ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # domains/github/ingestion/
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


# ─── 알림 콜백 ──────────────────────────────────────────

def _send_slack_alert(context: dict) -> None:
    """Task 실패 시 Slack Webhook으로 알림 전송."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return

    task_instance = context.get("task_instance")
    dag_run = context.get("dag_run")
    exception = context.get("exception")

    message = {
        "text": (
            f":x: *Airflow Task 실패*\n"
            f"• DAG: `{task_instance.dag_id}`\n"
            f"• Task: `{task_instance.task_id}`\n"
            f"• 실행 날짜: `{dag_run.logical_date}`\n"
            f"• 에러: `{exception}`\n"
            f"• <{task_instance.log_url}|로그 보기>"
        ),
    }

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(message).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)


# ─── DAG 정의 ───────────────────────────────────────────

DEFAULT_ARGS = {
    "owner": "pseudolab",
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
    "on_failure_callback": _send_slack_alert,
}


@dag(
    dag_id="github_archive_daily",
    description="GitHub Archive 일일 ETL: 수집 → 검증 → R2/D1 업로드",
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=True,
    max_active_runs=1,
    tags=["etl", "github-archive", "pseudolab"],
    default_args=DEFAULT_ARGS,
)
def github_archive_daily():

    # ── Task 1: fetch (다운로드 + 필터링) ──
    fetch = BashOperator(
        task_id="fetch",
        bash_command=(
            "gharchive-etl fetch "
            "--date {{ data_interval_start | ds }} "
            f"--output-jsonl {DATA_DIR}/{{{{ data_interval_start | ds }}}}.jsonl "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
        retries=3,
        retry_delay=pendulum.duration(minutes=3),
    )

    # ── Task 2: validate (JSONL 파일 검증) ──
    @task.short_circuit()
    def validate(**context) -> bool:
        """JSONL 파일 존재 및 비어있지 않음 확인.

        Returns:
            True: 이벤트가 존재하면 downstream 실행
            False: 파일이 없거나 비어있으면 downstream 스킵
        """
        ds = context["data_interval_start"].strftime("%Y-%m-%d")
        jsonl_path = DATA_DIR / f"{ds}.jsonl"

        if not jsonl_path.exists():
            print(f"[validate] {ds}: JSONL 파일 없음 — downstream 스킵")
            return False

        file_size = jsonl_path.stat().st_size
        if file_size == 0:
            print(f"[validate] {ds}: JSONL 파일이 비어있음 (이벤트 없음) — downstream 스킵")
            return False

        line_count = sum(1 for line in open(jsonl_path, "rb") if line.strip())
        print(f"[validate] {ds}: {line_count} events, {file_size:,} bytes")

        return True

    validate_result = validate()

    # ── Task 3: upload_r2 (R2 원본 업로드) ──
    upload_r2 = BashOperator(
        task_id="upload_r2",
        bash_command=(
            "gharchive-etl upload "
            "--date {{ data_interval_start | ds }} "
            f"--input-dir {DATA_DIR} "
            "--target r2 "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
    )

    # ── Task 4: upload_d1 (D1 적재) ──
    upload_d1 = BashOperator(
        task_id="upload_d1",
        bash_command=(
            "gharchive-etl upload "
            "--date {{ data_interval_start | ds }} "
            f"--input-dir {DATA_DIR} "
            "--target d1 "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
    )

    # ── Task 5: cleanup (임시 파일 정리) ──
    @task(trigger_rule="none_failed_min_one_success")
    def cleanup(**context) -> None:
        """JSONL 임시 파일 삭제.

        trigger_rule="none_failed_min_one_success": 업로드 실패 시 JSONL을 보존하고,
        이벤트 없어서 스킵된 경우에는 빈 파일을 정리한다.
        """
        ds = context["data_interval_start"].strftime("%Y-%m-%d")
        jsonl_path = DATA_DIR / f"{ds}.jsonl"

        if jsonl_path.exists():
            jsonl_path.unlink()
            print(f"[cleanup] 삭제됨: {jsonl_path}")
        else:
            print(f"[cleanup] 파일 없음 (이미 삭제됨): {jsonl_path}")

    # ── 의존성 그래프 ──
    fetch >> validate_result >> [upload_r2, upload_d1] >> cleanup()


# DAG 인스턴스 생성
github_archive_daily()
