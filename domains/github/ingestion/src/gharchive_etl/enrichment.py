"""Enrichment 수집 오케스트레이터.

DL 테이블에서 수집 대상을 추출하고, GitHub API → R2 저장까지의 흐름을 조율한다.
Priority 1: 코드 변경 상세 (커밋 diff, PR 파일)
Priority 2: 토론 맥락 (이슈/PR 댓글, PR 리뷰)
Priority 3: 프로필 & 위키 (유저 프로필, 위키 페이지)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from gharchive_etl.config import AppConfig, D1Config
from gharchive_etl.d1 import query_rows
from gharchive_etl.enrichment_r2 import (
    build_enrichment_r2_key,
    check_r2_key_exists,
    upload_enrichment_json,
    upload_enrichment_text,
)
from gharchive_etl.github_api import GitHubApiClient, GitHubApiResult

logger = logging.getLogger(__name__)


# ── 결과 데이터클래스 ─────────────────────────────────────


@dataclass
class EnrichmentProgress:
    """수집 진행 상황."""

    priority: int
    category: str
    total: int
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


# ── repo_name 파싱 ─────────────────────────────────────────


def _split_repo_name(repo_name: str) -> tuple[str, str] | None:
    """repo_name을 (owner, repo) 튜플로 분리한다."""
    parts = repo_name.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


# ── 수집 대상 추출 함수 ────────────────────────────────────


def extract_commit_targets(
    config: D1Config, *, base_date: str | None = None
) -> list[dict[str, Any]]:
    """dl_push_events에서 고유 (repo_name, commit_sha) 목록을 추출한다."""
    sql = (
        "SELECT DISTINCT repo_name, commit_sha "
        "FROM dl_push_events "
        "WHERE commit_sha != '__no_commits__'"
    )
    params: list[Any] = []
    if base_date:
        sql += " AND base_date = ?"
        params.append(base_date)
    return query_rows(sql, params, config)


def extract_pr_targets(
    config: D1Config, *, base_date: str | None = None
) -> list[dict[str, Any]]:
    """dl_pull_request_events에서 고유 (repo_name, pr_number) 목록을 추출한다."""
    sql = (
        "SELECT DISTINCT repo_name, pr_number "
        "FROM dl_pull_request_events "
        "WHERE pr_number IS NOT NULL"
    )
    params: list[Any] = []
    if base_date:
        sql += " AND base_date = ?"
        params.append(base_date)
    return query_rows(sql, params, config)


def extract_issue_targets(
    config: D1Config, *, base_date: str | None = None
) -> list[dict[str, Any]]:
    """dl_issues_events에서 고유 (repo_name, issue_number) 목록을 추출한다."""
    sql = (
        "SELECT DISTINCT repo_name, issue_number "
        "FROM dl_issues_events "
        "WHERE issue_number IS NOT NULL"
    )
    params: list[Any] = []
    if base_date:
        sql += " AND base_date = ?"
        params.append(base_date)
    return query_rows(sql, params, config)


def extract_pr_review_targets(
    config: D1Config, *, base_date: str | None = None
) -> list[dict[str, Any]]:
    """dl_pull_request_review_events에서 고유 (repo_name, pr_number) 목록을 추출한다."""
    sql = (
        "SELECT DISTINCT repo_name, pr_number "
        "FROM dl_pull_request_review_events "
        "WHERE pr_number IS NOT NULL"
    )
    params: list[Any] = []
    if base_date:
        sql += " AND base_date = ?"
        params.append(base_date)
    return query_rows(sql, params, config)


def extract_user_targets(config: D1Config) -> list[str]:
    """전체 DL 테이블에서 고유 user_login 목록을 추출한다."""
    logins: set[str] = set()

    # 공통 user_login 필드
    tables_with_user_login = [
        "dl_push_events",
        "dl_pull_request_events",
        "dl_issues_events",
        "dl_issue_comment_events",
        "dl_watch_events",
        "dl_fork_events",
        "dl_create_events",
        "dl_delete_events",
        "dl_pull_request_review_events",
        "dl_member_events",
        "dl_gollum_events",
        "dl_release_events",
        "dl_public_events",
    ]
    for table in tables_with_user_login:
        rows = query_rows(f"SELECT DISTINCT user_login FROM {table}", [], config)
        for row in rows:
            if row.get("user_login"):
                logins.add(row["user_login"])

    # PR author
    rows = query_rows(
        "SELECT DISTINCT pr_author_login FROM dl_pull_request_events "
        "WHERE pr_author_login IS NOT NULL",
        [],
        config,
    )
    for row in rows:
        if row.get("pr_author_login"):
            logins.add(row["pr_author_login"])

    # Issue author
    rows = query_rows(
        "SELECT DISTINCT issue_author_login FROM dl_issues_events "
        "WHERE issue_author_login IS NOT NULL",
        [],
        config,
    )
    for row in rows:
        if row.get("issue_author_login"):
            logins.add(row["issue_author_login"])

    # Member
    rows = query_rows(
        "SELECT DISTINCT member_login FROM dl_member_events "
        "WHERE member_login IS NOT NULL",
        [],
        config,
    )
    for row in rows:
        if row.get("member_login"):
            logins.add(row["member_login"])

    return sorted(logins)


def extract_wiki_targets(config: D1Config) -> list[dict[str, Any]]:
    """dl_gollum_events에서 고유 (repo_name, page_name) 목록을 추출한다."""
    return query_rows(
        "SELECT DISTINCT repo_name, page_name "
        "FROM dl_gollum_events "
        "WHERE page_name != '__no_pages__'",
        [],
        config,
    )


# ── 개별 항목 수집 공통 패턴 ────────────────────────────────


def _enrich_single_item(
    *,
    api: GitHubApiClient,
    bucket: str,
    r2_key: str,
    skip_existing: bool,
    dry_run: bool,
    fetch_fn: Callable[[], Any],
    upload_fn: Callable[[Any], bool],
    progress: EnrichmentProgress,
    label: str,
) -> None:
    """개별 항목 수집의 공통 패턴."""
    # 1. Skip check
    if skip_existing and not dry_run:
        if check_r2_key_exists(bucket, r2_key):
            progress.skipped += 1
            return

    # dry-run: 대상 카운트만 하고 실제 API 호출/업로드 생략
    if dry_run:
        progress.completed += 1
        return

    # 2. Fetch
    result = fetch_fn()

    # fetch_xxx 메서드에 따라 결과 타입이 다름
    if isinstance(result, GitHubApiResult):
        if result.skipped or result.error:
            progress.failed += 1
            if result.error:
                progress.errors.append(f"{label}: {result.error}")
            return
        data = result.data
    else:
        # list 반환 (paginated)
        data = result

    # 3. Upload
    if upload_fn(data):
        progress.completed += 1
    else:
        progress.failed += 1
        progress.errors.append(f"{label}: upload failed")


# ── Priority별 수집 함수 ───────────────────────────────────


def enrich_priority_1(
    api: GitHubApiClient,
    config: AppConfig,
    *,
    base_date: str | None = None,
    dry_run: bool = False,
    on_progress: Callable[[EnrichmentProgress], None] | None = None,
) -> list[EnrichmentProgress]:
    """Priority 1: 코드 변경 상세 수집 (커밋 상세, PR 파일 diff)."""
    results: list[EnrichmentProgress] = []
    bucket = config.r2.bucket_name
    skip_existing = config.github_api.skip_existing

    # 1-1. 커밋 상세
    targets = extract_commit_targets(config.d1, base_date=base_date)
    progress = EnrichmentProgress(priority=1, category="commits", total=len(targets))

    for i, target in enumerate(targets):
        repo_name = target.get("repo_name", "")
        sha = target.get("commit_sha", "")
        parsed = _split_repo_name(repo_name)
        if not parsed or not sha:
            progress.failed += 1
            continue

        owner, repo = parsed
        r2_key = build_enrichment_r2_key("commits", owner, repo, sha)
        label = f"commits/{owner}/{repo}/{sha[:8]}"

        _enrich_single_item(
            api=api,
            bucket=bucket,
            r2_key=r2_key,
            skip_existing=skip_existing,
            dry_run=dry_run,
            fetch_fn=lambda o=owner, r=repo, s=sha: api.fetch_commit_detail(o, r, s),
            upload_fn=lambda data, k=r2_key: upload_enrichment_json(
                bucket, k, data, dry_run=dry_run
            ),
            progress=progress,
            label=label,
        )

        if on_progress and (i + 1) % 50 == 0:
            on_progress(progress)

    results.append(progress)
    if on_progress:
        on_progress(progress)

    # 1-2. PR 파일 diff
    targets = extract_pr_targets(config.d1, base_date=base_date)
    progress = EnrichmentProgress(priority=1, category="pr-files", total=len(targets))

    for i, target in enumerate(targets):
        repo_name = target.get("repo_name", "")
        pr_number = target.get("pr_number")
        parsed = _split_repo_name(repo_name)
        if not parsed or pr_number is None:
            progress.failed += 1
            continue

        owner, repo = parsed
        r2_key = build_enrichment_r2_key("pr-files", owner, repo, str(pr_number))
        label = f"pr-files/{owner}/{repo}/PR#{pr_number}"

        _enrich_single_item(
            api=api,
            bucket=bucket,
            r2_key=r2_key,
            skip_existing=skip_existing,
            dry_run=dry_run,
            fetch_fn=lambda o=owner, r=repo, n=pr_number: api.fetch_pr_files(o, r, n),
            upload_fn=lambda data, k=r2_key: upload_enrichment_json(
                bucket, k, data, dry_run=dry_run
            ),
            progress=progress,
            label=label,
        )

        if on_progress and (i + 1) % 50 == 0:
            on_progress(progress)

    results.append(progress)
    if on_progress:
        on_progress(progress)

    return results


def enrich_priority_2(
    api: GitHubApiClient,
    config: AppConfig,
    *,
    base_date: str | None = None,
    dry_run: bool = False,
    on_progress: Callable[[EnrichmentProgress], None] | None = None,
) -> list[EnrichmentProgress]:
    """Priority 2: 토론 맥락 수집 (이슈 댓글, PR 댓글, PR 리뷰)."""
    results: list[EnrichmentProgress] = []
    bucket = config.r2.bucket_name
    skip_existing = config.github_api.skip_existing

    # 2-1. 이슈 댓글
    targets = extract_issue_targets(config.d1, base_date=base_date)
    progress = EnrichmentProgress(priority=2, category="issue-comments", total=len(targets))

    for i, target in enumerate(targets):
        repo_name = target.get("repo_name", "")
        issue_number = target.get("issue_number")
        parsed = _split_repo_name(repo_name)
        if not parsed or issue_number is None:
            progress.failed += 1
            continue

        owner, repo = parsed
        r2_key = build_enrichment_r2_key("issue-comments", owner, repo, str(issue_number))
        label = f"issue-comments/{owner}/{repo}/#{issue_number}"

        _enrich_single_item(
            api=api,
            bucket=bucket,
            r2_key=r2_key,
            skip_existing=skip_existing,
            dry_run=dry_run,
            fetch_fn=lambda o=owner, r=repo, n=issue_number: api.fetch_issue_comments(o, r, n),
            upload_fn=lambda data, k=r2_key: upload_enrichment_json(
                bucket, k, data, dry_run=dry_run
            ),
            progress=progress,
            label=label,
        )

        if on_progress and (i + 1) % 50 == 0:
            on_progress(progress)

    results.append(progress)
    if on_progress:
        on_progress(progress)

    # 2-2. PR 댓글 (PR도 issues API로 댓글 조회)
    pr_targets = extract_pr_targets(config.d1, base_date=base_date)
    progress = EnrichmentProgress(priority=2, category="pr-comments", total=len(pr_targets))

    for i, target in enumerate(pr_targets):
        repo_name = target.get("repo_name", "")
        pr_number = target.get("pr_number")
        parsed = _split_repo_name(repo_name)
        if not parsed or pr_number is None:
            progress.failed += 1
            continue

        owner, repo = parsed
        r2_key = build_enrichment_r2_key("pr-comments", owner, repo, str(pr_number))
        label = f"pr-comments/{owner}/{repo}/PR#{pr_number}"

        _enrich_single_item(
            api=api,
            bucket=bucket,
            r2_key=r2_key,
            skip_existing=skip_existing,
            dry_run=dry_run,
            fetch_fn=lambda o=owner, r=repo, n=pr_number: api.fetch_issue_comments(o, r, n),
            upload_fn=lambda data, k=r2_key: upload_enrichment_json(
                bucket, k, data, dry_run=dry_run
            ),
            progress=progress,
            label=label,
        )

        if on_progress and (i + 1) % 50 == 0:
            on_progress(progress)

    results.append(progress)
    if on_progress:
        on_progress(progress)

    # 2-3. PR 리뷰
    review_targets = extract_pr_review_targets(config.d1, base_date=base_date)
    progress = EnrichmentProgress(priority=2, category="pr-reviews", total=len(review_targets))

    for i, target in enumerate(review_targets):
        repo_name = target.get("repo_name", "")
        pr_number = target.get("pr_number")
        parsed = _split_repo_name(repo_name)
        if not parsed or pr_number is None:
            progress.failed += 1
            continue

        owner, repo = parsed
        r2_key = build_enrichment_r2_key("pr-reviews", owner, repo, str(pr_number))
        label = f"pr-reviews/{owner}/{repo}/PR#{pr_number}"

        _enrich_single_item(
            api=api,
            bucket=bucket,
            r2_key=r2_key,
            skip_existing=skip_existing,
            dry_run=dry_run,
            fetch_fn=lambda o=owner, r=repo, n=pr_number: api.fetch_pr_reviews(o, r, n),
            upload_fn=lambda data, k=r2_key: upload_enrichment_json(
                bucket, k, data, dry_run=dry_run
            ),
            progress=progress,
            label=label,
        )

        if on_progress and (i + 1) % 50 == 0:
            on_progress(progress)

    results.append(progress)
    if on_progress:
        on_progress(progress)

    return results


def enrich_priority_3(
    api: GitHubApiClient,
    config: AppConfig,
    *,
    dry_run: bool = False,
    on_progress: Callable[[EnrichmentProgress], None] | None = None,
) -> list[EnrichmentProgress]:
    """Priority 3: 프로필 & 위키 수집 (유저 프로필, 위키 페이지)."""
    results: list[EnrichmentProgress] = []
    bucket = config.r2.bucket_name
    skip_existing = config.github_api.skip_existing

    # 3-1. 유저 프로필
    logins = extract_user_targets(config.d1)
    progress = EnrichmentProgress(priority=3, category="users", total=len(logins))

    for i, login in enumerate(logins):
        r2_key = build_enrichment_r2_key("users", "", "", login)
        label = f"users/{login}"

        _enrich_single_item(
            api=api,
            bucket=bucket,
            r2_key=r2_key,
            skip_existing=skip_existing,
            dry_run=dry_run,
            fetch_fn=lambda l=login: api.fetch_user_profile(l),
            upload_fn=lambda data, k=r2_key: upload_enrichment_json(
                bucket, k, data, dry_run=dry_run
            ),
            progress=progress,
            label=label,
        )

        if on_progress and (i + 1) % 50 == 0:
            on_progress(progress)

    results.append(progress)
    if on_progress:
        on_progress(progress)

    # 3-2. 위키 페이지
    targets = extract_wiki_targets(config.d1)
    progress = EnrichmentProgress(priority=3, category="wiki", total=len(targets))

    for i, target in enumerate(targets):
        repo_name = target.get("repo_name", "")
        page_name = target.get("page_name", "")
        parsed = _split_repo_name(repo_name)
        if not parsed or not page_name:
            progress.failed += 1
            continue

        owner, repo = parsed
        r2_key = build_enrichment_r2_key("wiki", owner, repo, page_name, extension=".md")
        label = f"wiki/{owner}/{repo}/{page_name}"

        # Wiki는 별도 fetch + upload 패턴
        if skip_existing and not dry_run:
            if check_r2_key_exists(bucket, r2_key):
                progress.skipped += 1
                continue

        result = api.fetch_wiki_page(owner, repo, page_name)
        if result.skipped or result.error:
            progress.failed += 1
            if result.error:
                progress.errors.append(f"{label}: {result.error}")
            continue

        content = result.data.get("content", "") if result.data else ""
        if upload_enrichment_text(bucket, r2_key, content, dry_run=dry_run):
            progress.completed += 1
        else:
            progress.failed += 1
            progress.errors.append(f"{label}: upload failed")

        if on_progress and (i + 1) % 50 == 0:
            on_progress(progress)

    results.append(progress)
    if on_progress:
        on_progress(progress)

    return results
