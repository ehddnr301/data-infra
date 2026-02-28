"""GitHub API 클라이언트 테스트."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from gharchive_etl.config import GitHubApiConfig
from gharchive_etl.github_api import GitHubApiClient, GitHubApiResult


@pytest.fixture()
def api_config() -> GitHubApiConfig:
    return GitHubApiConfig(
        token_env_var="GITHUB_TOKEN",
        max_retries=2,
        backoff_factor=0.01,
        request_timeout_sec=5,
        rate_limit_buffer=10,
    )


@pytest.fixture()
def api_client(api_config: GitHubApiConfig, monkeypatch: pytest.MonkeyPatch) -> GitHubApiClient:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_12345")
    client = GitHubApiClient(api_config)
    yield client
    client.close()


class TestGitHubApiClientInit:
    def test_client_init_missing_token(
        self, api_config: GitHubApiConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="환경변수 GITHUB_TOKEN이 설정되지 않았습니다"):
            GitHubApiClient(api_config)

    def test_client_init_success(
        self, api_config: GitHubApiConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        client = GitHubApiClient(api_config)
        assert client.rate_remaining is None
        client.close()

    def test_context_manager(
        self, api_config: GitHubApiConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        with GitHubApiClient(api_config) as client:
            assert client is not None


class TestFetchCommitDetail:
    def test_success(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://api.github.com/repos/Pseudo-Lab/repo/commits/abc123",
            json={
                "sha": "abc123",
                "commit": {
                    "message": "fix bug",
                    "author": {"name": "dev", "email": "dev@test.com", "date": "2025-01-01T00:00:00Z"},
                    "committer": {"name": "dev", "date": "2025-01-01T00:00:00Z"},
                },
                "stats": {"total": 2, "additions": 1, "deletions": 1},
                "files": [
                    {"filename": "f.py", "status": "modified", "additions": 1, "deletions": 1, "changes": 2, "patch": "@@ -1 +1 @@\n-old\n+new"}
                ],
                "parents": [{"sha": "parent1"}],
                "node_id": "should_be_removed",
                "url": "should_be_removed",
            },
            headers={"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"},
        )
        httpx_mock.add_response(
            url="https://github.com/Pseudo-Lab/repo/commit/abc123.diff",
            text="diff --git a/f.py b/f.py\n-old\n+new\n",
        )
        result = api_client.fetch_commit_detail("Pseudo-Lab", "repo", "abc123")
        assert result.status_code == 200
        assert result.data["sha"] == "abc123"
        assert result.data["message"] == "fix bug"
        assert result.data["stats"]["total"] == 2
        assert result.data["files"][0]["patch"] == "@@ -1 +1 @@\n-old\n+new"
        assert result.data["diff"] == "diff --git a/f.py b/f.py\n-old\n+new\n"
        assert result.data["parents"] == ["parent1"]
        # 메타데이터 필드가 compact에서 제거되었는지 확인
        assert "node_id" not in result.data
        assert "url" not in result.data
        assert not result.skipped
        assert result.error is None

    def test_404_returns_skipped(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://api.github.com/repos/Pseudo-Lab/deleted/commits/xyz",
            status_code=404,
            headers={"X-RateLimit-Remaining": "4998"},
        )
        result = api_client.fetch_commit_detail("Pseudo-Lab", "deleted", "xyz")
        assert result.status_code == 404
        assert result.skipped is True

    def test_5xx_retry_then_success(
        self, api_client: GitHubApiClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url="https://api.github.com/repos/Pseudo-Lab/repo/commits/abc",
            status_code=500,
        )
        httpx_mock.add_response(
            url="https://api.github.com/repos/Pseudo-Lab/repo/commits/abc",
            json={
                "sha": "abc",
                "commit": {"message": "m", "author": {}, "committer": {}},
                "stats": {"total": 0, "additions": 0, "deletions": 0},
                "files": [],
                "parents": [],
            },
            headers={"X-RateLimit-Remaining": "4990"},
        )
        httpx_mock.add_response(
            url="https://github.com/Pseudo-Lab/repo/commit/abc.diff",
            text="",
        )
        result = api_client.fetch_commit_detail("Pseudo-Lab", "repo", "abc")
        assert result.status_code == 200
        assert result.data["sha"] == "abc"

    def test_5xx_exhaust_retries(
        self, api_client: GitHubApiClient, httpx_mock: HTTPXMock
    ) -> None:
        # max_retries=2 → 3 attempts total, all 500
        for _ in range(3):
            httpx_mock.add_response(
                url="https://api.github.com/repos/Pseudo-Lab/repo/commits/bad",
                status_code=500,
            )
        result = api_client.fetch_commit_detail("Pseudo-Lab", "repo", "bad")
        assert result.status_code == 500
        assert result.error is not None
        assert "Server error" in result.error

    def test_diff_fetch_failure_returns_none(
        self, api_client: GitHubApiClient, httpx_mock: HTTPXMock
    ) -> None:
        """diff URL 실패 시 diff=None, 나머지는 정상 반환."""
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/commits/s",
            json={
                "sha": "s",
                "commit": {"message": "m", "author": {}, "committer": {}},
                "stats": {"total": 0, "additions": 0, "deletions": 0},
                "files": [],
                "parents": [],
            },
            headers={"X-RateLimit-Remaining": "4999"},
        )
        httpx_mock.add_response(
            url="https://github.com/o/r/commit/s.diff",
            status_code=404,
        )
        result = api_client.fetch_commit_detail("o", "r", "s")
        assert result.status_code == 200
        assert result.data["sha"] == "s"
        assert result.data["diff"] is None


class TestRateLimit:
    def test_rate_limit_wait(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        """rate_remaining <= buffer 일 때 sleep이 호출된다."""
        import time

        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/commits/s",
            json={
                "sha": "s",
                "commit": {"message": "m", "author": {}, "committer": {}},
                "stats": {},
                "files": [],
                "parents": [],
            },
            headers={
                "X-RateLimit-Remaining": "5",  # <= buffer(10)
                "X-RateLimit-Reset": str(int(time.time()) - 1),  # already past
            },
        )
        httpx_mock.add_response(
            url="https://github.com/o/r/commit/s.diff",
            text="",
        )
        with patch("gharchive_etl.github_api.time.sleep") as mock_sleep:
            result = api_client.fetch_commit_detail("o", "r", "s")
            assert result.status_code == 200
            # sleep은 호출되어야 함 (wait <= 1+1=2초)
            mock_sleep.assert_called_once()

    def test_429_retry(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/commits/s",
            status_code=429,
            headers={"Retry-After": "0"},
        )
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/commits/s",
            json={
                "sha": "s",
                "commit": {"message": "m", "author": {}, "committer": {}},
                "stats": {},
                "files": [],
                "parents": [],
            },
            headers={"X-RateLimit-Remaining": "100"},
        )
        httpx_mock.add_response(
            url="https://github.com/o/r/commit/s.diff",
            text="",
        )
        result = api_client.fetch_commit_detail("o", "r", "s")
        assert result.status_code == 200


class TestPagination:
    def test_single_page(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        # PR detail
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/pulls/1",
            json={"title": "PR1", "body": "desc", "state": "open", "user": {"login": "dev"}, "created_at": "2025-01-01"},
            headers={"X-RateLimit-Remaining": "4990"},
        )
        # PR files
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/pulls/1/files?per_page=100",
            json=[{"filename": "a.py", "status": "added"}, {"filename": "b.py", "status": "modified"}],
            headers={"X-RateLimit-Remaining": "4990"},
        )
        # PR diff
        httpx_mock.add_response(
            url="https://github.com/o/r/pull/1.diff",
            text="diff --git a/a.py\n+new file\n",
        )
        result = api_client.fetch_pr_files("o", "r", 1)
        assert result.data["title"] == "PR1"
        assert result.data["body"] == "desc"
        assert result.data["author"] == "dev"
        assert len(result.data["files"]) == 2
        assert result.data["files"][0]["filename"] == "a.py"
        assert result.data["diff"] is not None

    def test_multi_page(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        # PR detail
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/pulls/1",
            json={"title": "PR1", "body": "b", "state": "merged", "user": {"login": "dev"}},
            headers={"X-RateLimit-Remaining": "4990"},
        )
        # PR files page 1
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/pulls/1/files?per_page=100",
            json=[{"filename": "a.py"}],
            headers={
                "Link": '<https://api.github.com/repos/o/r/pulls/1/files?page=2>; rel="next"',
                "X-RateLimit-Remaining": "4990",
            },
        )
        # PR files page 2
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/pulls/1/files?page=2",
            json=[{"filename": "b.py"}],
            headers={"X-RateLimit-Remaining": "4989"},
        )
        # PR diff
        httpx_mock.add_response(
            url="https://github.com/o/r/pull/1.diff",
            text="diff\n",
        )
        result = api_client.fetch_pr_files("o", "r", 1)
        assert len(result.data["files"]) == 2
        assert result.data["files"][1]["filename"] == "b.py"


class TestFetchMethods:
    def test_fetch_issue_comments(
        self, api_client: GitHubApiClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/issues/10/comments?per_page=100",
            json=[{"id": 1, "body": "comment", "user": {"login": "dev"}, "created_at": "2025-01-01", "updated_at": "2025-01-01", "author_association": "MEMBER"}],
            headers={"X-RateLimit-Remaining": "4990"},
        )
        comments = api_client.fetch_issue_comments("o", "r", 10)
        assert len(comments) == 1
        assert comments[0]["body"] == "comment"
        assert comments[0]["user"] == "dev"
        # URL 필드가 없어야 함
        assert "url" not in comments[0]

    def test_fetch_pr_reviews(
        self, api_client: GitHubApiClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url="https://api.github.com/repos/o/r/pulls/5/reviews?per_page=100",
            json=[{"id": 1, "state": "APPROVED", "body": "LGTM", "user": {"login": "reviewer"}, "submitted_at": "2025-01-01"}],
            headers={"X-RateLimit-Remaining": "4990"},
        )
        reviews = api_client.fetch_pr_reviews("o", "r", 5)
        assert len(reviews) == 1
        assert reviews[0]["state"] == "APPROVED"
        assert reviews[0]["body"] == "LGTM"
        assert reviews[0]["user"] == "reviewer"

    def test_fetch_user_profile(
        self, api_client: GitHubApiClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url="https://api.github.com/users/octocat",
            json={
                "login": "octocat", "id": 1, "name": "The Octocat", "type": "User",
                "url": "should_be_removed", "html_url": "should_be_removed",
                "followers_url": "should_be_removed",
            },
            headers={"X-RateLimit-Remaining": "4990"},
        )
        result = api_client.fetch_user_profile("octocat")
        assert result.status_code == 200
        assert result.data["login"] == "octocat"
        assert result.data["name"] == "The Octocat"
        # URL 필드가 compact에서 제거되었는지 확인
        assert "url" not in result.data
        assert "html_url" not in result.data
        assert "followers_url" not in result.data

    def test_fetch_wiki_page_success(
        self, api_client: GitHubApiClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url="https://raw.githubusercontent.com/wiki/o/r/Home.md",
            text="# Welcome",
        )
        result = api_client.fetch_wiki_page("o", "r", "Home")
        assert result.status_code == 200
        assert result.data["content"] == "# Welcome"

    def test_fetch_wiki_page_404(
        self, api_client: GitHubApiClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url="https://raw.githubusercontent.com/wiki/o/r/Missing.md",
            status_code=404,
        )
        result = api_client.fetch_wiki_page("o", "r", "Missing")
        assert result.status_code == 404
        assert result.skipped is True


class TestParseNextLink:
    def test_with_next(self) -> None:
        headers = {
            "Link": '<https://api.github.com/repos/o/r/pulls?page=2>; rel="next", '
            '<https://api.github.com/repos/o/r/pulls?page=5>; rel="last"'
        }
        assert (
            GitHubApiClient._parse_next_link(headers)
            == "https://api.github.com/repos/o/r/pulls?page=2"
        )

    def test_without_next(self) -> None:
        headers = {"Link": '<https://api.github.com/repos/o/r/pulls?page=1>; rel="prev"'}
        assert GitHubApiClient._parse_next_link(headers) is None

    def test_no_link_header(self) -> None:
        assert GitHubApiClient._parse_next_link({}) is None


class TestRequestWith304:
    """304 Not Modified 및 extra_headers 테스트."""

    def test_304_returns_none_data(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        """304 응답 시 data=None 반환."""
        httpx_mock.add_response(
            url="https://api.github.com/orgs/Pseudo-Lab/events?per_page=100",
            status_code=304,
            headers={"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"},
        )
        result = api_client.fetch_org_events("Pseudo-Lab", etag='W/"abc123"')
        assert result.status_code == 304
        assert result.data is None

    def test_extra_headers_passed(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        """extra_headers가 요청에 전달되는지 확인."""
        httpx_mock.add_response(
            url="https://api.github.com/orgs/Pseudo-Lab/events?per_page=100",
            json=[],
            headers={"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"},
        )
        result = api_client.fetch_org_events("Pseudo-Lab", etag='W/"test-etag"')
        assert result.status_code == 200
        # Verify the If-None-Match header was sent
        request = httpx_mock.get_requests()[0]
        assert request.headers.get("if-none-match") == 'W/"test-etag"'


class TestFetchOrgEvents:
    """org events 수집 테스트."""

    def test_basic_fetch(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        """기본 org events 수집."""
        events = [{"id": "1", "type": "PushEvent"}, {"id": "2", "type": "WatchEvent"}]
        httpx_mock.add_response(
            url="https://api.github.com/orgs/Pseudo-Lab/events?per_page=100",
            json=events,
            headers={"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"},
        )
        result = api_client.fetch_org_events("Pseudo-Lab")
        assert result.status_code == 200
        assert len(result.data) == 2

    def test_etag_not_modified_304(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        """ETag 기반 304 Not Modified."""
        httpx_mock.add_response(
            url="https://api.github.com/orgs/Pseudo-Lab/events?per_page=100",
            status_code=304,
            headers={"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"},
        )
        result = api_client.fetch_org_events("Pseudo-Lab", etag='W/"etag123"')
        assert result.status_code == 304
        assert result.data is None

    def test_pagination_multiple_pages(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        """페이지네이션으로 여러 페이지 수집."""
        page1 = [{"id": str(i)} for i in range(100)]
        page2 = [{"id": str(i)} for i in range(100, 150)]
        httpx_mock.add_response(
            url="https://api.github.com/orgs/Pseudo-Lab/events?per_page=100",
            json=page1,
            headers={
                "X-RateLimit-Remaining": "4998",
                "X-RateLimit-Reset": "9999999999",
                "Link": '<https://api.github.com/orgs/Pseudo-Lab/events?per_page=100&page=2>; rel="next"',
            },
        )
        httpx_mock.add_response(
            url="https://api.github.com/orgs/Pseudo-Lab/events?per_page=100&page=2",
            json=page2,
            headers={"X-RateLimit-Remaining": "4997", "X-RateLimit-Reset": "9999999999"},
        )
        result = api_client.fetch_org_events("Pseudo-Lab", max_pages=3)
        assert result.status_code == 200
        assert len(result.data) == 150

    @pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
    def test_max_pages_limit(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        """max_pages 제한으로 더 이상 수집하지 않음."""
        for i in range(3):
            page = [{"id": str(i * 100 + j)} for j in range(100)]
            headers = {
                "X-RateLimit-Remaining": str(4999 - i),
                "X-RateLimit-Reset": "9999999999",
            }
            if i < 2:  # pages 0,1 have next links
                headers["Link"] = f'<https://api.github.com/orgs/Pseudo-Lab/events?per_page=100&page={i+2}>; rel="next"'
            url = "https://api.github.com/orgs/Pseudo-Lab/events?per_page=100" if i == 0 else f"https://api.github.com/orgs/Pseudo-Lab/events?per_page=100&page={i+1}"
            httpx_mock.add_response(url=url, json=page, headers=headers)

        result = api_client.fetch_org_events("Pseudo-Lab", max_pages=2)
        assert len(result.data) == 200  # Only 2 pages, not 3


class TestFetchRepoEvents:
    """repo events 수집 테스트."""

    def test_basic_fetch(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        events = [{"id": "1"}, {"id": "2"}]
        httpx_mock.add_response(
            url="https://api.github.com/repos/Pseudo-Lab/repo/events?per_page=100",
            json=events,
            headers={"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"},
        )
        result = api_client.fetch_repo_events("Pseudo-Lab", "repo")
        assert result.status_code == 200
        assert len(result.data) == 2


class TestFetchOrgRepos:
    """org repos 조회 테스트."""

    def test_basic_fetch(self, api_client: GitHubApiClient, httpx_mock: HTTPXMock) -> None:
        repos = [{"name": "repo1"}, {"name": "repo2"}]
        httpx_mock.add_response(
            url="https://api.github.com/orgs/Pseudo-Lab/repos?per_page=100&type=public",
            json=repos,
            headers={"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"},
        )
        result = api_client.fetch_org_repos("Pseudo-Lab")
        assert result.status_code == 200
        assert len(result.data) == 2
        assert result.data[0]["name"] == "repo1"
