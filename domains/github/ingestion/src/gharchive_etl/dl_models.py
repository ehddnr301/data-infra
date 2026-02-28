"""DL 테이블 Row TypedDict 정의.

14개 이벤트 타입별 DL 테이블에 대응하는 Row 타입을 정의한다.
모든 Row는 _CommonFields 6개 필드를 공유한다.
"""

from __future__ import annotations

from typing import TypedDict


class _CommonFields(TypedDict):
    """모든 DL 테이블 공통 필드."""

    event_id: str
    repo_name: str
    organization: str | None
    user_login: str
    ts_kst: str
    base_date: str
    source: str  # 'gharchive' | 'rest_api'


# 1) dl_push_events — PushEvent (커밋 단위 펼침)
class PushEventRow(_CommonFields):
    ref_full: str | None
    ref_name: str | None
    is_branch_ref: int
    is_tag_ref: int
    head_sha: str | None
    before_sha: str | None
    commit_sha: str  # NOT NULL (sentinel 사용)
    commit_author_name: str | None
    commit_author_email: str | None
    commit_message: str | None
    commit_distinct: int | None
    commit_url: str | None


# 2) dl_pull_request_events — PullRequestEvent
class PullRequestEventRow(_CommonFields):
    pr_action: str | None
    pr_number: int | None
    pr_title: str | None
    pr_html_url: str | None
    pr_state: str | None
    is_draft: int | None
    pr_body: str | None
    pr_author_login: str | None
    pr_author_id: int | None
    head_ref: str | None
    base_ref: str | None
    head_sha: str | None
    base_sha: str | None
    commits_count: int | None
    additions: int | None
    deletions: int | None
    changed_files: int | None
    issue_comments_count: int | None
    review_comments_count: int | None
    is_merged: int | None
    merge_commit_sha: str | None


# 3) dl_issues_events — IssuesEvent
class IssuesEventRow(_CommonFields):
    issue_action: str | None
    issue_number: int | None
    issue_title: str | None
    issue_body: str | None
    issue_state: str | None
    issue_html_url: str | None
    issue_author_login: str | None
    issue_author_id: int | None


# 4) dl_issue_comment_events — IssueCommentEvent
class IssueCommentEventRow(_CommonFields):
    ic_action: str | None
    issue_number: int | None
    issue_title: str | None
    issue_state: str | None
    issue_html_url: str | None
    issue_author_login: str | None
    issue_author_id: int | None
    comment_id: int | None
    comment_html_url: str | None
    comment_body: str | None
    commenter_login: str | None
    commenter_id: int | None


# 5) dl_watch_events — WatchEvent (공통 필드만)
class WatchEventRow(_CommonFields):
    pass


# 6) dl_fork_events — ForkEvent
class ForkEventRow(_CommonFields):
    forkee_id: int | None
    forkee_full_name: str | None
    forkee_html_url: str | None
    forkee_owner_login: str | None
    forkee_owner_id: int | None
    forkee_description: str | None
    is_fork_private: int | None
    forkee_default_branch: str | None


# 7) dl_create_events — CreateEvent
class CreateEventRow(_CommonFields):
    created_ref_type: str | None
    created_ref_name: str | None
    default_branch: str | None
    repo_description: str | None
    pusher_type: str | None
    is_repo_creation: int
    is_branch_creation: int
    is_tag_creation: int


# 8) dl_delete_events — DeleteEvent
class DeleteEventRow(_CommonFields):
    deleted_ref_type: str | None
    deleted_ref_name: str | None
    pusher_type: str | None
    is_branch_deletion: int
    is_tag_deletion: int


# 9) dl_pull_request_review_events — PullRequestReviewEvent
class PullRequestReviewEventRow(_CommonFields):
    reviewer_login: str | None
    reviewer_id: int | None
    review_state: str | None
    review_body: str | None
    review_html_url: str | None
    commit_sha: str | None
    review_submitted_at_utc: str | None
    review_submitted_at_kst: str | None
    pr_number: int | None
    pr_title: str | None
    pr_html_url: str | None
    pr_author_login: str | None


# 10) dl_pull_request_review_comment_events — PullRequestReviewCommentEvent
class PullRequestReviewCommentEventRow(_CommonFields):
    pr_review_comment_action: str | None
    review_comment_id: int | None
    review_comment_html_url: str | None
    review_comment_body: str | None
    diff_hunk: str | None
    file_path: str | None
    commit_id: str | None
    review_id: int | None
    commenter_login: str | None
    commenter_id: int | None
    pr_number: int | None
    pr_title: str | None
    pr_html_url: str | None
    pr_state: str | None


# 11) dl_member_events — MemberEvent
class MemberEventRow(_CommonFields):
    member_login: str | None
    member_id: int | None
    member_html_url: str | None
    member_action: str | None
    is_member_added: int
    is_member_removed: int


# 12) dl_gollum_events — GollumEvent (페이지 단위 펼침)
class GollumEventRow(_CommonFields):
    page_name: str  # NOT NULL (sentinel 사용)
    page_title: str | None
    page_summary: str | None
    page_action: str | None
    page_sha: str | None
    page_html_url: str | None
    is_page_created: int
    is_page_edited: int
    is_page_deleted: int


# 13) dl_release_events — ReleaseEvent
class ReleaseEventRow(_CommonFields):
    release_action: str | None
    tag_name: str | None
    release_name: str | None
    is_prerelease: int | None
    release_html_url: str | None
    release_author_login: str | None


# 14) dl_public_events — PublicEvent (공통 필드만)
class PublicEventRow(_CommonFields):
    pass


# ── 테이블명 ↔ 이벤트 타입 매핑 ──────────────────────────────

EVENT_TYPE_TO_TABLE: dict[str, str] = {
    "PushEvent": "dl_push_events",
    "PullRequestEvent": "dl_pull_request_events",
    "IssuesEvent": "dl_issues_events",
    "IssueCommentEvent": "dl_issue_comment_events",
    "WatchEvent": "dl_watch_events",
    "ForkEvent": "dl_fork_events",
    "CreateEvent": "dl_create_events",
    "DeleteEvent": "dl_delete_events",
    "PullRequestReviewEvent": "dl_pull_request_review_events",
    "PullRequestReviewCommentEvent": "dl_pull_request_review_comment_events",
    "MemberEvent": "dl_member_events",
    "GollumEvent": "dl_gollum_events",
    "ReleaseEvent": "dl_release_events",
    "PublicEvent": "dl_public_events",
}

TABLE_TO_EVENT_TYPE: dict[str, str] = {v: k for k, v in EVENT_TYPE_TO_TABLE.items()}

DL_TABLES: list[str] = sorted(EVENT_TYPE_TO_TABLE.values())

# ── 테이블별 컬럼 정의 (D1 insert 순서) ──────────────────────

DL_TABLE_COLUMNS: dict[str, list[str]] = {
    "dl_push_events": [
        "event_id", "repo_name", "organization", "user_login",
        "ref_full", "ref_name", "is_branch_ref", "is_tag_ref",
        "head_sha", "before_sha",
        "commit_sha", "commit_author_name", "commit_author_email",
        "commit_message", "commit_distinct", "commit_url",
        "ts_kst", "base_date", "source",
    ],
    "dl_pull_request_events": [
        "event_id", "repo_name", "organization", "user_login",
        "pr_action", "pr_number", "pr_title", "pr_html_url",
        "pr_state", "is_draft", "pr_body",
        "pr_author_login", "pr_author_id",
        "head_ref", "base_ref", "head_sha", "base_sha",
        "commits_count", "additions", "deletions", "changed_files",
        "issue_comments_count", "review_comments_count",
        "is_merged", "merge_commit_sha",
        "ts_kst", "base_date", "source",
    ],
    "dl_issues_events": [
        "event_id", "repo_name", "organization", "user_login",
        "issue_action", "issue_number", "issue_title", "issue_body",
        "issue_state", "issue_html_url",
        "issue_author_login", "issue_author_id",
        "ts_kst", "base_date", "source",
    ],
    "dl_issue_comment_events": [
        "event_id", "repo_name", "organization", "user_login",
        "ic_action", "issue_number", "issue_title", "issue_state",
        "issue_html_url", "issue_author_login", "issue_author_id",
        "comment_id", "comment_html_url", "comment_body",
        "commenter_login", "commenter_id",
        "ts_kst", "base_date", "source",
    ],
    "dl_watch_events": [
        "event_id", "repo_name", "organization", "user_login",
        "ts_kst", "base_date", "source",
    ],
    "dl_fork_events": [
        "event_id", "repo_name", "organization", "user_login",
        "forkee_id", "forkee_full_name", "forkee_html_url",
        "forkee_owner_login", "forkee_owner_id",
        "forkee_description", "is_fork_private", "forkee_default_branch",
        "ts_kst", "base_date", "source",
    ],
    "dl_create_events": [
        "event_id", "repo_name", "organization", "user_login",
        "created_ref_type", "created_ref_name",
        "default_branch", "repo_description", "pusher_type",
        "is_repo_creation", "is_branch_creation", "is_tag_creation",
        "ts_kst", "base_date", "source",
    ],
    "dl_delete_events": [
        "event_id", "repo_name", "organization", "user_login",
        "deleted_ref_type", "deleted_ref_name", "pusher_type",
        "is_branch_deletion", "is_tag_deletion",
        "ts_kst", "base_date", "source",
    ],
    "dl_pull_request_review_events": [
        "event_id", "repo_name", "organization", "user_login",
        "reviewer_login", "reviewer_id",
        "review_state", "review_body", "review_html_url",
        "commit_sha", "review_submitted_at_utc", "review_submitted_at_kst",
        "pr_number", "pr_title", "pr_html_url", "pr_author_login",
        "ts_kst", "base_date", "source",
    ],
    "dl_pull_request_review_comment_events": [
        "event_id", "repo_name", "organization", "user_login",
        "pr_review_comment_action",
        "review_comment_id", "review_comment_html_url", "review_comment_body",
        "diff_hunk", "file_path", "commit_id", "review_id",
        "commenter_login", "commenter_id",
        "pr_number", "pr_title", "pr_html_url", "pr_state",
        "ts_kst", "base_date", "source",
    ],
    "dl_member_events": [
        "event_id", "repo_name", "organization", "user_login",
        "member_login", "member_id", "member_html_url", "member_action",
        "is_member_added", "is_member_removed",
        "ts_kst", "base_date", "source",
    ],
    "dl_gollum_events": [
        "event_id", "repo_name", "organization", "user_login",
        "page_name", "page_title", "page_summary", "page_action",
        "page_sha", "page_html_url",
        "is_page_created", "is_page_edited", "is_page_deleted",
        "ts_kst", "base_date", "source",
    ],
    "dl_release_events": [
        "event_id", "repo_name", "organization", "user_login",
        "release_action", "tag_name", "release_name",
        "is_prerelease", "release_html_url", "release_author_login",
        "ts_kst", "base_date", "source",
    ],
    "dl_public_events": [
        "event_id", "repo_name", "organization", "user_login",
        "ts_kst", "base_date", "source",
    ],
}

# 배열 펼침 테이블 (daily_stats에서 distinct event_id count 필요)
EXPLODED_TABLES: frozenset[str] = frozenset({"dl_push_events", "dl_gollum_events"})
