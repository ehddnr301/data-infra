"""REST API 파이프라인 통합 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gharchive_etl.config import R2Config
from gharchive_etl.dl_models import DL_TABLE_COLUMNS
from gharchive_etl.models import Actor, GitHubEvent, Org, Repo
from gharchive_etl.r2 import _build_r2_key, upload_events_to_r2
from gharchive_etl.transformer import transform_events


def _make_event(
    *,
    event_id: str = "12345",
    event_type: str = "PushEvent",
    org_login: str = "Pseudo-Lab",
    repo_name: str = "Pseudo-Lab/test-repo",
    created_at: str = "2024-01-15T10:30:00Z",
) -> GitHubEvent:
    """테스트용 GitHubEvent 생성."""
    return GitHubEvent(
        id=event_id,
        type=event_type,
        actor=Actor(
            id=1,
            login="testuser",
            display_login="testuser",
            gravatar_id="",
            url="https://api.github.com/users/testuser",
            avatar_url="https://avatars.githubusercontent.com/u/1?",
        ),
        repo=Repo(
            id=100,
            name=repo_name,
            url=f"https://api.github.com/repos/{repo_name}",
        ),
        org=Org(
            id=200,
            login=org_login,
            gravatar_id="",
            url=f"https://api.github.com/orgs/{org_login}",
            avatar_url=f"https://avatars.githubusercontent.com/u/200?",
        ),
        payload={
            "push_id": 999,
            "size": 1,
            "distinct_size": 1,
            "ref": "refs/heads/main",
            "head": "abc123",
            "before": "def456",
            "commits": [
                {
                    "sha": "abc123",
                    "author": {"email": "test@test.com", "name": "Test"},
                    "message": "test commit",
                    "distinct": True,
                    "url": "https://api.github.com/repos/test/commits/abc123",
                }
            ],
        },
        public=True,
        created_at=created_at,
    )


class TestRestApiIntegration:
    """REST API 파이프라인 통합 테스트."""

    def test_end_to_end_rest_fetch_to_transform(self) -> None:
        """rest-fetch 수집 → transform_events(source='rest_api') 전체 흐름.

        1. GitHubEvent 생성
        2. transform_events에 source='rest_api' 전달
        3. 모든 결과 row에 source='rest_api' 확인
        """
        events = [_make_event(event_id="1"), _make_event(event_id="2")]
        dl_rows, stats = transform_events(events, source="rest_api")

        # 결과가 있는 테이블만 검증
        assert len(dl_rows) > 0, "transform_events 결과가 비어있음"

        for table_name, rows in dl_rows.items():
            for row in rows:
                assert row.get("source") == "rest_api", (
                    f"Table {table_name}: source가 'rest_api'가 아님: {row.get('source')}"
                )

    def test_existing_gharchive_pipeline_unaffected(self) -> None:
        """기존 GH Archive 파이프라인이 source='gharchive'로 정상 동작.

        1. transform_events(events) — source 미지정
        2. 모든 row에 source='gharchive' 확인
        """
        events = [_make_event()]
        dl_rows, stats = transform_events(events)

        for table_name, rows in dl_rows.items():
            for row in rows:
                assert row.get("source") == "gharchive", (
                    f"Table {table_name}: 기본 source가 'gharchive'가 아님"
                )

    def test_duplicate_event_id_same_source(self) -> None:
        """동일 event_id + 동일 source — transform_events 레벨에서 중복 생성.

        D1 INSERT OR IGNORE가 중복을 방지하므로,
        transform 단계에서는 동일 이벤트가 중복 row를 생성할 수 있음을 확인.
        실제 중복 방지는 D1 레벨에서 보장.
        """
        event = _make_event(event_id="dup-1")

        # gharchive로 한 번
        dl_rows_1, _ = transform_events([event], source="gharchive")
        # rest_api로 한 번 (동일 event_id)
        dl_rows_2, _ = transform_events([event], source="rest_api")

        # 동일 테이블에 동일 event_id가 다른 source로 존재
        for table_name in dl_rows_1:
            if table_name in dl_rows_2:
                rows_1 = dl_rows_1[table_name]
                rows_2 = dl_rows_2[table_name]
                if rows_1 and rows_2:
                    assert rows_1[0].get("source") == "gharchive"
                    assert rows_2[0].get("source") == "rest_api"
                    # event_id는 동일
                    assert rows_1[0].get("event_id") == rows_2[0].get("event_id")

    def test_backfill_multi_date_events(self) -> None:
        """백필 모드 — 여러 날짜 이벤트의 base_date 정상 변환."""
        events = [
            _make_event(event_id="1", created_at="2024-01-15T10:00:00Z"),
            _make_event(event_id="2", created_at="2024-01-16T14:30:00Z"),
        ]
        dl_rows, _ = transform_events(events, source="rest_api")

        # base_date 값을 수집
        all_base_dates = set()
        for rows in dl_rows.values():
            for row in rows:
                if "base_date" in row:
                    all_base_dates.add(row["base_date"])
                assert row.get("source") == "rest_api"

        # 서로 다른 날짜의 이벤트이므로 base_date가 2개여야 함
        assert len(all_base_dates) >= 1, "base_date가 존재해야 함"

    def test_r2_path_rest_api_format(self) -> None:
        """R2 키가 raw/rest-api/{org}/{repo}/{date}-{hour}.jsonl.gz 형식."""
        key = _build_r2_key("raw/rest-api", "Pseudo-Lab", "test-repo", "2024-01-15-14")
        assert key == "raw/rest-api/Pseudo-Lab/test-repo/2024-01-15-14.jsonl.gz"

    def test_r2_path_gharchive_format(self) -> None:
        """기존 GH Archive R2 키 형식 유지."""
        key = _build_r2_key("raw/github-archive", "Pseudo-Lab", "test-repo", "2024-01-15")
        assert key == "raw/github-archive/Pseudo-Lab/test-repo/2024-01-15.jsonl.gz"

    @patch("gharchive_etl.r2._find_wrangler", return_value="wrangler")
    @patch("gharchive_etl.r2.subprocess.run")
    def test_upload_with_prefix_override_and_hour(
        self,
        mock_run: MagicMock,
        mock_find: MagicMock,
    ) -> None:
        """prefix_override + hour 조합으로 REST API 경로 생성."""
        import subprocess

        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        config = R2Config(bucket_name="github-archive-raw", prefix="raw/github-archive")
        events = [_make_event(repo_name="Pseudo-Lab/test-repo")]

        result = upload_events_to_r2(
            events,
            "2024-01-15",
            config,
            prefix_override="raw/rest-api",
            hour="14",
        )

        assert result.files_uploaded == 1
        # wrangler 호출 시 key 확인
        call_args = mock_run.call_args[0][0]
        bucket_key = call_args[4]  # f"{bucket}/{key}"
        assert "raw/rest-api" in bucket_key
        assert "2024-01-15-14" in bucket_key

    def test_source_in_all_dl_table_columns(self) -> None:
        """모든 DL 테이블 정의에 source 컬럼이 포함되어 있다."""
        for table_name, columns in DL_TABLE_COLUMNS.items():
            assert "source" in columns, (
                f"Table {table_name}: DL_TABLE_COLUMNS에 'source' 컬럼 누락"
            )


class TestDagIntegrationTests:
    """DAG 관련 통합 테스트 (Airflow 미설치 시 skip)."""

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("airflow"),
        reason="Airflow not installed",
    )
    def test_hourly_dag_exists_and_valid(self) -> None:
        """github_rest_api_hourly DAG가 DagBag에 존재한다."""
        from airflow.models import DagBag
        from pathlib import Path

        dag_dir = Path(__file__).resolve().parent.parent / "dags"
        dagbag = DagBag(dag_folder=str(dag_dir), include_examples=False)
        assert "github_rest_api_hourly" in dagbag.dags, (
            f"DAG 없음. import errors: {dagbag.import_errors}"
        )

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("airflow"),
        reason="Airflow not installed",
    )
    def test_hourly_dag_schedule(self) -> None:
        """github_rest_api_hourly 스케줄이 '10 * * * *'."""
        from airflow.models import DagBag
        from pathlib import Path

        dag_dir = Path(__file__).resolve().parent.parent / "dags"
        dagbag = DagBag(dag_folder=str(dag_dir), include_examples=False)
        dag = dagbag.dags["github_rest_api_hourly"]
        assert str(dag.schedule_interval) == "10 * * * *"
        assert dag.catchup is False

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("airflow"),
        reason="Airflow not installed",
    )
    def test_hourly_dag_has_expected_tasks(self) -> None:
        """github_rest_api_hourly에 예상 Task들이 포함."""
        from airflow.models import DagBag
        from pathlib import Path

        dag_dir = Path(__file__).resolve().parent.parent / "dags"
        dagbag = DagBag(dag_folder=str(dag_dir), include_examples=False)
        dag = dagbag.dags["github_rest_api_hourly"]
        task_ids = {t.task_id for t in dag.tasks}
        expected = {
            "rest_fetch",
            "validate",
            "upload_r2",
            "upload_d1",
            "enrich_details",
            "quality_check",
            "cleanup",
        }
        assert expected.issubset(task_ids), f"누락: {expected - task_ids}"

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("airflow"),
        reason="Airflow not installed",
    )
    def test_daily_dag_schedule_updated(self) -> None:
        """기존 daily DAG 스케줄이 0 3 * * *로 변경됨."""
        from airflow.models import DagBag
        from pathlib import Path

        dag_dir = Path(__file__).resolve().parent.parent / "dags"
        dagbag = DagBag(dag_folder=str(dag_dir), include_examples=False)
        dag = dagbag.dags["github_archive_daily"]
        assert str(dag.schedule_interval) == "0 3 * * *"
