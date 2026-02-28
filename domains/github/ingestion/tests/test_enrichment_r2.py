"""Enrichment R2 업로드 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gharchive_etl.enrichment_r2 import (
    build_enrichment_r2_key,
    check_r2_key_exists,
    load_enriched_keys,
    save_enriched_key,
    upload_enrichment_json,
    upload_enrichment_text,
)


class TestBuildEnrichmentR2Key:
    def test_commits_key(self) -> None:
        key = build_enrichment_r2_key("commits", "Pseudo-Lab", "repo", "abc123")
        assert key == "enriched/commits/Pseudo-Lab/repo/abc123.json"

    def test_pr_files_key(self) -> None:
        key = build_enrichment_r2_key("pr-files", "Pseudo-Lab", "repo", "42")
        assert key == "enriched/pr-files/Pseudo-Lab/repo/42.json"

    def test_users_key(self) -> None:
        key = build_enrichment_r2_key("users", "", "", "octocat")
        assert key == "enriched/users/octocat.json"

    def test_wiki_key(self) -> None:
        key = build_enrichment_r2_key("wiki", "Pseudo-Lab", "repo", "Home", extension=".md")
        assert key == "enriched/wiki/Pseudo-Lab/repo/Home.md"

    def test_issue_comments_key(self) -> None:
        key = build_enrichment_r2_key("issue-comments", "Pseudo-Lab", "repo", "100")
        assert key == "enriched/issue-comments/Pseudo-Lab/repo/100.json"

    def test_pr_reviews_key(self) -> None:
        key = build_enrichment_r2_key("pr-reviews", "Pseudo-Lab", "repo", "55")
        assert key == "enriched/pr-reviews/Pseudo-Lab/repo/55.json"

    def test_custom_prefix(self) -> None:
        key = build_enrichment_r2_key("commits", "org", "repo", "sha", prefix="custom")
        assert key == "custom/commits/org/repo/sha.json"


class TestCheckR2KeyExists:
    @patch("gharchive_etl.enrichment_r2.subprocess.run")
    def test_exists_returns_true(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        assert check_r2_key_exists("bucket", "key") is True
        mock_run.assert_called_once()

    @patch("gharchive_etl.enrichment_r2.subprocess.run")
    def test_not_exists_returns_false(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1)
        assert check_r2_key_exists("bucket", "key") is False

    @patch("gharchive_etl.enrichment_r2.subprocess.run")
    def test_exception_returns_false(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("wrangler not found")
        assert check_r2_key_exists("bucket", "key") is False


class TestEnrichedKeysTracker:
    def test_load_empty(self, tmp_path: Path) -> None:
        """트래커 파일이 없으면 빈 set을 반환한다."""
        with patch("gharchive_etl.enrichment_r2._TRACKER_DIR", tmp_path):
            keys = load_enriched_keys("test-bucket")
            assert keys == set()

    def test_save_and_load(self, tmp_path: Path) -> None:
        """저장한 키를 다시 로드할 수 있다."""
        with patch("gharchive_etl.enrichment_r2._TRACKER_DIR", tmp_path):
            save_enriched_key("test-bucket", "enriched/commits/org/repo/abc.json")
            save_enriched_key("test-bucket", "enriched/commits/org/repo/def.json")
            keys = load_enriched_keys("test-bucket")
            assert keys == {
                "enriched/commits/org/repo/abc.json",
                "enriched/commits/org/repo/def.json",
            }

    def test_deduplication_on_load(self, tmp_path: Path) -> None:
        """같은 키를 여러 번 저장해도 set이므로 중복 제거된다."""
        with patch("gharchive_etl.enrichment_r2._TRACKER_DIR", tmp_path):
            save_enriched_key("bucket", "key1")
            save_enriched_key("bucket", "key1")
            keys = load_enriched_keys("bucket")
            assert len(keys) == 1

    def test_different_buckets(self, tmp_path: Path) -> None:
        """버킷별로 독립적으로 트래킹한다."""
        with patch("gharchive_etl.enrichment_r2._TRACKER_DIR", tmp_path):
            save_enriched_key("bucket-a", "key1")
            save_enriched_key("bucket-b", "key2")
            assert "key1" in load_enriched_keys("bucket-a")
            assert "key1" not in load_enriched_keys("bucket-b")


class TestUploadEnrichmentJson:
    @patch("gharchive_etl.enrichment_r2._wrangler_r2_put")
    def test_upload_success(self, mock_put: MagicMock) -> None:
        data = {"sha": "abc123", "message": "test"}
        result = upload_enrichment_json("bucket", "key.json", data)
        assert result is True
        mock_put.assert_called_once()

    def test_dry_run_skips_upload(self) -> None:
        data = {"sha": "abc123"}
        result = upload_enrichment_json("bucket", "key.json", data, dry_run=True)
        assert result is True

    @patch("gharchive_etl.enrichment_r2._wrangler_r2_put")
    def test_upload_failure(self, mock_put: MagicMock) -> None:
        mock_put.side_effect = RuntimeError("upload failed")
        result = upload_enrichment_json("bucket", "key.json", {"data": 1})
        assert result is False

    @patch("gharchive_etl.enrichment_r2._wrangler_r2_put")
    def test_upload_list_data(self, mock_put: MagicMock) -> None:
        data = [{"file": "a.py"}, {"file": "b.py"}]
        result = upload_enrichment_json("bucket", "key.json", data)
        assert result is True


class TestUploadEnrichmentText:
    @patch("gharchive_etl.enrichment_r2._wrangler_r2_put")
    def test_upload_success(self, mock_put: MagicMock) -> None:
        result = upload_enrichment_text("bucket", "wiki.md", "# Hello")
        assert result is True
        mock_put.assert_called_once()

    def test_dry_run_skips_upload(self) -> None:
        result = upload_enrichment_text("bucket", "wiki.md", "# Hello", dry_run=True)
        assert result is True

    @patch("gharchive_etl.enrichment_r2._wrangler_r2_put")
    def test_upload_failure(self, mock_put: MagicMock) -> None:
        mock_put.side_effect = RuntimeError("upload failed")
        result = upload_enrichment_text("bucket", "wiki.md", "text")
        assert result is False
