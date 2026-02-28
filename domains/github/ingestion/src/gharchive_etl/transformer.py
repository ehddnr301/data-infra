"""이벤트 필터링 후 D1 DL 테이블 적재를 위한 가공 로직.

기존 단일 events 테이블 구조에서 14개 타입별 DL 테이블 구조로 전환.
- 각 이벤트 타입별 전용 변환 함수
- created_at(UTC) → ts_kst(KST) + base_date(KST) 변환
- PushEvent/GollumEvent는 배열 펼침 (1 event → N rows)
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from gharchive_etl.dl_models import (
    DL_TABLE_COLUMNS,
    EVENT_TYPE_TO_TABLE,
    TABLE_TO_EVENT_TYPE,
)
from gharchive_etl.models import GitHubEvent

logger = logging.getLogger(__name__)

# ── 타입 별칭 ────────────────────────────────────────────────

DLRowsByTable = dict[str, list[dict[str, Any]]]
"""테이블명 → Row 리스트 매핑."""


# ── KST 변환 ─────────────────────────────────────────────────

_KST = timezone(timedelta(hours=9))


def _to_kst(created_at: datetime) -> tuple[str, str]:
    """UTC datetime → (ts_kst ISO문자열, base_date YYYY-MM-DD) 변환.

    naive datetime이면 UTC로 간주.
    """
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    kst_dt = created_at.astimezone(_KST)
    ts_kst = kst_dt.isoformat()
    base_date = kst_dt.strftime("%Y-%m-%d")
    return ts_kst, base_date


# ── 공통 필드 빌더 ───────────────────────────────────────────

def _common(event: GitHubEvent) -> dict[str, Any]:
    """이벤트에서 공통 6개 필드를 추출한다."""
    ts_kst, base_date = _to_kst(event.created_at)
    return {
        "event_id": event.id,
        "repo_name": event.repo.name,
        "organization": event.org.login if event.org else None,
        "user_login": event.actor.login,
        "ts_kst": ts_kst,
        "base_date": base_date,
    }


# ── 타입별 변환 함수 ─────────────────────────────────────────

def _to_push_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """PushEvent → 커밋 단위 펼침 rows."""
    c = _common(event)
    payload = event.payload
    ref_full = payload.get("ref") or ""
    ref_name = re.sub(r"^(refs/heads/|refs/tags/)", "", ref_full) if ref_full else None

    push_meta = {
        "ref_full": ref_full or None,
        "ref_name": ref_name,
        "is_branch_ref": 1 if ref_full.startswith("refs/heads/") else 0,
        "is_tag_ref": 1 if ref_full.startswith("refs/tags/") else 0,
        "head_sha": payload.get("head"),
        "before_sha": payload.get("before"),
    }

    commits = payload.get("commits", [])
    if not commits:
        return [{
            **c, **push_meta,
            "commit_sha": "__empty__#0",
            "commit_author_name": None,
            "commit_author_email": None,
            "commit_message": None,
            "commit_distinct": None,
            "commit_url": None,
        }]

    rows = []
    for idx, commit in enumerate(commits):
        rows.append({
            **c, **push_meta,
            "commit_sha": commit.get("sha") or f"__no_commit__#{idx}",
            "commit_author_name": (commit.get("author") or {}).get("name"),
            "commit_author_email": (commit.get("author") or {}).get("email"),
            "commit_message": (commit.get("message") or "")[:200],
            "commit_distinct": 1 if commit.get("distinct") else 0,
            "commit_url": commit.get("url"),
        })
    return rows


def _to_pull_request_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """PullRequestEvent → 1 row."""
    c = _common(event)
    payload = event.payload
    pr = payload.get("pull_request", {})
    user = pr.get("user") or {}
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    return [{
        **c,
        "pr_action": payload.get("action"),
        "pr_number": payload.get("number"),
        "pr_title": pr.get("title"),
        "pr_html_url": pr.get("html_url"),
        "pr_state": pr.get("state"),
        "is_draft": 1 if pr.get("draft") else (0 if pr.get("draft") is not None else None),
        "pr_body": pr.get("body"),
        "pr_author_login": user.get("login"),
        "pr_author_id": user.get("id"),
        "head_ref": head.get("ref"),
        "base_ref": base.get("ref"),
        "head_sha": head.get("sha"),
        "base_sha": base.get("sha"),
        "commits_count": pr.get("commits"),
        "additions": pr.get("additions"),
        "deletions": pr.get("deletions"),
        "changed_files": pr.get("changed_files"),
        "issue_comments_count": pr.get("comments"),
        "review_comments_count": pr.get("review_comments"),
        "is_merged": 1 if pr.get("merged") else (0 if pr.get("merged") is not None else None),
        "merge_commit_sha": pr.get("merge_commit_sha"),
    }]


def _to_issues_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """IssuesEvent → 1 row."""
    c = _common(event)
    payload = event.payload
    issue = payload.get("issue", {})
    user = issue.get("user") or {}
    return [{
        **c,
        "issue_action": payload.get("action"),
        "issue_number": issue.get("number"),
        "issue_title": issue.get("title"),
        "issue_body": issue.get("body"),
        "issue_state": issue.get("state"),
        "issue_html_url": issue.get("html_url"),
        "issue_author_login": user.get("login"),
        "issue_author_id": user.get("id"),
    }]


def _to_issue_comment_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """IssueCommentEvent → 1 row."""
    c = _common(event)
    payload = event.payload
    issue = payload.get("issue", {})
    comment = payload.get("comment", {})
    issue_user = issue.get("user") or {}
    comment_user = comment.get("user") or {}
    return [{
        **c,
        "ic_action": payload.get("action"),
        "issue_number": issue.get("number"),
        "issue_title": issue.get("title"),
        "issue_state": issue.get("state"),
        "issue_html_url": issue.get("html_url"),
        "issue_author_login": issue_user.get("login"),
        "issue_author_id": issue_user.get("id"),
        "comment_id": comment.get("id"),
        "comment_html_url": comment.get("html_url"),
        "comment_body": comment.get("body"),
        "commenter_login": comment_user.get("login"),
        "commenter_id": comment_user.get("id"),
    }]


def _to_watch_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """WatchEvent → 1 row (공통 필드만)."""
    return [_common(event)]


def _to_fork_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """ForkEvent → 1 row."""
    c = _common(event)
    forkee = event.payload.get("forkee", {})
    owner = forkee.get("owner") or {}
    return [{
        **c,
        "forkee_id": forkee.get("id"),
        "forkee_full_name": forkee.get("full_name"),
        "forkee_html_url": forkee.get("html_url"),
        "forkee_owner_login": owner.get("login"),
        "forkee_owner_id": owner.get("id"),
        "forkee_description": forkee.get("description"),
        "is_fork_private": 1 if forkee.get("private") else (0 if forkee.get("private") is not None else None),
        "forkee_default_branch": forkee.get("default_branch"),
    }]


def _to_create_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """CreateEvent → 1 row."""
    c = _common(event)
    payload = event.payload
    ref_type = payload.get("ref_type", "")
    return [{
        **c,
        "created_ref_type": ref_type or None,
        "created_ref_name": payload.get("ref"),
        "default_branch": payload.get("master_branch"),
        "repo_description": payload.get("description"),
        "pusher_type": payload.get("pusher_type"),
        "is_repo_creation": 1 if ref_type == "repository" else 0,
        "is_branch_creation": 1 if ref_type == "branch" else 0,
        "is_tag_creation": 1 if ref_type == "tag" else 0,
    }]


def _to_delete_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """DeleteEvent → 1 row."""
    c = _common(event)
    payload = event.payload
    ref_type = payload.get("ref_type", "")
    return [{
        **c,
        "deleted_ref_type": ref_type or None,
        "deleted_ref_name": payload.get("ref"),
        "pusher_type": payload.get("pusher_type"),
        "is_branch_deletion": 1 if ref_type == "branch" else 0,
        "is_tag_deletion": 1 if ref_type == "tag" else 0,
    }]


def _to_pull_request_review_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """PullRequestReviewEvent → 1 row."""
    c = _common(event)
    payload = event.payload
    review = payload.get("review", {})
    pr = payload.get("pull_request", {})
    reviewer = review.get("user") or {}
    pr_user = pr.get("user") or {}

    submitted_at_utc = review.get("submitted_at")
    submitted_at_kst = None
    if submitted_at_utc:
        try:
            raw = submitted_at_utc
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            submitted_at_kst = dt.astimezone(_KST).isoformat()
        except (ValueError, TypeError):
            pass

    return [{
        **c,
        "reviewer_login": reviewer.get("login"),
        "reviewer_id": reviewer.get("id"),
        "review_state": review.get("state"),
        "review_body": review.get("body"),
        "review_html_url": review.get("html_url"),
        "commit_sha": review.get("commit_id"),
        "review_submitted_at_utc": submitted_at_utc,
        "review_submitted_at_kst": submitted_at_kst,
        "pr_number": pr.get("number"),
        "pr_title": pr.get("title"),
        "pr_html_url": pr.get("html_url"),
        "pr_author_login": pr_user.get("login"),
    }]


def _to_pull_request_review_comment_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """PullRequestReviewCommentEvent → 1 row."""
    c = _common(event)
    payload = event.payload
    comment = payload.get("comment", {})
    pr = payload.get("pull_request", {})
    comment_user = comment.get("user") or {}
    return [{
        **c,
        "pr_review_comment_action": payload.get("action"),
        "review_comment_id": comment.get("id"),
        "review_comment_html_url": comment.get("html_url"),
        "review_comment_body": comment.get("body"),
        "diff_hunk": comment.get("diff_hunk"),
        "file_path": comment.get("path"),
        "commit_id": comment.get("commit_id"),
        "review_id": comment.get("pull_request_review_id"),
        "commenter_login": comment_user.get("login"),
        "commenter_id": comment_user.get("id"),
        "pr_number": pr.get("number"),
        "pr_title": pr.get("title"),
        "pr_html_url": pr.get("html_url"),
        "pr_state": pr.get("state"),
    }]


def _to_member_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """MemberEvent → 1 row."""
    c = _common(event)
    payload = event.payload
    member = payload.get("member", {})
    action = payload.get("action", "")
    return [{
        **c,
        "member_login": member.get("login"),
        "member_id": member.get("id"),
        "member_html_url": member.get("html_url"),
        "member_action": action or None,
        "is_member_added": 1 if action == "added" else 0,
        "is_member_removed": 1 if action == "removed" else 0,
    }]


def _to_gollum_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """GollumEvent → 페이지 단위 펼침 rows."""
    c = _common(event)
    pages = event.payload.get("pages", [])

    if not pages:
        return [{
            **c,
            "page_name": "__empty__#0",
            "page_title": None,
            "page_summary": None,
            "page_action": None,
            "page_sha": None,
            "page_html_url": None,
            "is_page_created": 0,
            "is_page_edited": 0,
            "is_page_deleted": 0,
        }]

    rows = []
    for idx, page in enumerate(pages):
        action = page.get("action", "")
        rows.append({
            **c,
            "page_name": page.get("page_name") or f"__no_page__#{idx}",
            "page_title": page.get("title"),
            "page_summary": page.get("summary"),
            "page_action": action or None,
            "page_sha": page.get("sha"),
            "page_html_url": page.get("html_url"),
            "is_page_created": 1 if action == "created" else 0,
            "is_page_edited": 1 if action == "edited" else 0,
            "is_page_deleted": 1 if action == "deleted" else 0,
        })
    return rows


def _to_release_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """ReleaseEvent → 1 row."""
    c = _common(event)
    payload = event.payload
    release = payload.get("release", {})
    author = release.get("author") or {}
    prerelease = release.get("prerelease")
    return [{
        **c,
        "release_action": payload.get("action"),
        "tag_name": release.get("tag_name"),
        "release_name": release.get("name"),
        "is_prerelease": 1 if prerelease else (0 if prerelease is not None else None),
        "release_html_url": release.get("html_url"),
        "release_author_login": author.get("login"),
    }]


def _to_public_event_rows(event: GitHubEvent) -> list[dict[str, Any]]:
    """PublicEvent → 1 row (공통 필드만)."""
    return [_common(event)]


# ── 변환 함수 디스패치 테이블 ────────────────────────────────

_CONVERTERS: dict[str, Callable[[GitHubEvent], list[dict[str, Any]]]] = {
    "PushEvent": _to_push_event_rows,
    "PullRequestEvent": _to_pull_request_event_rows,
    "IssuesEvent": _to_issues_event_rows,
    "IssueCommentEvent": _to_issue_comment_event_rows,
    "WatchEvent": _to_watch_event_rows,
    "ForkEvent": _to_fork_event_rows,
    "CreateEvent": _to_create_event_rows,
    "DeleteEvent": _to_delete_event_rows,
    "PullRequestReviewEvent": _to_pull_request_review_event_rows,
    "PullRequestReviewCommentEvent": _to_pull_request_review_comment_event_rows,
    "MemberEvent": _to_member_event_rows,
    "GollumEvent": _to_gollum_event_rows,
    "ReleaseEvent": _to_release_event_rows,
    "PublicEvent": _to_public_event_rows,
}


# ── 통계 ─────────────────────────────────────────────────────

@dataclass
class TransformStats:
    """가공 결과 통계."""

    total_input: int = 0
    total_output: int = 0
    skipped: int = 0
    validation_errors: int = 0
    input_type_counts: dict[str, int] = field(default_factory=dict)
    output_table_counts: dict[str, int] = field(default_factory=dict)
    error_details: list[str] = field(default_factory=list)


# ── Row 검증 ─────────────────────────────────────────────────

_TS_KST_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_BASE_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_dl_row(row: dict[str, Any], table_name: str) -> tuple[bool, str | None]:
    """DL Row 공통 필수 필드 검증."""
    if not row.get("event_id"):
        return False, "event_id is empty"
    if not row.get("user_login"):
        return False, "user_login is empty"
    if not row.get("repo_name"):
        return False, "repo_name is empty"
    if not _TS_KST_RE.match(row.get("ts_kst", "")):
        return False, f"ts_kst format invalid: {row.get('ts_kst')}"
    if not _BASE_DATE_RE.match(row.get("base_date", "")):
        return False, f"base_date format invalid: {row.get('base_date')}"
    return True, None


# ── 메인 변환 파이프라인 ─────────────────────────────────────

def transform_events(
    events: list[GitHubEvent],
    source: str = "gharchive",
) -> tuple[DLRowsByTable, TransformStats]:
    """GitHubEvent 리스트를 타입별 DL Row 딕셔너리로 변환한다.

    Returns:
        (DLRowsByTable, TransformStats) 튜플.
        DLRowsByTable = dict[테이블명, list[dict]].
    """
    stats = TransformStats()
    stats.total_input = len(events)
    result: DLRowsByTable = {}

    for event in events:
        stats.input_type_counts[event.type] = stats.input_type_counts.get(event.type, 0) + 1

        table_name = EVENT_TYPE_TO_TABLE.get(event.type)
        if table_name is None:
            stats.skipped += 1
            logger.warning(
                "Unknown event type skipped: %s (event_id=%s)", event.type, event.id
            )
            continue

        try:
            rows = _CONVERTERS[event.type](event)
        except Exception as e:
            stats.validation_errors += 1
            error_msg = f"Transform failed for event {event.id} ({event.type}): {e}"
            stats.error_details.append(error_msg)
            logger.error(error_msg)
            continue

        # 행 단위 검증
        for row in rows:
            is_valid, error = validate_dl_row(row, table_name)
            if not is_valid:
                stats.validation_errors += 1
                error_msg = f"Validation failed for event {row.get('event_id')}: {error}"
                stats.error_details.append(error_msg)
                logger.warning(error_msg)
                continue
            result.setdefault(table_name, []).append(row)

    # source 필드 주입 (Approach C: 후처리)
    for table_rows in result.values():
        for row in table_rows:
            row["source"] = source

    # 출력 통계
    total_output = 0
    for table_name, rows in result.items():
        stats.output_table_counts[table_name] = len(rows)
        total_output += len(rows)
    stats.total_output = total_output

    logger.info(
        "Transform complete: input=%d, output_rows=%d, tables=%d, skipped=%d, errors=%d",
        stats.total_input,
        stats.total_output,
        len(result),
        stats.skipped,
        stats.validation_errors,
    )

    return result, stats


# ── 일별 통계 ────────────────────────────────────────────────

class DailyStatsRow(TypedDict):
    """D1 daily_stats 테이블 행 타입."""

    date: str
    org_name: str
    repo_name: str
    event_type: str
    count: int


def compute_daily_stats(rows_by_table: DLRowsByTable) -> list[DailyStatsRow]:
    """DLRowsByTable에서 일별 통계를 집계한다.

    push/gollum은 커밋/페이지 펼침이므로 event_id 기준 distinct count.
    나머지 테이블도 event_id(PK) 기준으로 deduplicate 하여,
    D1 INSERT OR IGNORE 동작과 일치하는 count를 보장한다.
    """
    counter: dict[tuple[str, str, str, str], int] = {}

    for table_name, rows in rows_by_table.items():
        event_type = TABLE_TO_EVENT_TYPE.get(table_name, table_name)

        seen_event_ids: set[str] = set()
        for row in rows:
            eid = row["event_id"]
            if eid in seen_event_ids:
                continue
            seen_event_ids.add(eid)

            key = (row["base_date"], row["organization"] or "", row["repo_name"], event_type)
            counter[key] = counter.get(key, 0) + 1

    return [
        DailyStatsRow(date=k[0], org_name=k[1], repo_name=k[2], event_type=k[3], count=v)
        for k, v in sorted(counter.items())
    ]
