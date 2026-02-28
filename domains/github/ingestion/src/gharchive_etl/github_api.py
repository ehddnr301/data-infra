"""GitHub REST API 동기 클라이언트.

GitHub API를 호출하여 커밋 상세, PR 파일, 이슈/PR 댓글, 리뷰, 유저 프로필, 위키 페이지를 수집한다.
- rate limit 사전 대기 (buffer 기반)
- 429/5xx 지수 백오프 재시도
- Link 헤더 기반 pagination
"""

from __future__ import annotations

import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from gharchive_etl.config import GitHubApiConfig

logger = logging.getLogger(__name__)


@dataclass
class GitHubApiResult:
    """API 호출 결과."""

    url: str
    status_code: int
    data: dict[str, Any] | list[Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    skipped: bool = False


class GitHubApiClient:
    """GitHub REST API 동기 클라이언트."""

    def __init__(self, config: GitHubApiConfig) -> None:
        token = os.environ.get(config.token_env_var, "")
        if not token:
            raise RuntimeError(f"환경변수 {config.token_env_var}이 설정되지 않았습니다")

        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "gharchive-etl/0.1.0 (pseudolab)",
            },
            timeout=config.request_timeout_sec,
        )
        self._rate_remaining: int | None = None
        self._rate_reset: float | None = None

    def _check_rate_limit(self, response: httpx.Response) -> None:
        """응답 헤더에서 rate limit 정보를 갱신하고, 필요시 대기한다."""
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_at = response.headers.get("X-RateLimit-Reset")

        if remaining is not None:
            self._rate_remaining = int(remaining)
        if reset_at is not None:
            self._rate_reset = float(reset_at)

        if (
            self._rate_remaining is not None
            and self._rate_remaining <= self._config.rate_limit_buffer
            and self._rate_reset is not None
        ):
            wait_seconds = max(0, self._rate_reset - time.time()) + 1
            logger.warning(
                "Rate limit approaching (%d remaining), waiting %.0fs until reset",
                self._rate_remaining,
                wait_seconds,
            )
            time.sleep(wait_seconds)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> GitHubApiResult:
        """공통 요청 메서드 (rate limit 체크 → 요청 → 재시도)."""
        max_retries = self._config.max_retries
        backoff_factor = self._config.backoff_factor

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                resp = self._client.request(method, path, params=params, headers=extra_headers)

                self._check_rate_limit(resp)

                # 304: Not Modified (ETag 조건부 요청)
                if resp.status_code == 304:
                    return GitHubApiResult(
                        url=str(resp.url),
                        status_code=304,
                        data=None,
                        headers=dict(resp.headers),
                    )

                # 429: rate limited
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else (backoff_factor ** (attempt + 1))
                    logger.warning("Rate limited (429), waiting %.0fs", wait)
                    if attempt < max_retries:
                        time.sleep(wait)
                        continue
                    return GitHubApiResult(
                        url=str(resp.url),
                        status_code=429,
                        headers=dict(resp.headers),
                        error="Rate limited after max retries",
                    )

                # 404: 삭제된 리소스
                if resp.status_code == 404:
                    return GitHubApiResult(
                        url=str(resp.url),
                        status_code=404,
                        headers=dict(resp.headers),
                        skipped=True,
                        error="Not found (404)",
                    )

                # 403 (rate limit 아닌 경우): 권한 없음
                if resp.status_code == 403:
                    return GitHubApiResult(
                        url=str(resp.url),
                        status_code=403,
                        headers=dict(resp.headers),
                        skipped=True,
                        error="Forbidden (403)",
                    )

                # 기타 4xx: skip
                if 400 <= resp.status_code < 500:
                    return GitHubApiResult(
                        url=str(resp.url),
                        status_code=resp.status_code,
                        headers=dict(resp.headers),
                        skipped=True,
                        error=f"Client error ({resp.status_code})",
                    )

                # 5xx: 재시도
                if resp.status_code >= 500:
                    if attempt < max_retries:
                        delay = backoff_factor ** (attempt + 1) + random.uniform(0, 1)
                        logger.warning(
                            "Server error %d, retry %d/%d in %.1fs",
                            resp.status_code,
                            attempt + 1,
                            max_retries,
                            delay,
                        )
                        time.sleep(delay)
                        continue
                    return GitHubApiResult(
                        url=str(resp.url),
                        status_code=resp.status_code,
                        headers=dict(resp.headers),
                        error=f"Server error ({resp.status_code}) after {max_retries} retries",
                    )

                # 성공 (2xx)
                data = resp.json() if resp.content else None
                return GitHubApiResult(
                    url=str(resp.url),
                    status_code=resp.status_code,
                    data=data,
                    headers=dict(resp.headers),
                )

            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < max_retries:
                    delay = backoff_factor ** (attempt + 1) + random.uniform(0, 1)
                    logger.warning(
                        "Timeout, retry %d/%d in %.1fs: %s",
                        attempt + 1,
                        max_retries,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                    continue

        return GitHubApiResult(
            url=path,
            status_code=0,
            error=f"Timeout after {max_retries} retries: {last_exc}",
        )

    @staticmethod
    def _parse_next_link(headers: dict[str, str]) -> str | None:
        """Link 헤더에서 rel="next" URL을 추출한다."""
        link_header = headers.get("link") or headers.get("Link")
        if not link_header:
            return None

        for part in link_header.split(","):
            match = re.search(r'<([^>]+)>;\s*rel="next"', part)
            if match:
                return match.group(1)
        return None

    def _paginated_get(self, path: str, *, per_page: int = 100, extra_params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Link 헤더 기반 pagination으로 전체 결과를 수집한다."""
        all_items: list[dict[str, Any]] = []
        url: str | None = path
        params: dict[str, Any] | None = {"per_page": per_page}
        if extra_params:
            params.update(extra_params)

        while url:
            result = self._request("GET", url, params=params)
            if result.error or result.skipped:
                break
            if isinstance(result.data, list):
                all_items.extend(result.data)
            next_url = self._parse_next_link(result.headers)
            if next_url:
                url = next_url
                params = None  # 다음 페이지 URL에 이미 params 포함
            else:
                url = None

        return all_items

    # ── 응답 필터링 ─────────────────────────────────────────

    @staticmethod
    def _compact_commit(data: dict[str, Any]) -> dict[str, Any]:
        """커밋 응답에서 코드 변경 상세만 추출한다."""
        commit = data.get("commit", {})
        return {
            "sha": data.get("sha"),
            "message": commit.get("message"),
            "author": {
                "name": commit.get("author", {}).get("name"),
                "email": commit.get("author", {}).get("email"),
                "date": commit.get("author", {}).get("date"),
            },
            "committer": {
                "name": commit.get("committer", {}).get("name"),
                "date": commit.get("committer", {}).get("date"),
            },
            "stats": data.get("stats"),
            "files": [
                {
                    "filename": f.get("filename"),
                    "status": f.get("status"),
                    "additions": f.get("additions"),
                    "deletions": f.get("deletions"),
                    "changes": f.get("changes"),
                    "patch": f.get("patch"),
                }
                for f in data.get("files", [])
            ],
            "parents": [p.get("sha") for p in data.get("parents", [])],
        }

    @staticmethod
    def _compact_file(f: dict[str, Any]) -> dict[str, Any]:
        """PR 파일 항목에서 diff 정보만 추출한다."""
        return {
            "filename": f.get("filename"),
            "status": f.get("status"),
            "additions": f.get("additions"),
            "deletions": f.get("deletions"),
            "changes": f.get("changes"),
            "patch": f.get("patch"),
        }

    @staticmethod
    def _compact_comment(c: dict[str, Any]) -> dict[str, Any]:
        """이슈/PR 댓글에서 본문과 작성자 정보만 추출한다."""
        return {
            "id": c.get("id"),
            "user": c.get("user", {}).get("login"),
            "body": c.get("body"),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
            "author_association": c.get("author_association"),
        }

    @staticmethod
    def _compact_review(r: dict[str, Any]) -> dict[str, Any]:
        """PR 리뷰에서 핵심 정보만 추출한다."""
        return {
            "id": r.get("id"),
            "user": r.get("user", {}).get("login"),
            "state": r.get("state"),
            "body": r.get("body"),
            "submitted_at": r.get("submitted_at"),
            "author_association": r.get("author_association"),
        }

    @staticmethod
    def _compact_user(data: dict[str, Any]) -> dict[str, Any]:
        """유저 프로필에서 핵심 정보만 추출한다."""
        return {
            "login": data.get("login"),
            "id": data.get("id"),
            "type": data.get("type"),
            "name": data.get("name"),
            "company": data.get("company"),
            "blog": data.get("blog"),
            "location": data.get("location"),
            "email": data.get("email"),
            "bio": data.get("bio"),
            "twitter_username": data.get("twitter_username"),
            "public_repos": data.get("public_repos"),
            "public_gists": data.get("public_gists"),
            "followers": data.get("followers"),
            "following": data.get("following"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }

    def fetch_org_events(
        self, org: str, *, per_page: int = 100, max_pages: int = 3, etag: str | None = None,
    ) -> GitHubApiResult:
        """GET /orgs/{org}/events — org 단위 공개 이벤트 수집.

        ETag 기반 조건부 요청을 지원한다. 최대 max_pages 페이지까지 수집.
        """
        extra_headers = {"If-None-Match": etag} if etag else None
        first_result = self._request(
            "GET", f"/orgs/{org}/events",
            params={"per_page": per_page},
            extra_headers=extra_headers,
        )
        if first_result.status_code == 304 or first_result.error or first_result.skipped:
            return first_result

        all_events: list[dict[str, Any]] = []
        if isinstance(first_result.data, list):
            all_events.extend(first_result.data)

        # 추가 페이지 수집 (최대 max_pages - 1 추가 페이지)
        next_url = self._parse_next_link(first_result.headers)
        pages_fetched = 1
        while next_url and pages_fetched < max_pages:
            result = self._request("GET", next_url)
            if result.error or result.skipped:
                break
            if isinstance(result.data, list):
                all_events.extend(result.data)
            next_url = self._parse_next_link(result.headers)
            pages_fetched += 1

        return GitHubApiResult(
            url=f"/orgs/{org}/events",
            status_code=first_result.status_code,
            data=all_events,
            headers=first_result.headers,
        )

    def fetch_repo_events(
        self, owner: str, repo: str, *, per_page: int = 100,
    ) -> GitHubApiResult:
        """GET /repos/{owner}/{repo}/events — repo 단위 이벤트 수집."""
        items = self._paginated_get(f"/repos/{owner}/{repo}/events", per_page=per_page)
        return GitHubApiResult(
            url=f"/repos/{owner}/{repo}/events",
            status_code=200,
            data=items,
        )

    def fetch_org_repos(
        self, org: str, *, repo_type: str = "public", per_page: int = 100,
    ) -> GitHubApiResult:
        """GET /orgs/{org}/repos — org의 repo 목록 조회."""
        items = self._paginated_get(
            f"/orgs/{org}/repos",
            per_page=per_page,
            extra_params={"type": repo_type},
        )
        return GitHubApiResult(
            url=f"/orgs/{org}/repos",
            status_code=200,
            data=items,
        )

    # ── 공개 API 메서드 ──────────────────────────────────────

    def _fetch_diff(self, url: str) -> str | None:
        """GitHub .diff URL에서 전체 unified diff 텍스트를 가져온다.

        github.com 도메인이므로 API 클라이언트가 아닌 별도 요청을 사용한다.
        """
        try:
            resp = httpx.get(
                url,
                headers={"Authorization": self._client.headers["Authorization"]},
                timeout=self._config.request_timeout_sec,
                follow_redirects=True,
            )
            if resp.status_code == 200:
                return resp.text
            logger.warning("Failed to fetch diff from %s: %d", url, resp.status_code)
        except httpx.TimeoutException:
            logger.warning("Timeout fetching diff from %s", url)
        return None

    def fetch_commit_detail(self, owner: str, repo: str, sha: str) -> GitHubApiResult:
        """GET /repos/{owner}/{repo}/commits/{sha} — 코드 변경 상세 + 전체 diff."""
        result = self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}")
        if result.data and not result.error:
            compact = self._compact_commit(result.data)
            # 전체 unified diff 다운로드
            diff_url = f"https://github.com/{owner}/{repo}/commit/{sha}.diff"
            compact["diff"] = self._fetch_diff(diff_url)
            result.data = compact
        return result

    def fetch_pr_files(self, owner: str, repo: str, pr_number: int) -> GitHubApiResult:
        """PR 상세 (제목, 본문, 작성자) + 파일 목록 + 전체 unified diff."""
        # PR 메타 정보 (제목, 본문, 상태)
        pr_result = self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        pr_meta: dict[str, Any] = {}
        if pr_result.data and not pr_result.error:
            pr_data = pr_result.data
            pr_meta = {
                "title": pr_data.get("title"),
                "body": pr_data.get("body"),
                "state": pr_data.get("state"),
                "author": (pr_data.get("user") or {}).get("login"),
                "created_at": pr_data.get("created_at"),
                "merged_at": pr_data.get("merged_at"),
                "closed_at": pr_data.get("closed_at"),
            }
        elif pr_result.error:
            return pr_result  # 404/403 등은 그대로 반환

        # 파일 목록
        items = self._paginated_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/files")
        compact_files = [self._compact_file(f) for f in items]

        # 전체 unified diff 다운로드
        diff_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}.diff"
        diff_text = self._fetch_diff(diff_url)

        return GitHubApiResult(
            url=f"/repos/{owner}/{repo}/pulls/{pr_number}",
            status_code=200,
            data={**pr_meta, "files": compact_files, "diff": diff_text},
        )

    def fetch_issue_comments(
        self, owner: str, repo: str, issue_number: int
    ) -> list[dict[str, Any]]:
        """GET /repos/{owner}/{repo}/issues/{n}/comments — 본문과 작성자만 반환."""
        items = self._paginated_get(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")
        return [self._compact_comment(c) for c in items]

    def fetch_pr_reviews(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """GET /repos/{owner}/{repo}/pulls/{n}/reviews — 핵심 리뷰 정보만 반환."""
        items = self._paginated_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")
        return [self._compact_review(r) for r in items]

    def fetch_user_profile(self, login: str) -> GitHubApiResult:
        """GET /users/{login} — 핵심 프로필 정보만 반환."""
        result = self._request("GET", f"/users/{login}")
        if result.data and not result.error:
            result.data = self._compact_user(result.data)
        return result

    def fetch_wiki_page(self, owner: str, repo: str, page_name: str) -> GitHubApiResult:
        """raw.githubusercontent.com에서 위키 페이지를 가져온다."""
        wiki_url = f"https://raw.githubusercontent.com/wiki/{owner}/{repo}/{page_name}.md"
        try:
            resp = httpx.get(wiki_url, timeout=self._config.request_timeout_sec)
            if resp.status_code == 200:
                return GitHubApiResult(
                    url=wiki_url,
                    status_code=200,
                    data={"content": resp.text},
                    headers=dict(resp.headers),
                )
            return GitHubApiResult(
                url=wiki_url,
                status_code=resp.status_code,
                skipped=resp.status_code == 404,
                error=f"Wiki fetch failed ({resp.status_code})",
            )
        except httpx.TimeoutException:
            return GitHubApiResult(
                url=wiki_url,
                status_code=0,
                error="Wiki fetch timeout",
            )

    @property
    def rate_remaining(self) -> int | None:
        """현재 남은 rate limit."""
        return self._rate_remaining

    def close(self) -> None:
        """httpx.Client를 종료한다."""
        self._client.close()

    def __enter__(self) -> GitHubApiClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
