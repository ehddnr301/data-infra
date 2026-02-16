"""이벤트 가공 로직 테스트."""

from __future__ import annotations

import json
from typing import Any

from gharchive_etl.models import GitHubEvent
from gharchive_etl.transformer import (
    EventRow,
    compute_daily_stats,
    deduplicate,
    normalize_payload,
    to_event_row,
    transform_events,
    validate_row,
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


def _make_row(**overrides: Any) -> EventRow:
    """테스트용 EventRow 헬퍼."""
    defaults: dict[str, Any] = {
        "id": "1",
        "type": "PushEvent",
        "actor_login": "testuser",
        "repo_name": "pseudolab/test-repo",
        "org_name": "pseudolab",
        "payload": "{}",
        "created_at": "2024-01-15T10:30:00",
        "batch_date": "2024-01-15",
    }
    defaults.update(overrides)
    return defaults  # type: ignore[return-value]


class TestNormalizePayload:
    """payload 정규화 로직 테스트."""

    def test_push_event(self) -> None:
        payload = {
            "size": 2,
            "distinct_size": 1,
            "ref": "refs/heads/main",
            "commits": [
                {"sha": "abc123", "message": "Initial commit"},
                {"sha": "def456", "message": "Update README"},
            ],
        }
        result = normalize_payload("PushEvent", payload)
        assert result["size"] == 2
        assert result["distinct_size"] == 1
        assert result["ref"] == "refs/heads/main"
        assert len(result["commits"]) == 2
        assert result["commits"][0]["sha"] == "abc123"
        assert result["commits"][0]["message"] == "Initial commit"

    def test_push_event_long_message_truncated(self) -> None:
        payload = {
            "commits": [{"sha": "abc123", "message": "a" * 300}],
        }
        result = normalize_payload("PushEvent", payload)
        assert len(result["commits"][0]["message"]) == 200

    def test_pull_request_event(self) -> None:
        payload = {
            "action": "opened",
            "number": 42,
            "pull_request": {
                "title": "Fix bug",
                "state": "open",
                "merged": False,
                "additions": 10,
                "deletions": 5,
                "changed_files": 3,
            },
        }
        result = normalize_payload("PullRequestEvent", payload)
        assert result["action"] == "opened"
        assert result["number"] == 42
        assert result["title"] == "Fix bug"
        assert result["state"] == "open"
        assert result["merged"] is False
        assert result["additions"] == 10
        assert result["deletions"] == 5
        assert result["changed_files"] == 3

    def test_issues_event(self) -> None:
        payload = {
            "action": "opened",
            "issue": {
                "number": 10,
                "title": "Bug report",
                "state": "open",
                "labels": [{"name": "bug"}, {"name": "help wanted"}],
            },
        }
        result = normalize_payload("IssuesEvent", payload)
        assert result["action"] == "opened"
        assert result["number"] == 10
        assert result["title"] == "Bug report"
        assert result["state"] == "open"
        assert result["labels"] == ["bug", "help wanted"]

    def test_issue_comment_event(self) -> None:
        payload = {
            "action": "created",
            "issue": {"number": 10},
            "comment": {"id": 555},
        }
        result = normalize_payload("IssueCommentEvent", payload)
        assert result["action"] == "created"
        assert result["issue_number"] == 10
        assert result["comment_id"] == 555

    def test_watch_event(self) -> None:
        payload = {"action": "started"}
        result = normalize_payload("WatchEvent", payload)
        assert result == {"action": "started"}

    def test_fork_event(self) -> None:
        payload = {"forkee": {"full_name": "user/forked-repo"}}
        result = normalize_payload("ForkEvent", payload)
        assert result["forkee_full_name"] == "user/forked-repo"

    def test_create_event(self) -> None:
        payload = {
            "ref": "main",
            "ref_type": "branch",
            "master_branch": "main",
        }
        result = normalize_payload("CreateEvent", payload)
        assert result["ref"] == "main"
        assert result["ref_type"] == "branch"
        assert result["master_branch"] == "main"

    def test_delete_event(self) -> None:
        payload = {
            "ref": "feature-branch",
            "ref_type": "branch",
        }
        result = normalize_payload("DeleteEvent", payload)
        assert result["ref"] == "feature-branch"
        assert result["ref_type"] == "branch"

    def test_release_event(self) -> None:
        payload = {
            "action": "published",
            "release": {
                "tag_name": "v1.0",
                "name": "Release 1.0",
                "prerelease": False,
            },
        }
        result = normalize_payload("ReleaseEvent", payload)
        assert result["action"] == "published"
        assert result["tag_name"] == "v1.0"
        assert result["name"] == "Release 1.0"
        assert result["prerelease"] is False

    def test_review_event(self) -> None:
        payload = {
            "action": "submitted",
            "review": {"state": "approved"},
            "pull_request": {"number": 42},
        }
        result = normalize_payload("PullRequestReviewEvent", payload)
        assert result["action"] == "submitted"
        assert result["review_state"] == "approved"
        assert result["pull_request_number"] == 42

    def test_review_comment_event(self) -> None:
        payload = {
            "action": "created",
            "comment": {"id": 789},
            "pull_request": {"number": 42},
        }
        result = normalize_payload("PullRequestReviewCommentEvent", payload)
        assert result["action"] == "created"
        assert result["comment_id"] == 789
        assert result["pull_request_number"] == 42

    def test_member_event(self) -> None:
        payload = {
            "action": "added",
            "member": {"login": "newuser"},
        }
        result = normalize_payload("MemberEvent", payload)
        assert result["action"] == "added"
        assert result["member_login"] == "newuser"

    def test_public_event(self) -> None:
        payload = {}
        result = normalize_payload("PublicEvent", payload)
        assert result == {}

    def test_gollum_event(self) -> None:
        payload = {
            "pages": [
                {"action": "created", "title": "Home"},
                {"action": "edited", "title": "API"},
            ],
        }
        result = normalize_payload("GollumEvent", payload)
        assert len(result["pages"]) == 2
        assert result["pages"][0]["action"] == "created"
        assert result["pages"][0]["title"] == "Home"
        assert result["pages"][1]["action"] == "edited"
        assert result["pages"][1]["title"] == "API"

    def test_unknown_type_fallback(self) -> None:
        payload = {
            "long_string": "x" * 300,
            "number": 42,
            "nested_dict": {"key": "value"},
            "list_items": [1, 2, 3],
        }
        result = normalize_payload("SomeNewEvent", payload)
        assert len(result["long_string"]) == 200
        assert result["number"] == 42
        assert result["nested_dict"] == "<dict>"
        assert result["list_items"] == "<list[3]>"

    def test_missing_nested_field(self) -> None:
        payload = {}
        result = normalize_payload("PullRequestEvent", payload)
        assert result["action"] is None
        assert result["number"] is None
        assert result["title"] is None


class TestToEventRow:
    """GitHubEvent → EventRow 변환 테스트."""

    def test_basic_conversion(self) -> None:
        event = _make_event(
            event_id="12345",
            event_type="PushEvent",
            org_login="pseudolab",
            repo_name="pseudolab/test-repo",
            payload={"size": 1},
            created_at="2024-01-15T10:30:00Z",
        )
        row = to_event_row(event, batch_date="2024-01-15")
        assert row["id"] == "12345"
        assert row["type"] == "PushEvent"
        assert row["actor_login"] == "testuser"
        assert row["repo_name"] == "pseudolab/test-repo"
        assert row["org_name"] == "pseudolab"
        assert row["batch_date"] == "2024-01-15"
        assert "size" in json.loads(row["payload"])

    def test_org_none(self) -> None:
        event = _make_event(org_login=None)
        row = to_event_row(event, batch_date="2024-01-15")
        assert row["org_name"] is None

    def test_created_at_format(self) -> None:
        event = _make_event(created_at="2024-01-15T10:30:00Z")
        row = to_event_row(event, batch_date="2024-01-15")
        assert "T" in row["created_at"]
        assert row["created_at"].startswith("2024-01-15")

    def test_payload_is_json_string(self) -> None:
        event = _make_event(payload={"size": 1})
        row = to_event_row(event, batch_date="2024-01-15")
        parsed = json.loads(row["payload"])
        assert isinstance(parsed, dict)
        assert "size" in parsed


class TestDeduplicate:
    """중복 제거 로직 테스트."""

    def test_no_duplicates(self) -> None:
        rows = [
            _make_row(id="1"),
            _make_row(id="2"),
            _make_row(id="3"),
        ]
        result, dup_count = deduplicate(rows)
        assert len(result) == 3
        assert dup_count == 0

    def test_removes_duplicates(self) -> None:
        rows = [
            _make_row(id="1"),
            _make_row(id="2"),
            _make_row(id="1"),
            _make_row(id="3"),
            _make_row(id="2"),
        ]
        result, dup_count = deduplicate(rows)
        assert len(result) == 3
        assert dup_count == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"
        assert result[2]["id"] == "3"

    def test_empty_input(self) -> None:
        result, dup_count = deduplicate([])
        assert result == []
        assert dup_count == 0


class TestValidateRow:
    """행 유효성 검사 테스트."""

    def test_valid_row(self) -> None:
        row = _make_row()
        is_valid, error = validate_row(row)
        assert is_valid is True
        assert error is None

    def test_empty_id(self) -> None:
        row = _make_row(id="")
        is_valid, error = validate_row(row)
        assert is_valid is False
        assert error is not None
        assert "id" in error

    def test_invalid_payload_json(self) -> None:
        row = _make_row(payload="not-json{")
        is_valid, error = validate_row(row)
        assert is_valid is False
        assert error is not None
        assert "payload" in error

    def test_invalid_created_at_format(self) -> None:
        row = _make_row(created_at="2024/01/15")
        is_valid, error = validate_row(row)
        assert is_valid is False
        assert error is not None
        assert "created_at" in error

    def test_invalid_batch_date_format(self) -> None:
        row = _make_row(batch_date="20240115")
        is_valid, error = validate_row(row)
        assert is_valid is False
        assert error is not None
        assert "batch_date" in error


class TestTransformEvents:
    """전체 변환 파이프라인 테스트."""

    def test_full_pipeline(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent"),
            _make_event(event_id="2", event_type="IssuesEvent"),
            _make_event(event_id="3", event_type="WatchEvent"),
        ]
        rows, stats = transform_events(events, batch_date="2024-01-15")
        assert len(rows) == 3
        assert stats.total_input == 3
        assert stats.total_output == 3

    def test_stats_input_type_counts(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent"),
            _make_event(event_id="2", event_type="PushEvent"),
            _make_event(event_id="3", event_type="IssuesEvent"),
        ]
        _, stats = transform_events(events, batch_date="2024-01-15")
        assert stats.input_type_counts["PushEvent"] == 2
        assert stats.input_type_counts["IssuesEvent"] == 1

    def test_stats_output_type_counts(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent"),
            _make_event(event_id="2", event_type="PushEvent"),
            _make_event(event_id="3", event_type="IssuesEvent"),
        ]
        _, stats = transform_events(events, batch_date="2024-01-15")
        assert stats.output_type_counts["PushEvent"] == 2
        assert stats.output_type_counts["IssuesEvent"] == 1

    def test_validation_error_skipped(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent"),
        ]
        # Pass invalid batch_date to trigger validation errors
        _, stats = transform_events(events, batch_date="not-a-date")
        assert stats.validation_errors > 0
        assert stats.total_output == 0

    def test_duplicates_in_stats(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent"),
            _make_event(event_id="1", event_type="PushEvent"),
        ]
        _rows, stats = transform_events(events, batch_date="2024-01-15")
        assert stats.duplicates_removed == 1
        assert stats.total_output == 1


class TestComputeDailyStats:
    """일별 통계 집계 테스트."""

    def test_compute_daily_stats_basic(self) -> None:
        rows = [
            _make_row(
                id="1",
                type="PushEvent",
                org_name="pseudolab",
                repo_name="pseudolab/repo",
                batch_date="2024-01-15",
            ),
            _make_row(
                id="2",
                type="PushEvent",
                org_name="pseudolab",
                repo_name="pseudolab/repo",
                batch_date="2024-01-15",
            ),
        ]
        stats = compute_daily_stats(rows)
        assert len(stats) == 1
        assert stats[0]["date"] == "2024-01-15"
        assert stats[0]["org_name"] == "pseudolab"
        assert stats[0]["repo_name"] == "pseudolab/repo"
        assert stats[0]["event_type"] == "PushEvent"
        assert stats[0]["count"] == 2

    def test_compute_daily_stats_null_org(self) -> None:
        rows = [
            _make_row(
                id="1",
                type="PushEvent",
                org_name=None,
                repo_name="user/repo",
                batch_date="2024-01-15",
            ),
        ]
        stats = compute_daily_stats(rows)
        assert len(stats) == 1
        assert stats[0]["org_name"] == ""
        assert stats[0]["count"] == 1

    def test_compute_daily_stats_multiple_types(self) -> None:
        rows = [
            _make_row(
                id="1",
                type="PushEvent",
                org_name="pseudolab",
                repo_name="pseudolab/repo",
                batch_date="2024-01-15",
            ),
            _make_row(
                id="2",
                type="IssuesEvent",
                org_name="pseudolab",
                repo_name="pseudolab/repo",
                batch_date="2024-01-15",
            ),
            _make_row(
                id="3",
                type="PushEvent",
                org_name="pseudolab",
                repo_name="pseudolab/repo",
                batch_date="2024-01-15",
            ),
        ]
        stats = compute_daily_stats(rows)
        assert len(stats) == 2
        # sorted by key: (date, org, repo, type) so IssuesEvent < PushEvent
        assert stats[0]["event_type"] == "IssuesEvent"
        assert stats[0]["count"] == 1
        assert stats[1]["event_type"] == "PushEvent"
        assert stats[1]["count"] == 2

    def test_compute_daily_stats_empty(self) -> None:
        stats = compute_daily_stats([])
        assert stats == []
