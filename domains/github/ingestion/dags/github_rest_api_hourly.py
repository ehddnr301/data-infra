"""GitHub REST API Events 시간별 수집 DAG.

매시 10분에 GitHub REST API에서 이벤트를 수집하고 D1/R2에 적재한다.

Task 흐름:
  rest_fetch → [upload_r2, upload_d1]
  upload_d1 → enrich_details → quality_check → should_run_daily_sync → sync_catalog → daily_summary → cleanup
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
DATA_DIR = PROJECT_ROOT / "data" / "rest-api"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# ─── Slack 실패 알림 ──────────────────────────────────
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
    dag_id="github_rest_api_hourly",
    description="GitHub REST API Events 시간별 수집 → D1/R2 적재",
    schedule="10 * * * *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["etl", "github-rest-api", "hourly"],
    default_args=DEFAULT_ARGS,
)
def github_rest_api_hourly():
    def _resolve_target_hour_anchor(**context):
        """이 DAG 실행에서 처리할 '완료된 이전 1시간' 앵커를 계산한다."""
        data_interval_end = context.get("data_interval_end")
        if data_interval_end is not None:
            return pendulum.instance(data_interval_end).subtract(hours=1)

        dag_run = context.get("dag_run")
        dag_run_data_interval_end = getattr(dag_run, "data_interval_end", None)
        if dag_run_data_interval_end is not None:
            return pendulum.instance(dag_run_data_interval_end).subtract(hours=1)

        logical_date = context.get("logical_date")
        if logical_date is not None:
            return pendulum.instance(logical_date).subtract(hours=1)

        dag_run_logical_date = getattr(dag_run, "logical_date", None)
        if dag_run_logical_date is not None:
            return pendulum.instance(dag_run_logical_date).subtract(hours=1)

        run_id = context.get("run_id")
        if isinstance(run_id, str) and "__" in run_id:
            _, _, timestamp_part = run_id.partition("__")
            try:
                return pendulum.parse(timestamp_part).subtract(hours=1)
            except Exception:
                pass

        raise ValueError("target hour anchor를 컨텍스트에서 결정할 수 없습니다")

    @task(task_id="resolve_run_ds")
    def resolve_run_ds(**context) -> str:
        anchor = _resolve_target_hour_anchor(**context)
        return anchor.strftime("%Y-%m-%d")

    @task(task_id="resolve_run_hour")
    def resolve_run_hour(**context) -> str:
        anchor = _resolve_target_hour_anchor(**context)
        return anchor.strftime("%H")

    run_ds_template = "{{ ti.xcom_pull(task_ids='resolve_run_ds') }}"
    run_hour_template = "{{ ti.xcom_pull(task_ids='resolve_run_hour') }}"
    run_ds = resolve_run_ds()
    run_hour = resolve_run_hour()

    # ── Task 1: rest_fetch (REST API 이벤트 수집) ──
    rest_fetch = BashOperator(
        task_id="rest_fetch",
        bash_command=(
            "gharchive-etl rest-fetch "
            f"--output-jsonl {DATA_DIR}/{run_ds_template}-{run_hour_template}.jsonl "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
        retries=3,
        retry_delay=pendulum.duration(minutes=3),
    )

    # ── Task 2: validate (JSONL 파일 검증) ──
    @task.short_circuit()
    def validate(run_ds: str, run_hour: str) -> bool:
        """JSONL 파일 존재 및 비어있지 않음 확인."""
        jsonl_file = DATA_DIR / f"{run_ds}-{run_hour}.jsonl"

        if not jsonl_file.exists():
            print(f"[validate] {run_ds}-{run_hour}: JSONL 파일 없음 — downstream 스킵")
            return False

        file_size = jsonl_file.stat().st_size
        if file_size == 0:
            print(f"[validate] {run_ds}-{run_hour}: JSONL 파일이 비어있음 — downstream 스킵")
            return False

        line_count = sum(1 for line in open(jsonl_file, "rb") if line.strip())
        print(f"[validate] {run_ds}-{run_hour}: {line_count} events, {file_size:,} bytes")
        return True

    validate_result = validate(run_ds, run_hour)

    @task.short_circuit(
        task_id="should_run_daily_sync",
        ignore_downstream_trigger_rules=False,
    )
    def should_run_daily_sync(run_hour: str) -> bool:
        return run_hour == "00"

    run_daily_sync = should_run_daily_sync(run_hour)

    # ── Task 3: upload_r2 (R2 원본 업로드) ──
    upload_r2 = BashOperator(
        task_id="upload_r2",
        bash_command=(
            "gharchive-etl upload "
            f"--date {run_ds_template} "
            f"--input-file {DATA_DIR}/{run_ds_template}-{run_hour_template}.jsonl "
            "--source rest_api "
            "--target r2 "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
    )

    # ── Task 4: upload_d1 (D1 적재, daily_stats 생략) ──
    upload_d1 = BashOperator(
        task_id="upload_d1",
        bash_command=(
            "gharchive-etl upload "
            f"--date {run_ds_template} "
            f"--input-file {DATA_DIR}/{run_ds_template}-{run_hour_template}.jsonl "
            "--source rest_api "
            "--target d1 "
            f"--config {CONFIG_PATH} "
            "--json-log"
        ),
    )

    # ── Task 5: enrich_details (GitHub API 상세 데이터 수집) ──
    enrich_details = BashOperator(
        task_id="enrich_details",
        bash_command=(
            "gharchive-etl enrich "
            f"--date {run_ds_template} "
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
            f"gharchive-etl quality-check --date {run_ds_template} --config {CONFIG_PATH} --json-log"
        ),
    )

    # ── Task 6.5: sync_catalog (카탈로그 메타데이터 동기화, soft-fail) ──
    sync_catalog = BashOperator(
        task_id="sync_catalog",
        bash_command=(
            "gharchive-etl sync-catalog "
            f"--date {run_ds_template} "
            f"--status-file {DATA_DIR}/{run_ds_template}.sync-catalog.json "
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

    # ── Task 6.7: daily_summary (UTC 00 sync 결과 요약) ──
    @task(trigger_rule="none_failed_min_one_success")
    def daily_summary(run_ds: str, run_hour: str) -> None:
        from gharchive_etl.notify import build_daily_summary, send_slack_webhook

        webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        if not webhook_url:
            print("[daily_summary] SLACK_WEBHOOK_URL 미설정 — 요약 스킵")
            return

        jsonl_file = DATA_DIR / f"{run_ds}-{run_hour}.jsonl"
        events_count = 0
        if jsonl_file.exists():
            events_count = sum(1 for line in open(jsonl_file, "rb") if line.strip())

        summary = build_daily_summary(
            batch_date=run_ds,
            events_count=events_count,
            upload_success=True,
            quality_passed=True,
            errors=_collect_sync_errors(run_ds),
        )
        send_slack_webhook(summary, webhook_url)
        print(f"[daily_summary] {run_ds}T{run_hour}: Slack 요약 전송 완료 ({events_count} events)")

    # ── Task 7: cleanup (JSONL 임시 파일 삭제) ──
    @task(trigger_rule="none_failed_min_one_success")
    def cleanup(run_ds: str, run_hour: str) -> None:
        """JSONL 임시 파일 삭제."""
        jsonl_file = DATA_DIR / f"{run_ds}-{run_hour}.jsonl"
        sync_status_file = DATA_DIR / f"{run_ds}.sync-catalog.json"

        if jsonl_file.exists():
            jsonl_file.unlink()
            print(f"[cleanup] 삭제됨: {jsonl_file}")
        else:
            print(f"[cleanup] 파일 없음: {jsonl_file}")

        if sync_status_file.exists():
            sync_status_file.unlink()
            print(f"[cleanup] 삭제됨: {sync_status_file}")

    summary_task = daily_summary(run_ds, run_hour)
    cleanup_task = cleanup(run_ds, run_hour)

    # ── 의존성 그래프 ──
    # rest_fetch → validate → [upload_r2, upload_d1]
    # upload_d1 → enrich_details → quality_check → should_run_daily_sync → sync_catalog → daily_summary → cleanup
    # upload_r2 → cleanup
    [run_ds, run_hour] >> rest_fetch
    rest_fetch >> validate_result >> [upload_r2, upload_d1]
    (
        upload_d1
        >> enrich_details
        >> quality_check
        >> run_daily_sync
        >> sync_catalog
        >> summary_task
        >> cleanup_task
    )
    upload_r2 >> cleanup_task


# DAG 인스턴스 생성
github_rest_api_hourly()
