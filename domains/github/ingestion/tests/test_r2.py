"""R2 업로드 모듈 테스트."""

from __future__ import annotations

import gzip
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import orjson
import pytest
from gharchive_etl.config import R2Config
from gharchive_etl.models import GitHubEvent
from gharchive_etl.r2 import (
    _build_r2_key,
    _compress_events_to_gzip,
    _extract_org_repo,
    _group_events_by_org_repo,
    upload_events_to_r2,
)

# ── 테스트 픽스처 ──────────────────────────────────────────


def _make_event(
    *,
    event_id: str = "1",
    repo_name: str = "org/repo",
    event_type: str = "PushEvent",
) -> GitHubEvent:
    """테스트용 GitHubEvent를 생성한다."""
    return GitHubEvent(
        id=event_id,
        type=event_type,
        actor={"id": 1, "login": "user"},
        repo={"id": 1, "name": repo_name},
        created_at="2024-01-15T10:00:00Z",
        payload={},
    )


# ── TestExtractOrgRepo ─────────────────────────────────────


class TestExtractOrgRepo:
    """_extract_org_repo 함수 테스트."""

    def test_normal(self) -> None:
        event = _make_event(repo_name="pseudolab/test-repo")
        result = _extract_org_repo(event)
        assert result == ("pseudolab", "test-repo")

    def test_without_org(self) -> None:
        """org 없이 user/repo 형식도 정상 추출."""
        event = _make_event(repo_name="someuser/myrepo")
        result = _extract_org_repo(event)
        assert result == ("someuser", "myrepo")

    def test_invalid_no_slash(self) -> None:
        """슬래시가 없는 repo name은 None을 반환."""
        event = _make_event(repo_name="noslash")
        result = _extract_org_repo(event)
        assert result is None

    def test_invalid_multiple_slashes(self) -> None:
        """슬래시가 여러 개인 경우 None을 반환."""
        event = _make_event(repo_name="a/b/c")
        result = _extract_org_repo(event)
        assert result is None


# ── TestGroupEvents ────────────────────────────────────────


class TestGroupEvents:
    """_group_events_by_org_repo 함수 테스트."""

    def test_by_org_repo(self) -> None:
        events = [
            _make_event(event_id="1", repo_name="org1/repo1"),
            _make_event(event_id="2", repo_name="org1/repo1"),
            _make_event(event_id="3", repo_name="org2/repo2"),
        ]
        grouped, skipped = _group_events_by_org_repo(events)
        assert skipped == 0
        assert len(grouped[("org1", "repo1")]) == 2
        assert len(grouped[("org2", "repo2")]) == 1

    def test_skips_invalid(self) -> None:
        events = [
            _make_event(event_id="1", repo_name="org/repo"),
            _make_event(event_id="2", repo_name="noslash"),
            _make_event(event_id="3", repo_name="a/b/c"),
        ]
        grouped, skipped = _group_events_by_org_repo(events)
        assert skipped == 2
        assert len(grouped) == 1
        assert ("org", "repo") in grouped

    def test_empty(self) -> None:
        grouped, skipped = _group_events_by_org_repo([])
        assert grouped == {}
        assert skipped == 0


# ── TestCompressEvents ─────────────────────────────────────


class TestCompressEvents:
    """_compress_events_to_gzip 함수 테스트."""

    def test_to_gzip(self, tmp_path: Path) -> None:
        events = [
            _make_event(event_id="1"),
            _make_event(event_id="2"),
        ]
        gz_path = tmp_path / "test.jsonl.gz"
        file_bytes = _compress_events_to_gzip(events, gz_path)

        assert file_bytes > 0
        assert gz_path.exists()

        # gzip 파일을 열어 내용 검증
        with gzip.open(gz_path, "rb") as f:
            lines = f.read().decode().strip().split("\n")

        assert len(lines) == 2
        parsed = orjson.loads(lines[0])
        assert parsed["id"] == "1"
        assert parsed["type"] == "PushEvent"

    def test_empty(self, tmp_path: Path) -> None:
        gz_path = tmp_path / "empty.jsonl.gz"
        file_bytes = _compress_events_to_gzip([], gz_path)

        assert file_bytes > 0  # gzip 헤더만 있어도 크기 > 0
        with gzip.open(gz_path, "rb") as f:
            content = f.read()
        assert content == b""


# ── TestR2KeyNaming ────────────────────────────────────────


class TestR2KeyNaming:
    """_build_r2_key 함수 테스트."""

    def test_format(self) -> None:
        key = _build_r2_key("raw/github-archive", "pseudolab", "repo", "2024-01-15")
        assert key == "raw/github-archive/pseudolab/repo/2024-01-15.jsonl.gz"

    def test_with_prefix(self) -> None:
        key = _build_r2_key("custom/prefix", "org", "repo", "2024-01-15")
        assert key == "custom/prefix/org/repo/2024-01-15.jsonl.gz"

    def test_empty_prefix(self) -> None:
        key = _build_r2_key("", "org", "repo", "2024-01-15")
        assert key == "org/repo/2024-01-15.jsonl.gz"


# ── TestUploadToR2 ─────────────────────────────────────────


class TestUploadToR2:
    """upload_events_to_r2 함수 테스트."""

    @pytest.fixture()
    def r2_config(self) -> R2Config:
        return R2Config(
            bucket_name="github-archive-raw",
            prefix="raw/github-archive",
        )

    @pytest.fixture()
    def sample_events(self) -> list[GitHubEvent]:
        return [
            _make_event(event_id="1", repo_name="pseudolab/repo1"),
            _make_event(event_id="2", repo_name="pseudolab/repo1"),
            _make_event(event_id="3", repo_name="pseudolab/repo2"),
        ]

    @patch("gharchive_etl.r2._find_wrangler", return_value="wrangler")
    @patch("gharchive_etl.r2.subprocess.run")
    def test_success(
        self,
        mock_run: MagicMock,
        mock_find: MagicMock,
        r2_config: R2Config,
        sample_events: list[GitHubEvent],
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        result = upload_events_to_r2(
            sample_events,
            "2024-01-15",
            r2_config,
        )

        assert result.total_events == 3
        assert result.files_uploaded == 2
        assert result.errors == []
        assert result.bytes_total > 0
        assert result.dry_run is False

    @patch("gharchive_etl.r2._find_wrangler", return_value="wrangler")
    @patch("gharchive_etl.r2.subprocess.run")
    def test_dry_run(
        self,
        mock_run: MagicMock,
        mock_find: MagicMock,
        r2_config: R2Config,
        sample_events: list[GitHubEvent],
    ) -> None:
        result = upload_events_to_r2(
            sample_events,
            "2024-01-15",
            r2_config,
            dry_run=True,
        )

        assert result.total_events == 3
        assert result.files_uploaded == 0
        assert result.files_skipped == 2  # 2 org/repo groups
        assert result.dry_run is True
        assert result.bytes_total > 0
        # dry_run에서는 subprocess.run이 호출되지 않아야 함
        mock_run.assert_not_called()

    @patch("gharchive_etl.r2._find_wrangler", return_value="wrangler")
    @patch("gharchive_etl.r2.time.sleep")
    @patch("gharchive_etl.r2.subprocess.run")
    def test_retry(
        self,
        mock_run: MagicMock,
        mock_sleep: MagicMock,
        mock_find: MagicMock,
        r2_config: R2Config,
    ) -> None:
        events = [_make_event(event_id="1", repo_name="org/repo")]
        # 첫 put 실패, 두 번째 put 성공
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "wrangler", stderr="temp error"),  # 1st put
            subprocess.CompletedProcess(args=[], returncode=0),  # 2nd put
        ]

        result = upload_events_to_r2(events, "2024-01-15", r2_config)

        assert result.files_uploaded == 1
        assert result.errors == []
        mock_sleep.assert_called_once()

    @patch("gharchive_etl.r2._find_wrangler", return_value="wrangler")
    @patch("gharchive_etl.r2.time.sleep")
    @patch("gharchive_etl.r2.subprocess.run")
    def test_max_retries_exceeded(
        self,
        mock_run: MagicMock,
        mock_sleep: MagicMock,
        mock_find: MagicMock,
        r2_config: R2Config,
    ) -> None:
        events = [_make_event(event_id="1", repo_name="org/repo")]
        # 모든 put 실패
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "wrangler", stderr="fail1"),
            subprocess.CalledProcessError(1, "wrangler", stderr="fail2"),
            subprocess.CalledProcessError(1, "wrangler", stderr="fail3"),
        ]

        result = upload_events_to_r2(events, "2024-01-15", r2_config, max_retries=3)

        assert result.files_uploaded == 0
        assert len(result.errors) == 1
        assert "fail3" in result.errors[0]

    @patch("gharchive_etl.r2._find_wrangler", side_effect=RuntimeError("wrangler CLI is not installed or not in PATH."))
    def test_wrangler_not_installed(
        self,
        mock_find: MagicMock,
        r2_config: R2Config,
    ) -> None:
        events = [_make_event(event_id="1", repo_name="org/repo")]

        with pytest.raises(RuntimeError, match="wrangler CLI is not installed"):
            upload_events_to_r2(events, "2024-01-15", r2_config)
