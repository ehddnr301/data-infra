"""DL 테이블 변환 로직 테스트."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from gharchive_etl.dl_models import DL_TABLE_COLUMNS, EVENT_TYPE_TO_TABLE, EXPLODED_TABLES
from gharchive_etl.models import GitHubEvent
from gharchive_etl.transformer import (
    DLRowsByTable,
    _to_kst,
    compute_daily_stats,
    transform_events,
    validate_dl_row,
)


def _make_event(
    event_id: str = "1",
    event_type: str = "PushEvent",
    org_login: str | None = "pseudolab",
    repo_name: str = "pseudolab/test-repo",
    payload: dict[str, Any] | None = None,
    created_at: str = "2024-01-15T10:30:00Z",
) -> GitHubEvent:
    """테스트용 이벤트 헬퍼."""
    data: dict[str, Any] = {
        "id": event_id,
        "type": event_type,
        "actor": {"id": 1, "login": "testuser"},
        "repo": {"id": 100, "name": repo_name},
        "payload": payload or {},
        "created_at": created_at,
    }
    if org_login is not None:
        data["org"] = {"id": 200, "login": org_login}
    return GitHubEvent.model_validate(data)


# ── KST 변환 테스트 ──────────────────────────────────────

class TestKstConversion:
    """UTC → KST 변환 테스트."""

    def test_utc_to_kst_basic(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        ts_kst, base_date = _to_kst(dt)
        assert ts_kst.startswith("2024-01-15T19:30:00")
        assert base_date == "2024-01-15"

    def test_utc_to_kst_date_boundary(self) -> None:
        """UTC 15:30 → KST 다음날 00:30."""
        dt = datetime(2024, 1, 15, 15, 30, 0, tzinfo=timezone.utc)
        ts_kst, base_date = _to_kst(dt)
        assert ts_kst.startswith("2024-01-16T00:30:00")
        assert base_date == "2024-01-16"

    def test_utc_to_kst_midnight(self) -> None:
        """UTC 15:00 → KST 00:00."""
        dt = datetime(2024, 1, 15, 15, 0, 0, tzinfo=timezone.utc)
        ts_kst, base_date = _to_kst(dt)
        assert ts_kst.startswith("2024-01-16T00:00:00")
        assert base_date == "2024-01-16"

    def test_naive_datetime_treated_as_utc(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 0)  # naive
        ts_kst, base_date = _to_kst(dt)
        assert ts_kst.startswith("2024-01-15T19:30:00")
        assert base_date == "2024-01-15"


# ── PushEvent 변환 테스트 ────────────────────────────────

class TestPushEventConversion:
    """PushEvent → dl_push_events 변환 테스트."""

    def test_single_commit(self) -> None:
        event = _make_event(payload={
            "ref": "refs/heads/main",
            "head": "abc123",
            "before": "def456",
            "commits": [
                {"sha": "abc123", "message": "Init", "author": {"name": "u", "email": "u@e"}, "distinct": True, "url": "http://x"},
            ],
        })
        result, _ = transform_events([event])
        rows = result["dl_push_events"]
        assert len(rows) == 1
        assert rows[0]["commit_sha"] == "abc123"
        assert rows[0]["ref_name"] == "main"
        assert rows[0]["is_branch_ref"] == 1
        assert rows[0]["is_tag_ref"] == 0

    def test_multiple_commits(self) -> None:
        event = _make_event(payload={
            "ref": "refs/heads/dev",
            "commits": [
                {"sha": "a1", "message": "m1", "author": {"name": "u"}, "distinct": True},
                {"sha": "a2", "message": "m2", "author": {"name": "u"}, "distinct": False},
                {"sha": "a3", "message": "m3", "author": {"name": "u"}, "distinct": True},
            ],
        })
        result, _ = transform_events([event])
        rows = result["dl_push_events"]
        assert len(rows) == 3
        assert all(r["event_id"] == "1" for r in rows)
        assert rows[1]["commit_distinct"] == 0

    def test_empty_commits_header_row(self) -> None:
        event = _make_event(payload={
            "ref": "refs/heads/main",
            "commits": [],
        })
        result, _ = transform_events([event])
        rows = result["dl_push_events"]
        assert len(rows) == 1
        assert rows[0]["commit_sha"] == "__empty__#0"
        assert rows[0]["commit_author_name"] is None

    def test_commit_message_truncation(self) -> None:
        event = _make_event(payload={
            "commits": [{"sha": "a1", "message": "x" * 300}],
        })
        result, _ = transform_events([event])
        rows = result["dl_push_events"]
        assert len(rows[0]["commit_message"]) == 200

    def test_tag_ref_detection(self) -> None:
        event = _make_event(payload={
            "ref": "refs/tags/v1.0",
            "commits": [{"sha": "a1"}],
        })
        result, _ = transform_events([event])
        row = result["dl_push_events"][0]
        assert row["is_tag_ref"] == 1
        assert row["is_branch_ref"] == 0
        assert row["ref_name"] == "v1.0"

    def test_null_sha_sentinel_index(self) -> None:
        event = _make_event(payload={
            "commits": [
                {"sha": None, "message": "m1"},
                {"sha": None, "message": "m2"},
            ],
        })
        result, _ = transform_events([event])
        rows = result["dl_push_events"]
        assert rows[0]["commit_sha"] == "__no_commit__#0"
        assert rows[1]["commit_sha"] == "__no_commit__#1"


# ── PullRequestEvent 변환 테스트 ─────────────────────────

class TestPullRequestEventConversion:
    """PullRequestEvent → dl_pull_request_events 변환 테스트."""

    def test_full_pr_fields(self) -> None:
        event = _make_event(event_type="PullRequestEvent", payload={
            "action": "opened",
            "number": 42,
            "pull_request": {
                "title": "Fix bug",
                "html_url": "https://github.com/org/repo/pull/42",
                "state": "open",
                "draft": False,
                "body": "Description here",
                "user": {"login": "author", "id": 10},
                "head": {"ref": "feature", "sha": "h1"},
                "base": {"ref": "main", "sha": "b1"},
                "commits": 3,
                "additions": 10,
                "deletions": 5,
                "changed_files": 2,
                "comments": 1,
                "review_comments": 0,
                "merged": False,
                "merge_commit_sha": None,
            },
        })
        result, _ = transform_events([event])
        rows = result["dl_pull_request_events"]
        assert len(rows) == 1
        row = rows[0]
        assert row["pr_action"] == "opened"
        assert row["pr_number"] == 42
        assert row["pr_title"] == "Fix bug"
        assert row["is_draft"] == 0
        assert row["pr_author_login"] == "author"
        assert row["commits_count"] == 3
        assert row["is_merged"] == 0

    def test_missing_optional_fields(self) -> None:
        event = _make_event(event_type="PullRequestEvent", payload={
            "action": "closed",
        })
        result, _ = transform_events([event])
        row = result["dl_pull_request_events"][0]
        assert row["pr_title"] is None
        assert row["pr_number"] is None
        assert row["is_draft"] is None


# ── GollumEvent 변환 테스트 ──────────────────────────────

class TestGollumEventConversion:
    """GollumEvent → dl_gollum_events 변환 테스트."""

    def test_multiple_pages(self) -> None:
        event = _make_event(event_type="GollumEvent", payload={
            "pages": [
                {"page_name": "Home", "title": "Home", "action": "created", "sha": "s1", "html_url": "u1"},
                {"page_name": "API", "title": "API", "action": "edited", "sha": "s2", "html_url": "u2"},
            ],
        })
        result, _ = transform_events([event])
        rows = result["dl_gollum_events"]
        assert len(rows) == 2
        assert rows[0]["is_page_created"] == 1
        assert rows[1]["is_page_edited"] == 1

    def test_empty_pages_header_row(self) -> None:
        event = _make_event(event_type="GollumEvent", payload={"pages": []})
        result, _ = transform_events([event])
        rows = result["dl_gollum_events"]
        assert len(rows) == 1
        assert rows[0]["page_name"] == "__empty__#0"

    def test_null_page_name_sentinel(self) -> None:
        event = _make_event(event_type="GollumEvent", payload={
            "pages": [
                {"page_name": None, "action": "created"},
                {"page_name": None, "action": "edited"},
            ],
        })
        result, _ = transform_events([event])
        rows = result["dl_gollum_events"]
        assert rows[0]["page_name"] == "__no_page__#0"
        assert rows[1]["page_name"] == "__no_page__#1"


# ── 기타 이벤트 타입 변환 테스트 ─────────────────────────

class TestOtherEventConversions:
    """나머지 이벤트 타입 변환 테스트."""

    def test_watch_event(self) -> None:
        event = _make_event(event_type="WatchEvent")
        result, _ = transform_events([event])
        rows = result["dl_watch_events"]
        assert len(rows) == 1
        assert rows[0]["event_id"] == "1"

    def test_fork_event(self) -> None:
        event = _make_event(event_type="ForkEvent", payload={
            "forkee": {
                "id": 999,
                "full_name": "user/fork",
                "html_url": "https://github.com/user/fork",
                "owner": {"login": "user", "id": 5},
                "description": "A fork",
                "private": False,
                "default_branch": "main",
            },
        })
        result, _ = transform_events([event])
        row = result["dl_fork_events"][0]
        assert row["forkee_full_name"] == "user/fork"
        assert row["is_fork_private"] == 0
        assert row["forkee_owner_login"] == "user"

    def test_create_event_branch(self) -> None:
        event = _make_event(event_type="CreateEvent", payload={
            "ref": "feature-branch",
            "ref_type": "branch",
            "master_branch": "main",
        })
        result, _ = transform_events([event])
        row = result["dl_create_events"][0]
        assert row["is_branch_creation"] == 1
        assert row["is_repo_creation"] == 0
        assert row["is_tag_creation"] == 0

    def test_delete_event_tag(self) -> None:
        event = _make_event(event_type="DeleteEvent", payload={
            "ref": "v1.0",
            "ref_type": "tag",
        })
        result, _ = transform_events([event])
        row = result["dl_delete_events"][0]
        assert row["is_tag_deletion"] == 1
        assert row["is_branch_deletion"] == 0

    def test_release_event(self) -> None:
        event = _make_event(event_type="ReleaseEvent", payload={
            "action": "published",
            "release": {
                "tag_name": "v1.0",
                "name": "Release 1.0",
                "prerelease": False,
                "html_url": "https://github.com/org/repo/releases/v1.0",
                "author": {"login": "releaser"},
            },
        })
        result, _ = transform_events([event])
        row = result["dl_release_events"][0]
        assert row["release_action"] == "published"
        assert row["tag_name"] == "v1.0"
        assert row["is_prerelease"] == 0
        assert row["release_author_login"] == "releaser"

    def test_member_event(self) -> None:
        event = _make_event(event_type="MemberEvent", payload={
            "action": "added",
            "member": {"login": "newuser", "id": 50, "html_url": "https://github.com/newuser"},
        })
        result, _ = transform_events([event])
        row = result["dl_member_events"][0]
        assert row["is_member_added"] == 1
        assert row["is_member_removed"] == 0
        assert row["member_login"] == "newuser"

    def test_public_event(self) -> None:
        event = _make_event(event_type="PublicEvent")
        result, _ = transform_events([event])
        rows = result["dl_public_events"]
        assert len(rows) == 1
        assert rows[0]["event_id"] == "1"

    def test_issue_comment_event(self) -> None:
        event = _make_event(event_type="IssueCommentEvent", payload={
            "action": "created",
            "issue": {
                "number": 10,
                "title": "Bug",
                "state": "open",
                "html_url": "https://github.com/org/repo/issues/10",
                "user": {"login": "issuer", "id": 20},
            },
            "comment": {
                "id": 555,
                "html_url": "https://github.com/org/repo/issues/10#comment-555",
                "body": "Comment text",
                "user": {"login": "commenter", "id": 30},
            },
        })
        result, _ = transform_events([event])
        row = result["dl_issue_comment_events"][0]
        assert row["ic_action"] == "created"
        assert row["comment_id"] == 555
        assert row["commenter_login"] == "commenter"

    def test_issues_event(self) -> None:
        event = _make_event(event_type="IssuesEvent", payload={
            "action": "opened",
            "issue": {
                "number": 10,
                "title": "Bug report",
                "body": "Details",
                "state": "open",
                "html_url": "https://github.com/org/repo/issues/10",
                "user": {"login": "reporter", "id": 15},
            },
        })
        result, _ = transform_events([event])
        row = result["dl_issues_events"][0]
        assert row["issue_action"] == "opened"
        assert row["issue_title"] == "Bug report"
        assert row["issue_author_login"] == "reporter"

    def test_pr_review_event(self) -> None:
        event = _make_event(event_type="PullRequestReviewEvent", payload={
            "action": "submitted",
            "review": {
                "state": "approved",
                "user": {"login": "reviewer", "id": 77},
                "body": "LGTM",
                "html_url": "https://github.com/org/repo/pull/1#review-1",
                "commit_id": "abc",
                "submitted_at": "2024-01-15T10:00:00Z",
            },
            "pull_request": {
                "number": 1,
                "title": "PR Title",
                "html_url": "https://github.com/org/repo/pull/1",
                "user": {"login": "author"},
            },
        })
        result, _ = transform_events([event])
        row = result["dl_pull_request_review_events"][0]
        assert row["review_state"] == "approved"
        assert row["reviewer_login"] == "reviewer"
        assert row["pr_number"] == 1
        assert row["review_submitted_at_utc"] == "2024-01-15T10:00:00Z"
        assert row["review_submitted_at_kst"] is not None

    def test_pr_review_comment_event(self) -> None:
        event = _make_event(event_type="PullRequestReviewCommentEvent", payload={
            "action": "created",
            "comment": {
                "id": 100,
                "html_url": "https://github.com/org/repo/pull/1#comment-100",
                "body": "Fix this",
                "diff_hunk": "@@ -1,3 +1,3 @@",
                "path": "src/main.py",
                "commit_id": "abc",
                "pull_request_review_id": 200,
                "user": {"login": "reviewer", "id": 77},
            },
            "pull_request": {
                "number": 1,
                "title": "PR",
                "html_url": "https://github.com/org/repo/pull/1",
                "state": "open",
            },
        })
        result, _ = transform_events([event])
        row = result["dl_pull_request_review_comment_events"][0]
        assert row["pr_review_comment_action"] == "created"
        assert row["review_comment_id"] == 100
        assert row["file_path"] == "src/main.py"


# ── transform_events 통합 테스트 ─────────────────────────

class TestTransformEvents:
    """전체 변환 파이프라인 테스트."""

    def test_returns_dict_by_table(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent", payload={"commits": [{"sha": "a"}]}),
            _make_event(event_id="2", event_type="IssuesEvent", payload={"action": "opened", "issue": {}}),
        ]
        result, stats = transform_events(events)
        assert isinstance(result, dict)
        assert "dl_push_events" in result
        assert "dl_issues_events" in result
        assert stats.total_input == 2

    def test_mixed_event_types(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent", payload={"commits": [{"sha": "a"}]}),
            _make_event(event_id="2", event_type="WatchEvent"),
            _make_event(event_id="3", event_type="ForkEvent", payload={"forkee": {}}),
        ]
        result, stats = transform_events(events)
        assert len(result) == 3
        assert stats.total_output == 3

    def test_unknown_event_type_skipped(self) -> None:
        events = [
            _make_event(event_id="1", event_type="SomeNewEvent"),
            _make_event(event_id="2", event_type="PushEvent", payload={"commits": [{"sha": "a"}]}),
        ]
        result, stats = transform_events(events)
        assert "dl_push_events" in result
        assert stats.skipped == 1
        assert stats.total_output == 1

    def test_stats_accuracy(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent", payload={
                "commits": [{"sha": "a1"}, {"sha": "a2"}],
            }),
            _make_event(event_id="2", event_type="WatchEvent"),
        ]
        result, stats = transform_events(events)
        assert stats.total_input == 2
        # 2 push rows + 1 watch row = 3 total output rows
        assert stats.total_output == 3
        assert stats.output_table_counts["dl_push_events"] == 2
        assert stats.output_table_counts["dl_watch_events"] == 1


# ── validate_dl_row 테스트 ───────────────────────────────

class TestValidateDlRow:
    """DL Row 검증 테스트."""

    def test_valid_row(self) -> None:
        row = {
            "event_id": "1",
            "user_login": "user",
            "repo_name": "org/repo",
            "ts_kst": "2024-01-15T19:30:00+09:00",
            "base_date": "2024-01-15",
        }
        is_valid, error = validate_dl_row(row, "dl_watch_events")
        assert is_valid is True
        assert error is None

    def test_empty_event_id(self) -> None:
        row = {
            "event_id": "",
            "user_login": "user",
            "repo_name": "org/repo",
            "ts_kst": "2024-01-15T19:30:00+09:00",
            "base_date": "2024-01-15",
        }
        is_valid, error = validate_dl_row(row, "dl_watch_events")
        assert is_valid is False
        assert "event_id" in error  # type: ignore[operator]

    def test_invalid_ts_kst_format(self) -> None:
        row = {
            "event_id": "1",
            "user_login": "user",
            "repo_name": "org/repo",
            "ts_kst": "not-a-date",
            "base_date": "2024-01-15",
        }
        is_valid, error = validate_dl_row(row, "dl_watch_events")
        assert is_valid is False
        assert "ts_kst" in error  # type: ignore[operator]


# ── compute_daily_stats 테스트 ───────────────────────────

class TestComputeDailyStats:
    """DLRowsByTable 기반 일별 통계 테스트."""

    def test_basic_count(self) -> None:
        rows_by_table: DLRowsByTable = {
            "dl_watch_events": [
                {"event_id": "1", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo"},
                {"event_id": "2", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo"},
            ],
        }
        stats = compute_daily_stats(rows_by_table)
        assert len(stats) == 1
        assert stats[0]["event_type"] == "WatchEvent"
        assert stats[0]["count"] == 2

    def test_non_exploded_table_deduplicates_event_id(self) -> None:
        """비-펼침 테이블도 event_id(PK) 기준 deduplicate."""
        rows_by_table: DLRowsByTable = {
            "dl_watch_events": [
                {"event_id": "1", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo"},
                {"event_id": "1", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo"},
            ],
        }
        stats = compute_daily_stats(rows_by_table)
        assert len(stats) == 1
        assert stats[0]["event_type"] == "WatchEvent"
        assert stats[0]["count"] == 1

    def test_push_events_count_by_event_id(self) -> None:
        """커밋 펼침 시 event_id 기준 count."""
        rows_by_table: DLRowsByTable = {
            "dl_push_events": [
                {"event_id": "1", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo", "commit_sha": "a1"},
                {"event_id": "1", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo", "commit_sha": "a2"},
                {"event_id": "2", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo", "commit_sha": "b1"},
            ],
        }
        stats = compute_daily_stats(rows_by_table)
        assert len(stats) == 1
        assert stats[0]["event_type"] == "PushEvent"
        assert stats[0]["count"] == 2  # 2 distinct event_ids, not 3 rows

    def test_gollum_events_count_by_event_id(self) -> None:
        """페이지 펼침 시 event_id 기준 count."""
        rows_by_table: DLRowsByTable = {
            "dl_gollum_events": [
                {"event_id": "1", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo"},
                {"event_id": "1", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo"},
            ],
        }
        stats = compute_daily_stats(rows_by_table)
        assert len(stats) == 1
        assert stats[0]["count"] == 1  # 1 distinct event_id

    def test_null_org(self) -> None:
        rows_by_table: DLRowsByTable = {
            "dl_watch_events": [
                {"event_id": "1", "base_date": "2024-01-15", "organization": None, "repo_name": "user/repo"},
            ],
        }
        stats = compute_daily_stats(rows_by_table)
        assert stats[0]["org_name"] == ""

    def test_empty_input(self) -> None:
        stats = compute_daily_stats({})
        assert stats == []

    def test_multiple_tables(self) -> None:
        rows_by_table: DLRowsByTable = {
            "dl_watch_events": [
                {"event_id": "1", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo"},
            ],
            "dl_issues_events": [
                {"event_id": "2", "base_date": "2024-01-15", "organization": "org", "repo_name": "org/repo"},
            ],
        }
        stats = compute_daily_stats(rows_by_table)
        assert len(stats) == 2
        types = {s["event_type"] for s in stats}
        assert types == {"WatchEvent", "IssuesEvent"}


# ── source 필드 테스트 ──────────────────────────────────

class TestSourceField:
    """source 필드 주입 테스트."""

    def test_default_source_gharchive(self) -> None:
        """기본값 source='gharchive' 확인."""
        event = _make_event(event_type="WatchEvent")
        result, _ = transform_events([event])
        row = result["dl_watch_events"][0]
        assert row["source"] == "gharchive"

    def test_source_rest_api(self) -> None:
        """source='rest_api' 명시 전달 확인."""
        event = _make_event(event_type="WatchEvent")
        result, _ = transform_events([event], source="rest_api")
        row = result["dl_watch_events"][0]
        assert row["source"] == "rest_api"

    def test_source_in_all_dl_table_columns(self) -> None:
        """모든 DL_TABLE_COLUMNS에 'source' 컬럼 포함 확인."""
        for table_name, columns in DL_TABLE_COLUMNS.items():
            assert "source" in columns, f"'{table_name}' is missing 'source' column"

    def test_source_injected_in_all_tables(self) -> None:
        """여러 이벤트 타입 변환 시 모든 테이블의 행에 source 주입 확인."""
        events = [
            _make_event(event_id="1", event_type="PushEvent", payload={"commits": [{"sha": "a"}]}),
            _make_event(event_id="2", event_type="IssuesEvent", payload={"action": "opened", "issue": {}}),
            _make_event(event_id="3", event_type="WatchEvent"),
        ]
        result, _ = transform_events(events, source="rest_api")
        for table_name, rows in result.items():
            for row in rows:
                assert row.get("source") == "rest_api", (
                    f"Row in '{table_name}' missing source='rest_api'"
                )
