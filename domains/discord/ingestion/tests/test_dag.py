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


class TestDiscordDagIntegrity:
    """discord_daily DAG 유효성 테스트."""

    def test_dag_file_imports_without_error(self):
        """DAG 파일이 import 에러 없이 로딩된다."""
        dag_file = DAG_DIR / "discord_daily.py"
        assert dag_file.exists(), f"DAG 파일 없음: {dag_file}"

        spec = importlib.util.spec_from_file_location("discord_daily", dag_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    def test_dag_has_correct_schedule(self):
        """DAG 스케줄이 '0 3 * * *'으로 설정되어 있다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        assert "discord_daily" in dagbag.dags, (
            f"DAG 없음. import errors: {dagbag.import_errors}"
        )
        dag = dagbag.dags["discord_daily"]

        assert str(dag.schedule_interval) == "0 3 * * *", (
            f"스케줄 불일치: {dag.schedule_interval}"
        )
        assert dag.catchup is False, "catchup이 True로 변경됨"
        assert dag.max_active_runs == 1, (
            f"max_active_runs 불일치: {dag.max_active_runs}"
        )

    def test_dag_has_expected_tasks(self):
        """DAG에 예상 Task들이 포함되어 있다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        assert "discord_daily" in dagbag.dags

        dag = dagbag.dags["discord_daily"]
        task_ids = {t.task_id for t in dag.tasks}

        expected_tasks = {
            "fetch", "validate", "upload_r2", "upload_d1",
            "quality_check", "summary", "cleanup",
        }
        assert expected_tasks.issubset(task_ids), (
            f"누락 Task: {expected_tasks - task_ids}"
        )

    def test_dag_task_count(self):
        """DAG에 7개의 Task가 있다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        dag = dagbag.dags["discord_daily"]
        assert len(dag.tasks) == 7, (
            f"Task 수 불일치: {len(dag.tasks)} (expected 7)"
        )

    def test_task_dependencies(self):
        """Task 의존성 그래프가 올바르다."""
        from airflow.models import DagBag

        dagbag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
        dag = dagbag.dags["discord_daily"]

        # fetch → validate
        validate_task = dag.get_task("validate")
        assert "fetch" in [t.task_id for t in validate_task.upstream_list]

        # validate → upload_r2, upload_d1 (병렬)
        upload_r2 = dag.get_task("upload_r2")
        upload_d1 = dag.get_task("upload_d1")
        assert "validate" in [t.task_id for t in upload_r2.upstream_list]
        assert "validate" in [t.task_id for t in upload_d1.upstream_list]

        # upload_d1 → quality_check → summary → cleanup
        quality = dag.get_task("quality_check")
        assert "upload_d1" in [t.task_id for t in quality.upstream_list]

        summary = dag.get_task("summary")
        assert "quality_check" in [t.task_id for t in summary.upstream_list]

        cleanup = dag.get_task("cleanup")
        cleanup_upstream_ids = {t.task_id for t in cleanup.upstream_list}
        assert "summary" in cleanup_upstream_ids
        assert "upload_r2" in cleanup_upstream_ids
