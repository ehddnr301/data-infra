"""GitHub REST API Events 시간별 수집 DAG.

매시 10분에 GitHub REST API에서 이벤트를 수집하고 D1/R2에 적재한다.

Task 흐름:
  rest_fetch → [upload_r2, upload_d1]
  upload_d1 → enrich_details → quality_check → cleanup
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
    @task(task_id="resolve_run_ds")
    def resolve_run_ds(**context) -> str:
        logical_date = context.get("logical_date")
        if logical_date is not None:
            return logical_date.strftime("%Y-%m-%d")

        dag_run = context.get("dag_run")
        dag_run_logical_date = getattr(dag_run, "logical_date", None)
        if dag_run_logical_date is not None:
            return dag_run_logical_date.strftime("%Y-%m-%d")

        run_id = context.get("run_id")
        if isinstance(run_id, str) and "__" in run_id:
            _, _, timestamp_part = run_id.partition("__")
            try:
                return pendulum.parse(timestamp_part).strftime("%Y-%m-%d")
            except Exception:
                pass

        raise ValueError("run ds를 컨텍스트에서 결정할 수 없습니다")

    @task(task_id="resolve_run_hour")
    def resolve_run_hour(**context) -> str:
        logical_date = context.get("logical_date")
        if logical_date is not None:
            return logical_date.strftime("%H")

        dag_run = context.get("dag_run")
        dag_run_logical_date = getattr(dag_run, "logical_date", None)
        if dag_run_logical_date is not None:
            return dag_run_logical_date.strftime("%H")

        run_id = context.get("run_id")
        if isinstance(run_id, str) and "__" in run_id:
            _, _, timestamp_part = run_id.partition("__")
            try:
                return pendulum.parse(timestamp_part).strftime("%H")
            except Exception:
                pass

        raise ValueError("run hour를 컨텍스트에서 결정할 수 없습니다")

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

    # ── Task 7: cleanup (JSONL 임시 파일 삭제) ──
    @task(trigger_rule="none_failed_min_one_success")
    def cleanup(run_ds: str, run_hour: str) -> None:
        """JSONL 임시 파일 삭제."""
        jsonl_file = DATA_DIR / f"{run_ds}-{run_hour}.jsonl"

        if jsonl_file.exists():
            jsonl_file.unlink()
            print(f"[cleanup] 삭제됨: {jsonl_file}")
        else:
            print(f"[cleanup] 파일 없음: {jsonl_file}")

    cleanup_task = cleanup(run_ds, run_hour)

    # ── 의존성 그래프 ──
    # rest_fetch → validate → [upload_r2, upload_d1]
    # upload_d1 → enrich_details → quality_check → cleanup
    # upload_r2 → cleanup
    [run_ds, run_hour] >> rest_fetch
    rest_fetch >> validate_result >> [upload_r2, upload_d1]
    upload_d1 >> enrich_details >> quality_check >> cleanup_task
    upload_r2 >> cleanup_task


# DAG 인스턴스 생성
github_rest_api_hourly()
