"""Discord 일일 ETL DAG.

매일 UTC 03:00에 Discord 채널 메시지를 수집, 업로드, 검증한다.

Task 흐름:
  fetch → validate → [upload_r2, upload_d1]
  upload_d1 → quality_check → summary → cleanup
  upload_r2 → cleanup

  TODO: on_failure_callback 괜찮은지 점검
"""

from __future__ import annotations

import os
from pathlib import Path

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

# ─── 상수 ───────────────────────────────────────────────
_domain_root = os.environ.get("DISCORD_INGESTION_ROOT")
PROJECT_ROOT = Path(_domain_root) if _domain_root else Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# ─── Slack 실패 알림 (GitHub DAG과 동일 패턴) ─────────────
_slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")

try:
    from gharchive_etl.notify import SlackWebhookNotifier

    _failure_notifier = SlackWebhookNotifier(webhook_url=_slack_url) if _slack_url else None
except ImportError:
    _failure_notifier = None


# ─── DAG 정의 ───────────────────────────────────────────

DEFAULT_ARGS = {
    "owner": "pseudolab",
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
    **({"on_failure_callback": _failure_notifier} if _failure_notifier else {}),
}


@dag(
    dag_id="discord_daily",
    description="Discord 일일 ETL: 수집 → 검증 → R2/D1 업로드",
    schedule="0 3 * * *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["etl", "discord", "pseudolab"],
    default_args=DEFAULT_ARGS,
)
def discord_daily():

    # ── Task 1: fetch (Discord API → JSONL) ──
    fetch = BashOperator(
        task_id="fetch",
        bash_command=(
            "discord-etl fetch "
            f"--output-dir {DATA_DIR} "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
        retries=3,
        retry_delay=pendulum.duration(minutes=3),
    )

    # ── Task 2: validate (JSONL 파일 검증) ──
    @task.short_circuit()
    def validate(**context) -> bool:
        """JSONL 파일 존재 및 비어있지 않음 확인."""
        ds = context["data_interval_start"].strftime("%Y-%m-%d")

        channel_dirs = [p for p in DATA_DIR.iterdir() if p.is_dir()]
        if not channel_dirs:
            print(f"[validate] {ds}: 채널 디렉토리 없음 — downstream 스킵")
            return False

        total_lines = 0
        for channel_dir in channel_dirs:
            jsonl_path = channel_dir / f"{ds}.jsonl"
            if jsonl_path.exists():
                with open(jsonl_path, "rb") as fh:
                    total_lines += sum(1 for line in fh if line.strip())

        if total_lines == 0:
            print(f"[validate] {ds}: 수집된 메시지 없음 — downstream 스킵")
            return False

        print(f"[validate] {ds}: {total_lines} messages across {len(channel_dirs)} channels")
        return True

    validate_result = validate()

    # ── Task 3: upload_r2 (R2 원본 업로드) ──
    upload_r2 = BashOperator(
        task_id="upload_r2",
        bash_command=(
            "discord-etl upload "
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
            "discord-etl upload "
            "--date {{ data_interval_start | ds }} "
            f"--input-dir {DATA_DIR} "
            "--target d1 "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
    )

    # ── Task 5: quality_check (데이터 품질 검증) ──
    quality_check = BashOperator(
        task_id="quality_check",
        bash_command=(
            "discord-etl quality-check "
            "--date {{ data_interval_start | ds }} "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
    )

    # ── Task 6: summary (Slack 알림) ──
    @task(trigger_rule="none_failed_min_one_success")
    def summary(**context) -> None:
        """일일 수집 결과를 Slack으로 전송."""
        from gharchive_etl.notify import AlertMessage, send_slack_webhook

        ds = context["data_interval_start"].strftime("%Y-%m-%d")
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        if not webhook_url:
            print("[summary] SLACK_WEBHOOK_URL 미설정 — 요약 스킵")
            return

        total_messages = 0
        for channel_dir in DATA_DIR.iterdir():
            if not channel_dir.is_dir():
                continue
            jsonl_path = channel_dir / f"{ds}.jsonl"
            if jsonl_path.exists():
                with open(jsonl_path, "rb") as fh:
                    total_messages += sum(1 for line in fh if line.strip())

        alert = AlertMessage(
            level="INFO",
            title="Discord 일일 수집 완료",
            text=(
                f"날짜: {ds}\n"
                f"수집 메시지: {total_messages}건"
            ),
        )
        send_slack_webhook(alert, webhook_url)
        print(f"[summary] {ds}: Slack 전송 완료 ({total_messages} messages)")

    # ── Task 7: cleanup (임시 파일 정리) ──
    @task(trigger_rule="none_failed_min_one_success")
    def cleanup(**context) -> None:
        """JSONL 임시 파일 삭제."""
        ds = context["data_interval_start"].strftime("%Y-%m-%d")

        for channel_dir in DATA_DIR.iterdir():
            if not channel_dir.is_dir():
                continue
            jsonl_path = channel_dir / f"{ds}.jsonl"
            if jsonl_path.exists():
                jsonl_path.unlink()
                print(f"[cleanup] 삭제됨: {jsonl_path}")

    summary_task = summary()
    cleanup_task = cleanup()

    # ── 의존성 그래프 ──
    # fetch → validate → [upload_r2, upload_d1]
    # upload_d1 → quality_check → summary → cleanup
    # upload_r2 → cleanup
    fetch >> validate_result >> [upload_r2, upload_d1]
    upload_d1 >> quality_check >> summary_task >> cleanup_task
    upload_r2 >> cleanup_task


# DAG 인스턴스 생성
discord_daily()
