"""DAG 유효성 테스트.

Airflow scheduler의 DAG 파싱 오류를 사전에 감지한다.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


DAG_DIR = Path(__file__).resolve().parent.parent / "dags"

pytestmark = pytest.mark.skipif(
    not importlib.util.find_spec("airflow"),
    reason="Airflow not installed",
)


class TestDagIntegrity:
    """DAG 파일 유효성 테스트."""

    def test_dag_file_imports_without_error(self):
        """DAG 파일이 import 에러 없이 로딩된다."""
        dag_file = DAG_DIR / "github_archive_daily.py"
        assert dag_file.exists(), f"DAG 파일 없음: {dag_file}"

        spec = importlib.util.spec_from_file_location("github_archive_daily", dag_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    def test_dag_has_correct_schedule(self):
        """DAG 스케줄이 '0 2 * * *'으로 설정되어 있다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        assert "github_archive_daily" in dagbag.dags, (
            f"DAG 없음. import errors: {dagbag.import_errors}"
        )
        dag = dagbag.dags["github_archive_daily"]

        assert str(dag.schedule_interval) == "0 2 * * *", (
            f"스케줄 불일치: {dag.schedule_interval}"
        )
        assert dag.catchup is True, "catchup이 False로 변경됨"
        assert dag.max_active_runs == 1, (
            f"max_active_runs 불일치: {dag.max_active_runs}"
        )

    def test_dag_has_expected_tasks(self):
        """DAG에 예상 Task들이 포함되어 있다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        assert "github_archive_daily" in dagbag.dags

        dag = dagbag.dags["github_archive_daily"]
        task_ids = {t.task_id for t in dag.tasks}

        expected_tasks = {
            "fetch", "validate", "upload_r2", "upload_d1",
            "verify_aggregation", "enrich_details", "quality_check",
            "daily_summary", "cleanup",
        }
        assert expected_tasks.issubset(task_ids), (
            f"누락 Task: {expected_tasks - task_ids}"
        )

    def test_dag_no_import_errors(self):
        """DagBag에 import 에러가 없다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        assert not dagbag.import_errors, (
            f"DAG import 에러: {dagbag.import_errors}"
        )

    def test_task_dependencies(self):
        """Task 의존성 그래프가 올바르다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        dag = dagbag.dags["github_archive_daily"]

        # fetch → validate
        validate_task = dag.get_task("validate")
        assert "fetch" in [t.task_id for t in validate_task.upstream_list]

        # validate → upload_r2, upload_d1 (병렬)
        upload_r2 = dag.get_task("upload_r2")
        upload_d1 = dag.get_task("upload_d1")
        assert "validate" in [t.task_id for t in upload_r2.upstream_list]
        assert "validate" in [t.task_id for t in upload_d1.upstream_list]

        # upload_r2 → cleanup
        cleanup_task = dag.get_task("cleanup")
        cleanup_upstream_ids = {t.task_id for t in cleanup_task.upstream_list}
        assert "upload_r2" in cleanup_upstream_ids

    def test_cloudflare_usage_hourly_dag_imports(self):
        """cloudflare_usage_hourly DAG 파일이 import 에러 없이 로딩된다."""
        dag_file = DAG_DIR / "cloudflare_usage_hourly.py"
        assert dag_file.exists(), f"DAG 파일 없음: {dag_file}"

        spec = importlib.util.spec_from_file_location("cloudflare_usage_hourly", dag_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    def test_cloudflare_usage_hourly_dag_exists(self):
        """cloudflare_usage_hourly DAG이 DagBag에 존재한다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        assert "cloudflare_usage_hourly" in dagbag.dags, (
            f"DAG 없음. import errors: {dagbag.import_errors}"
        )

    def test_cloudflare_usage_hourly_schedule(self):
        """cloudflare_usage_hourly 스케줄이 '0 * * * *', catchup=False."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        dag = dagbag.dags["cloudflare_usage_hourly"]

        assert str(dag.schedule_interval) == "0 * * * *", (
            f"스케줄 불일치: {dag.schedule_interval}"
        )
        assert dag.catchup is False, "catchup이 True로 변경됨"
        assert dag.max_active_runs == 1, (
            f"max_active_runs 불일치: {dag.max_active_runs}"
        )

    def test_cloudflare_usage_hourly_has_check_usage_task(self):
        """cloudflare_usage_hourly에 check_usage task가 존재한다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        dag = dagbag.dags["cloudflare_usage_hourly"]
        task_ids = {t.task_id for t in dag.tasks}

        assert "check_usage" in task_ids, f"check_usage 태스크 없음. 존재 태스크: {task_ids}"

    def test_verify_quality_dependencies(self):
        """upload_d1 → verify → enrich → quality → summary → cleanup 의존성."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        dag = dagbag.dags["github_archive_daily"]

        # upload_d1 → verify_aggregation
        verify = dag.get_task("verify_aggregation")
        assert "upload_d1" in [t.task_id for t in verify.upstream_list]

        # verify_aggregation → enrich_details
        enrich = dag.get_task("enrich_details")
        assert "verify_aggregation" in [t.task_id for t in enrich.upstream_list]

        # enrich_details → quality_check
        quality = dag.get_task("quality_check")
        assert "enrich_details" in [t.task_id for t in quality.upstream_list]

        # quality_check → daily_summary
        summary = dag.get_task("daily_summary")
        assert "quality_check" in [t.task_id for t in summary.upstream_list]

        # daily_summary → cleanup
        cleanup = dag.get_task("cleanup")
        assert "daily_summary" in [t.task_id for t in cleanup.upstream_list]
