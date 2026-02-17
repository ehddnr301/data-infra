"""DAG 유효성 테스트.

Airflow scheduler의 DAG 파싱 오류를 사전에 감지한다.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


DAG_DIR = Path(__file__).resolve().parent.parent / "dags"


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

        expected_tasks = {"fetch", "validate", "upload_r2", "upload_d1", "cleanup"}
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

        # upload_r2, upload_d1 → cleanup
        cleanup_task = dag.get_task("cleanup")
        cleanup_upstream_ids = {t.task_id for t in cleanup_task.upstream_list}
        assert "upload_r2" in cleanup_upstream_ids
        assert "upload_d1" in cleanup_upstream_ids
