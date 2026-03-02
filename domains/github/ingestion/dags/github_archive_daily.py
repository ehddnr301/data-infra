"""GitHub Archive 일일 ETL DAG.

매일 UTC 02:00에 전날의 GitHub Archive 데이터를 수집, 검증, 업로드한다.

Task 흐름:
  fetch → validate → [upload_r2, upload_d1]
  upload_d1 → verify_aggregation → enrich_details → quality_check → daily_summary → cleanup
  upload_r2 → cleanup
"""

from __future__ import annotations

import os
from pathlib import Path

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task


# ─── 상수 ───────────────────────────────────────────────
_domain_root = os.environ.get("GITHUB_INGESTION_ROOT")
PROJECT_ROOT = Path(_domain_root) if _domain_root else Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

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
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
    **({"on_failure_callback": _failure_notifier} if _failure_notifier else {}),
}


@dag(
    dag_id="github_archive_daily",
    description="GitHub Archive 일일 ETL: 수집 → 검증 → R2/D1 업로드",
    schedule="0 3 * * *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=True,
    max_active_runs=1,
    tags=["etl", "github-archive", "pseudolab"],
    default_args=DEFAULT_ARGS,
)
def github_archive_daily():
    @task(task_id="resolve_batch_date")
    def resolve_batch_date(**context) -> str:
        anchor_date = context.get("logical_date")

        if anchor_date is None:
            dag_run = context.get("dag_run")
            anchor_date = getattr(dag_run, "logical_date", None)

        if anchor_date is None:
            run_id = context.get("run_id")
            if isinstance(run_id, str) and "__" in run_id:
                _, _, timestamp_part = run_id.partition("__")
                try:
                    anchor_date = pendulum.parse(timestamp_part)
                except Exception:
                    pass

        if anchor_date is None:
            raise ValueError("batch date를 컨텍스트에서 결정할 수 없습니다")

        return pendulum.instance(anchor_date).subtract(days=1).strftime("%Y-%m-%d")

    batch_date_template = "{{ ti.xcom_pull(task_ids='resolve_batch_date') }}"
    batch_date = resolve_batch_date()

    # ── Task 1: fetch (다운로드 + 필터링) ──
    fetch = BashOperator(
        task_id="fetch",
        bash_command=(
            "gharchive-etl fetch "
            f"--date {batch_date_template} "
            f"--output-jsonl {DATA_DIR}/{batch_date_template}.jsonl "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
        retries=3,
        retry_delay=pendulum.duration(minutes=3),
    )

    # ── Task 2: validate (JSONL 파일 검증) ──
    @task.short_circuit()
    def validate(batch_date: str) -> bool:
        """JSONL 파일 존재 및 비어있지 않음 확인.

        Returns:
            True: 이벤트가 존재하면 downstream 실행
            False: 파일이 없거나 비어있으면 downstream 스킵
        """
        jsonl_path = DATA_DIR / f"{batch_date}.jsonl"

        if not jsonl_path.exists():
            print(f"[validate] {batch_date}: JSONL 파일 없음 — downstream 스킵")
            return False

        file_size = jsonl_path.stat().st_size
        if file_size == 0:
            print(f"[validate] {batch_date}: JSONL 파일이 비어있음 (이벤트 없음) — downstream 스킵")
            return False

        line_count = sum(1 for line in open(jsonl_path, "rb") if line.strip())
        print(f"[validate] {batch_date}: {line_count} events, {file_size:,} bytes")

        return True

    validate_result = validate(batch_date)

    # ── Task 3: upload_r2 (R2 원본 업로드) ──
    upload_r2 = BashOperator(
        task_id="upload_r2",
        bash_command=(
            "gharchive-etl upload "
            f"--date {batch_date_template} "
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
            f"--date {batch_date_template} "
            f"--input-dir {DATA_DIR} "
            "--target d1 "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
    )

    # ── Task 5: verify_aggregation (집계 정합성 검증) ──
    verify_aggregation = BashOperator(
        task_id="verify_aggregation",
        bash_command=(
            "gharchive-etl verify-aggregation "
            f"--date {batch_date_template} "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
    )

    # ── Task 5.5: enrich_details (GitHub API 상세 데이터 수집) ──
    enrich_details = BashOperator(
        task_id="enrich_details",
        bash_command=(
            "gharchive-etl enrich "
            f"--date {batch_date_template} "
            "--priority all "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
        retries=1,
        retry_delay=pendulum.duration(minutes=5),
    )

    # ── Task 6: quality_check (데이터 품질 검증) ──
    quality_check = BashOperator(
        task_id="quality_check",
        bash_command=(
            f"gharchive-etl quality-check --date {batch_date_template} --config {CONFIG_PATH} --json-log"
        ),
    )

    # ── Task 6.5: sync_catalog (카탈로그 메타데이터 동기화, soft-fail) ──
    sync_catalog = BashOperator(
        task_id="sync_catalog",
        bash_command=(
            "gharchive-etl sync-catalog "
            f"--date {batch_date_template} "
            f"--status-file {DATA_DIR}/{batch_date_template}.sync-catalog.json "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
    )

    def _collect_sync_errors(ds: str) -> list[str] | None:
        status_path = DATA_DIR / f"{ds}.sync-catalog.json"
        if not status_path.exists():
            return None

        try:
            import json

            payload = json.loads(status_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return [f"sync-catalog status read failed: {exc}"]

        errors = payload.get("errors")
        if not isinstance(errors, list):
            return None

        return [str(error) for error in errors]

    # ── Task 7: daily_summary (일일 실행 요약 Slack 전송) ──
    @task(trigger_rule="none_failed_min_one_success")
    def daily_summary(batch_date: str) -> None:
        """일일 실행 요약을 Slack으로 전송."""
        from gharchive_etl.notify import build_daily_summary, send_slack_webhook

        webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        if not webhook_url:
            print("[daily_summary] SLACK_WEBHOOK_URL 미설정 — 요약 스킵")
            return

        # JSONL 파일에서 실제 이벤트 수 계산
        jsonl_path = DATA_DIR / f"{batch_date}.jsonl"
        events_count = 0
        if jsonl_path.exists():
            events_count = sum(1 for line in open(jsonl_path, "rb") if line.strip())

        summary = build_daily_summary(
            batch_date=batch_date,
            events_count=events_count,
            upload_success=True,
            quality_passed=True,
            errors=_collect_sync_errors(batch_date),
        )
        send_slack_webhook(summary, webhook_url)
        print(f"[daily_summary] {batch_date}: Slack 요약 전송 완료 ({events_count} events)")

    # ── Task 8: cleanup (임시 파일 정리) ──
    @task(trigger_rule="none_failed_min_one_success")
    def cleanup(batch_date: str) -> None:
        """JSONL 임시 파일 삭제.

        trigger_rule="none_failed_min_one_success": 업로드 실패 시 JSONL을 보존하고,
        이벤트 없어서 스킵된 경우에는 빈 파일을 정리한다.
        """
        jsonl_path = DATA_DIR / f"{batch_date}.jsonl"
        sync_status_path = DATA_DIR / f"{batch_date}.sync-catalog.json"

        if jsonl_path.exists():
            jsonl_path.unlink()
            print(f"[cleanup] 삭제됨: {jsonl_path}")
        else:
            print(f"[cleanup] 파일 없음 (이미 삭제됨): {jsonl_path}")

        if sync_status_path.exists():
            sync_status_path.unlink()
            print(f"[cleanup] 삭제됨: {sync_status_path}")

    # ── 의존성 그래프 ──
    # fetch → validate → [upload_r2, upload_d1]
    # upload_d1 → verify_aggregation → quality_check → sync_catalog → daily_summary → cleanup
    # upload_r2 → cleanup
    summary_task = daily_summary(batch_date)
    cleanup_task = cleanup(batch_date)

    batch_date >> fetch
    fetch >> validate_result >> [upload_r2, upload_d1]
    (
        upload_d1
        >> verify_aggregation
        >> enrich_details
        >> quality_check
        >> sync_catalog
        >> summary_task
        >> cleanup_task
    )
    upload_r2 >> cleanup_task


# DAG 인스턴스 생성
github_archive_daily()
