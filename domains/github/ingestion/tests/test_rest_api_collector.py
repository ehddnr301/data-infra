"""REST API Events 수집 모듈 테스트."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gharchive_etl.config import AppConfig, RestApiConfig
from gharchive_etl.github_api import GitHubApiResult
from gharchive_etl.rest_api_collector import (
    CollectionResult,
    RestApiCollector,
    RestApiCollectionSummary,
)


def _make_app_config(**rest_api_overrides: Any) -> AppConfig:
    """테스트용 AppConfig 생성."""
    rest_cfg = {"r2_prefix": "raw/rest-api", "etag_cache_enabled": True, "repo_supplement_threshold": 300}
    rest_cfg.update(rest_api_overrides)
    return AppConfig(
        target_orgs=["Pseudo-Lab"],
        rest_api=RestApiConfig(**rest_cfg),
    )


def _mock_api_client() -> MagicMock:
    """mock GitHubApiClient 생성."""
    return MagicMock()


def _make_api_result(
    status_code: int = 200,
    data: Any = None,
    headers: dict[str, str] | None = None,
    error: str | None = None,
) -> GitHubApiResult:
    """테스트용 GitHubApiResult 생성."""
    return GitHubApiResult(
        url="https://api.github.com/test",
        status_code=status_code,
        data=data,
        headers=headers or {},
        error=error,
    )


class TestRestApiCollector:
    """RestApiCollector 기본 동작 테스트."""

    def test_collect_org_basic(self, tmp_path: Path) -> None:
        """기본 org 수집 동작."""
        config = _make_app_config()
        api = _mock_api_client()
        events = [
            {"id": "1", "type": "PushEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "o/r"}, "created_at": "2024-01-15T10:00:00Z"},
            {"id": "2", "type": "WatchEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "o/r"}, "created_at": "2024-01-15T10:00:00Z"},
        ]
        api.fetch_org_events.return_value = _make_api_result(data=events, headers={"ETag": 'W/"abc"'})

        collector = RestApiCollector(api, config, etag_cache_path=tmp_path / "etag.json")
        normalized, summary = collector.collect_all()

        assert len(normalized) == 2
        assert summary.total_events == 2
        api.fetch_org_events.assert_called_once()

    def test_collect_org_etag_304_skip(self, tmp_path: Path) -> None:
        """304 Not Modified 시 스킵."""
        config = _make_app_config()
        api = _mock_api_client()
        api.fetch_org_events.return_value = _make_api_result(status_code=304, data=None)

        # Pre-populate etag cache
        cache_path = tmp_path / "etag.json"
        cache_path.write_text('{"Pseudo-Lab": {"etag": "W/\\"old\\"", "last_poll": "2024-01-01T00:00:00Z"}}')

        collector = RestApiCollector(api, config, etag_cache_path=cache_path)
        normalized, summary = collector.collect_all()

        assert len(normalized) == 0
        assert summary.results[0].skipped_304 is True

    def test_repo_supplement_triggered_at_threshold(self, tmp_path: Path) -> None:
        """300건 이상일 때 repo 보충 수집 실행."""
        config = _make_app_config(repo_supplement_threshold=3)  # low threshold for test
        api = _mock_api_client()
        org_events = [
            {"id": str(i), "type": "PushEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "o/r"}, "created_at": "2024-01-15T10:00:00Z"}
            for i in range(5)
        ]
        api.fetch_org_events.return_value = _make_api_result(data=org_events)
        api.fetch_org_repos.return_value = _make_api_result(data=[{"name": "repo1"}])
        repo_events = [
            {"id": "100", "type": "IssuesEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "Pseudo-Lab/repo1"}, "created_at": "2024-01-15T10:00:00Z"}
        ]
        api.fetch_repo_events.return_value = _make_api_result(data=repo_events)

        collector = RestApiCollector(api, config, etag_cache_path=tmp_path / "etag.json")
        normalized, summary = collector.collect_all()

        assert summary.results[0].repo_supplement is True
        api.fetch_org_repos.assert_called_once()
        api.fetch_repo_events.assert_called_once()

    def test_repo_supplement_not_triggered_below_threshold(self, tmp_path: Path) -> None:
        """threshold 미만일 때 repo 보충 수집 미실행."""
        config = _make_app_config(repo_supplement_threshold=300)
        api = _mock_api_client()
        org_events = [
            {"id": "1", "type": "PushEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "o/r"}, "created_at": "2024-01-15T10:00:00Z"}
        ]
        api.fetch_org_events.return_value = _make_api_result(data=org_events)

        collector = RestApiCollector(api, config, etag_cache_path=tmp_path / "etag.json")
        normalized, summary = collector.collect_all()

        assert summary.results[0].repo_supplement is False
        api.fetch_org_repos.assert_not_called()

    def test_backfill_ignores_etag(self, tmp_path: Path) -> None:
        """backfill 모드에서 ETag 무시."""
        config = _make_app_config()
        api = _mock_api_client()
        events = [
            {"id": "1", "type": "PushEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "o/r"}, "created_at": "2024-01-15T10:00:00Z"}
        ]
        api.fetch_org_events.return_value = _make_api_result(data=events)
        api.fetch_org_repos.return_value = _make_api_result(data=[])

        # Pre-populate etag cache
        cache_path = tmp_path / "etag.json"
        cache_path.write_text('{"Pseudo-Lab": {"etag": "W/\\"old\\"", "last_poll": "2024-01-01T00:00:00Z"}}')

        collector = RestApiCollector(api, config, etag_cache_path=cache_path)
        normalized, summary = collector.collect_all(backfill=True)

        # Should pass etag=None
        api.fetch_org_events.assert_called_once_with("Pseudo-Lab", etag=None)
        assert len(normalized) == 1

    def test_backfill_forces_repo_supplement(self, tmp_path: Path) -> None:
        """backfill 모드에서 repo 보충 강제 실행."""
        config = _make_app_config(repo_supplement_threshold=9999)  # very high
        api = _mock_api_client()
        events = [
            {"id": "1", "type": "PushEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "o/r"}, "created_at": "2024-01-15T10:00:00Z"}
        ]
        api.fetch_org_events.return_value = _make_api_result(data=events)
        api.fetch_org_repos.return_value = _make_api_result(data=[])

        collector = RestApiCollector(api, config, etag_cache_path=tmp_path / "etag.json")
        normalized, summary = collector.collect_all(backfill=True)

        assert summary.results[0].repo_supplement is True
        api.fetch_org_repos.assert_called_once()

    def test_deduplicate_org_repo_overlap(self, tmp_path: Path) -> None:
        """org+repo 결과의 event_id 중복 제거."""
        config = _make_app_config(repo_supplement_threshold=1)  # trigger supplement
        api = _mock_api_client()
        # Same event appears in both org and repo results
        event = {"id": "1", "type": "PushEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "Pseudo-Lab/repo1"}, "created_at": "2024-01-15T10:00:00Z"}
        api.fetch_org_events.return_value = _make_api_result(data=[event])
        api.fetch_org_repos.return_value = _make_api_result(data=[{"name": "repo1"}])
        api.fetch_repo_events.return_value = _make_api_result(data=[event])  # duplicate

        collector = RestApiCollector(api, config, etag_cache_path=tmp_path / "etag.json")
        normalized, summary = collector.collect_all()

        assert summary.total_events == 1  # deduplicated

    def test_etag_cache_save_load(self, tmp_path: Path) -> None:
        """ETag 캐시 저장 및 로드."""
        config = _make_app_config()
        api = _mock_api_client()
        events = [
            {"id": "1", "type": "PushEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "o/r"}, "created_at": "2024-01-15T10:00:00Z"}
        ]
        api.fetch_org_events.return_value = _make_api_result(
            data=events, headers={"ETag": 'W/"new-etag"'},
        )

        cache_path = tmp_path / "etag.json"
        collector = RestApiCollector(api, config, etag_cache_path=cache_path)
        collector.collect_all()

        # Verify cache was saved
        assert cache_path.exists()
        import json
        cache = json.loads(cache_path.read_text())
        assert "Pseudo-Lab" in cache
        assert cache["Pseudo-Lab"]["etag"] == 'W/"new-etag"'

    def test_api_call_count_tracking(self, tmp_path: Path) -> None:
        """API 호출 횟수 추적."""
        config = _make_app_config(repo_supplement_threshold=1)
        api = _mock_api_client()
        events = [
            {"id": "1", "type": "PushEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "o/r"}, "created_at": "2024-01-15T10:00:00Z"}
        ]
        api.fetch_org_events.return_value = _make_api_result(data=events)
        api.fetch_org_repos.return_value = _make_api_result(data=[{"name": "r1"}, {"name": "r2"}])
        api.fetch_repo_events.return_value = _make_api_result(data=[])

        collector = RestApiCollector(api, config, etag_cache_path=tmp_path / "etag.json")
        _, summary = collector.collect_all()

        # 1 org_events + 1 org_repos + 2 repo_events = 4
        assert summary.total_api_calls == 4

    def test_normalize_invalid_event_skipped(self, tmp_path: Path) -> None:
        """정규화 실패 이벤트는 스킵."""
        config = _make_app_config()
        api = _mock_api_client()
        events = [
            {"id": "1"},  # Missing required fields → should be skipped
            {"id": "2", "type": "WatchEvent", "actor": {"id": 1, "login": "u"}, "repo": {"id": 1, "name": "o/r"}, "created_at": "2024-01-15T10:00:00Z"},
        ]
        api.fetch_org_events.return_value = _make_api_result(data=events)

        collector = RestApiCollector(api, config, etag_cache_path=tmp_path / "etag.json")
        normalized, summary = collector.collect_all()

        assert len(normalized) == 1
        assert normalized[0].id == "2"
