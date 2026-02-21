"""Enrichment R2 업로드 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gharchive_etl.enrichment_r2 import (
    build_enrichment_r2_key,
    check_r2_key_exists,
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
