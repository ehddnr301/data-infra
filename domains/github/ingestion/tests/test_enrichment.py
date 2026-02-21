"""Enrichment 수집 오케스트레이터 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gharchive_etl.config import AppConfig, D1Config, GitHubApiConfig, R2Config
from gharchive_etl.github_api import GitHubApiResult
from gharchive_etl.enrichment import (
    EnrichmentProgress,
    _split_repo_name,
    enrich_priority_1,
    enrich_priority_2,
    enrich_priority_3,
    extract_commit_targets,
    extract_issue_targets,
    extract_pr_review_targets,
    extract_pr_targets,
    extract_user_targets,
    extract_wiki_targets,
)


@pytest.fixture()
def mock_d1_config() -> D1Config:
    return D1Config(database_id="test-db", account_id="test-acct", api_token="test-token")


@pytest.fixture()
def mock_app_config(mock_d1_config: D1Config) -> AppConfig:
    return AppConfig(
        target_orgs=["Pseudo-Lab"],
        r2=R2Config(bucket_name="test-bucket"),
        d1=mock_d1_config,
        github_api=GitHubApiConfig(
            token_env_var="GITHUB_TOKEN",
            skip_existing=False,
            max_retries=1,
            backoff_factor=0.01,
        ),
    )


class TestSplitRepoName:
    def test_valid(self) -> None:
        assert _split_repo_name("Pseudo-Lab/some-repo") == ("Pseudo-Lab", "some-repo")

    def test_invalid_single(self) -> None:
        assert _split_repo_name("noslash") is None

    def test_invalid_empty_parts(self) -> None:
        assert _split_repo_name("/repo") is None
        assert _split_repo_name("org/") is None

    def test_invalid_too_many_parts(self) -> None:
        assert _split_repo_name("a/b/c") is None

    def test_empty_string(self) -> None:
        assert _split_repo_name("") is None


class TestExtractTargets:
    @patch("gharchive_etl.enrichment.query_rows")
    def test_extract_commit_targets(
        self, mock_query: MagicMock, mock_d1_config: D1Config
    ) -> None:
        mock_query.return_value = [
            {"repo_name": "Pseudo-Lab/repo1", "commit_sha": "abc"},
            {"repo_name": "Pseudo-Lab/repo2", "commit_sha": "def"},
        ]
        targets = extract_commit_targets(mock_d1_config)
        assert len(targets) == 2
        mock_query.assert_called_once()

    @patch("gharchive_etl.enrichment.query_rows")
    def test_extract_commit_targets_with_date(
        self, mock_query: MagicMock, mock_d1_config: D1Config
    ) -> None:
        mock_query.return_value = []
        extract_commit_targets(mock_d1_config, base_date="2024-01-15")
        sql = mock_query.call_args[0][0]
        assert "base_date = ?" in sql

    @patch("gharchive_etl.enrichment.query_rows")
    def test_extract_pr_targets(
        self, mock_query: MagicMock, mock_d1_config: D1Config
    ) -> None:
        mock_query.return_value = [{"repo_name": "Pseudo-Lab/repo", "pr_number": 42}]
        targets = extract_pr_targets(mock_d1_config)
        assert len(targets) == 1

    @patch("gharchive_etl.enrichment.query_rows")
    def test_extract_issue_targets(
        self, mock_query: MagicMock, mock_d1_config: D1Config
    ) -> None:
        mock_query.return_value = [{"repo_name": "Pseudo-Lab/repo", "issue_number": 10}]
        targets = extract_issue_targets(mock_d1_config)
        assert len(targets) == 1

    @patch("gharchive_etl.enrichment.query_rows")
    def test_extract_pr_review_targets(
        self, mock_query: MagicMock, mock_d1_config: D1Config
    ) -> None:
        mock_query.return_value = [{"repo_name": "Pseudo-Lab/repo", "pr_number": 5}]
        targets = extract_pr_review_targets(mock_d1_config)
        assert len(targets) == 1

    @patch("gharchive_etl.enrichment.query_rows")
    def test_extract_user_targets(
        self, mock_query: MagicMock, mock_d1_config: D1Config
    ) -> None:
        # user_login 테이블들에서 반환 + pr_author + issue_author + member
        def side_effect(sql: str, params: list, config: D1Config) -> list[dict]:
            if "pr_author_login" in sql:
                return [{"pr_author_login": "alice"}]
            if "issue_author_login" in sql:
                return [{"issue_author_login": "bob"}]
            if "member_login" in sql:
                return [{"member_login": "charlie"}]
            return [{"user_login": "alice"}]

        mock_query.side_effect = side_effect
        logins = extract_user_targets(mock_d1_config)
        assert "alice" in logins
        assert "bob" in logins
        assert "charlie" in logins

    @patch("gharchive_etl.enrichment.query_rows")
    def test_extract_wiki_targets(
        self, mock_query: MagicMock, mock_d1_config: D1Config
    ) -> None:
        mock_query.return_value = [{"repo_name": "Pseudo-Lab/repo", "page_name": "Home"}]
        targets = extract_wiki_targets(mock_d1_config)
        assert len(targets) == 1


class TestEnrichPriority1:
    @patch("gharchive_etl.enrichment.upload_enrichment_json")
    @patch("gharchive_etl.enrichment.extract_pr_targets")
    @patch("gharchive_etl.enrichment.extract_commit_targets")
    def test_flow(
        self,
        mock_commits: MagicMock,
        mock_prs: MagicMock,
        mock_upload: MagicMock,
        mock_app_config: AppConfig,
    ) -> None:
        mock_commits.return_value = [
            {"repo_name": "Pseudo-Lab/repo", "commit_sha": "abc123"},
        ]
        mock_prs.return_value = [
            {"repo_name": "Pseudo-Lab/repo", "pr_number": 42},
        ]
        mock_upload.return_value = True

        mock_api = MagicMock()
        mock_api.fetch_commit_detail.return_value = GitHubApiResult(
            url="", status_code=200, data={"sha": "abc123"}
        )
        mock_api.fetch_pr_files.return_value = [{"filename": "a.py"}]

        results = enrich_priority_1(mock_api, mock_app_config, dry_run=False)
        assert len(results) == 2  # commits + pr-files
        assert results[0].category == "commits"
        assert results[0].completed == 1
        assert results[1].category == "pr-files"
        assert results[1].completed == 1

    @patch("gharchive_etl.enrichment.upload_enrichment_json")
    @patch("gharchive_etl.enrichment.extract_pr_targets")
    @patch("gharchive_etl.enrichment.extract_commit_targets")
    def test_404_graceful(
        self,
        mock_commits: MagicMock,
        mock_prs: MagicMock,
        mock_upload: MagicMock,
        mock_app_config: AppConfig,
    ) -> None:
        mock_commits.return_value = [
            {"repo_name": "Pseudo-Lab/deleted", "commit_sha": "xyz"},
        ]
        mock_prs.return_value = []
        mock_upload.return_value = True

        mock_api = MagicMock()
        mock_api.fetch_commit_detail.return_value = GitHubApiResult(
            url="", status_code=404, error="Not found (404)", skipped=True
        )

        results = enrich_priority_1(mock_api, mock_app_config)
        assert results[0].failed == 1
        assert results[0].completed == 0

    @patch("gharchive_etl.enrichment.check_r2_key_exists")
    @patch("gharchive_etl.enrichment.extract_pr_targets")
    @patch("gharchive_etl.enrichment.extract_commit_targets")
    def test_skip_existing(
        self,
        mock_commits: MagicMock,
        mock_prs: MagicMock,
        mock_exists: MagicMock,
        mock_app_config: AppConfig,
    ) -> None:
        mock_app_config.github_api.skip_existing = True
        mock_commits.return_value = [
            {"repo_name": "Pseudo-Lab/repo", "commit_sha": "abc"},
        ]
        mock_prs.return_value = []
        mock_exists.return_value = True

        mock_api = MagicMock()
        results = enrich_priority_1(mock_api, mock_app_config)
        assert results[0].skipped == 1
        assert results[0].completed == 0
        mock_api.fetch_commit_detail.assert_not_called()


class TestEnrichPriority2:
    @patch("gharchive_etl.enrichment.upload_enrichment_json")
    @patch("gharchive_etl.enrichment.extract_pr_review_targets")
    @patch("gharchive_etl.enrichment.extract_pr_targets")
    @patch("gharchive_etl.enrichment.extract_issue_targets")
    def test_flow(
        self,
        mock_issues: MagicMock,
        mock_prs: MagicMock,
        mock_reviews: MagicMock,
        mock_upload: MagicMock,
        mock_app_config: AppConfig,
    ) -> None:
        mock_issues.return_value = [{"repo_name": "Pseudo-Lab/repo", "issue_number": 10}]
        mock_prs.return_value = [{"repo_name": "Pseudo-Lab/repo", "pr_number": 42}]
        mock_reviews.return_value = [{"repo_name": "Pseudo-Lab/repo", "pr_number": 5}]
        mock_upload.return_value = True

        mock_api = MagicMock()
        mock_api.fetch_issue_comments.return_value = [{"id": 1}]
        mock_api.fetch_pr_reviews.return_value = [{"id": 1}]

        results = enrich_priority_2(mock_api, mock_app_config)
        assert len(results) == 3  # issue-comments, pr-comments, pr-reviews


class TestEnrichPriority3:
    @patch("gharchive_etl.enrichment.upload_enrichment_text")
    @patch("gharchive_etl.enrichment.upload_enrichment_json")
    @patch("gharchive_etl.enrichment.extract_wiki_targets")
    @patch("gharchive_etl.enrichment.extract_user_targets")
    def test_flow(
        self,
        mock_users: MagicMock,
        mock_wiki: MagicMock,
        mock_upload_json: MagicMock,
        mock_upload_text: MagicMock,
        mock_app_config: AppConfig,
    ) -> None:
        mock_users.return_value = ["octocat"]
        mock_wiki.return_value = [{"repo_name": "Pseudo-Lab/repo", "page_name": "Home"}]
        mock_upload_json.return_value = True
        mock_upload_text.return_value = True

        mock_api = MagicMock()
        mock_api.fetch_user_profile.return_value = GitHubApiResult(
            url="", status_code=200, data={"login": "octocat"}
        )
        mock_api.fetch_wiki_page.return_value = GitHubApiResult(
            url="", status_code=200, data={"content": "# Wiki"}
        )

        results = enrich_priority_3(mock_api, mock_app_config)
        assert len(results) == 2  # users, wiki
        assert results[0].category == "users"
        assert results[0].completed == 1
        assert results[1].category == "wiki"
        assert results[1].completed == 1
