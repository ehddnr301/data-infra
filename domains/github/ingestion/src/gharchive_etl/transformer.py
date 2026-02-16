"""이벤트 필터링 후 D1 적재를 위한 가공 로직."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypedDict

from gharchive_etl.models import GitHubEvent

logger = logging.getLogger(__name__)


class EventRow(TypedDict):
    """D1 events 테이블 행 타입."""

    id: str  # event.id (PRIMARY KEY)
    type: str  # event.type
    actor_login: str  # event.actor.login
    repo_name: str  # event.repo.name
    org_name: str | None  # event.org.login (NULL 가능)
    payload: str  # json.dumps(normalized_payload)
    created_at: str  # ISO 8601 형식
    batch_date: str  # YYYY-MM-DD


@dataclass
class TransformStats:
    """가공 결과 통계."""

    total_input: int = 0
    total_output: int = 0
    duplicates_removed: int = 0
    validation_errors: int = 0
    input_type_counts: dict[str, int] = field(default_factory=dict)
    output_type_counts: dict[str, int] = field(default_factory=dict)
    error_details: list[str] = field(default_factory=list)


# Payload Extractors


def _extract_push(payload: dict[str, Any]) -> dict[str, Any]:
    """PushEvent 페이로드 추출."""
    commits = payload.get("commits", [])
    return {
        "size": payload.get("size"),
        "distinct_size": payload.get("distinct_size"),
        "ref": payload.get("ref"),
        "commits": [
            {
                "sha": c.get("sha"),
                "message": (c.get("message") or "")[:200],
            }
            for c in commits
        ],
    }


def _extract_pull_request(payload: dict[str, Any]) -> dict[str, Any]:
    """PullRequestEvent 페이로드 추출."""
    pr = payload.get("pull_request", {})
    return {
        "action": payload.get("action"),
        "number": payload.get("number"),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "merged": pr.get("merged"),
        "additions": pr.get("additions"),
        "deletions": pr.get("deletions"),
        "changed_files": pr.get("changed_files"),
    }


def _extract_issues(payload: dict[str, Any]) -> dict[str, Any]:
    """IssuesEvent 페이로드 추출."""
    issue = payload.get("issue", {})
    labels = issue.get("labels", [])
    return {
        "action": payload.get("action"),
        "number": issue.get("number"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "labels": [label.get("name") for label in labels],
    }


def _extract_issue_comment(payload: dict[str, Any]) -> dict[str, Any]:
    """IssueCommentEvent 페이로드 추출."""
    issue = payload.get("issue", {})
    comment = payload.get("comment", {})
    return {
        "action": payload.get("action"),
        "issue_number": issue.get("number"),
        "comment_id": comment.get("id"),
    }


def _extract_watch(payload: dict[str, Any]) -> dict[str, Any]:
    """WatchEvent 페이로드 추출."""
    return {
        "action": payload.get("action"),
    }


def _extract_fork(payload: dict[str, Any]) -> dict[str, Any]:
    """ForkEvent 페이로드 추출."""
    forkee = payload.get("forkee", {})
    return {
        "forkee_full_name": forkee.get("full_name"),
    }


def _extract_create(payload: dict[str, Any]) -> dict[str, Any]:
    """CreateEvent 페이로드 추출."""
    return {
        "ref": payload.get("ref"),
        "ref_type": payload.get("ref_type"),
        "master_branch": payload.get("master_branch"),
    }


def _extract_delete(payload: dict[str, Any]) -> dict[str, Any]:
    """DeleteEvent 페이로드 추출."""
    return {
        "ref": payload.get("ref"),
        "ref_type": payload.get("ref_type"),
    }


def _extract_release(payload: dict[str, Any]) -> dict[str, Any]:
    """ReleaseEvent 페이로드 추출."""
    release = payload.get("release", {})
    return {
        "action": payload.get("action"),
        "tag_name": release.get("tag_name"),
        "name": release.get("name"),
        "prerelease": release.get("prerelease"),
    }


def _extract_pull_request_review(payload: dict[str, Any]) -> dict[str, Any]:
    """PullRequestReviewEvent 페이로드 추출."""
    review = payload.get("review", {})
    pr = payload.get("pull_request", {})
    return {
        "action": payload.get("action"),
        "review_state": review.get("state"),
        "pull_request_number": pr.get("number"),
    }


def _extract_pull_request_review_comment(payload: dict[str, Any]) -> dict[str, Any]:
    """PullRequestReviewCommentEvent 페이로드 추출."""
    comment = payload.get("comment", {})
    pr = payload.get("pull_request", {})
    return {
        "action": payload.get("action"),
        "comment_id": comment.get("id"),
        "pull_request_number": pr.get("number"),
    }


def _extract_member(payload: dict[str, Any]) -> dict[str, Any]:
    """MemberEvent 페이로드 추출."""
    member = payload.get("member", {})
    return {
        "action": payload.get("action"),
        "member_login": member.get("login"),
    }


def _extract_public(payload: dict[str, Any]) -> dict[str, Any]:
    """PublicEvent 페이로드 추출."""
    return {}


def _extract_gollum(payload: dict[str, Any]) -> dict[str, Any]:
    """GollumEvent 페이로드 추출."""
    pages = payload.get("pages", [])
    return {
        "pages": [
            {
                "action": page.get("action"),
                "title": page.get("title"),
            }
            for page in pages
        ],
    }


def _extract_fallback(payload: dict[str, Any]) -> dict[str, Any]:
    """알려지지 않은 이벤트 타입에 대한 fallback 추출.

    - top-level 키만 추출
    - 문자열은 200자로 제한
    - 중첩된 객체는 타입 표시만
    """
    result: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            result[key] = value[:200]
        elif isinstance(value, (int, float, bool, type(None))):
            result[key] = value
        elif isinstance(value, dict):
            result[key] = "<dict>"
        elif isinstance(value, list):
            result[key] = f"<list[{len(value)}]>"
        else:
            result[key] = f"<{type(value).__name__}>"
    return result


# Payload extractor dispatch table
_PAYLOAD_EXTRACTORS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "PushEvent": _extract_push,
    "PullRequestEvent": _extract_pull_request,
    "IssuesEvent": _extract_issues,
    "IssueCommentEvent": _extract_issue_comment,
    "WatchEvent": _extract_watch,
    "ForkEvent": _extract_fork,
    "CreateEvent": _extract_create,
    "DeleteEvent": _extract_delete,
    "ReleaseEvent": _extract_release,
    "PullRequestReviewEvent": _extract_pull_request_review,
    "PullRequestReviewCommentEvent": _extract_pull_request_review_comment,
    "MemberEvent": _extract_member,
    "PublicEvent": _extract_public,
    "GollumEvent": _extract_gollum,
}


def normalize_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """이벤트 타입에 따라 페이로드를 정규화한다."""
    extractor = _PAYLOAD_EXTRACTORS.get(event_type)
    if extractor:
        return extractor(payload)
    return _extract_fallback(payload)


def to_event_row(event: GitHubEvent, batch_date: str) -> EventRow:
    """GitHubEvent를 EventRow로 변환한다."""
    normalized = normalize_payload(event.type, event.payload)
    return EventRow(
        id=event.id,
        type=event.type,
        actor_login=event.actor.login,
        repo_name=event.repo.name,
        org_name=event.org.login if event.org else None,
        payload=json.dumps(normalized, ensure_ascii=False),
        created_at=event.created_at.isoformat(),
        batch_date=batch_date,
    )


def deduplicate(rows: list[EventRow]) -> tuple[list[EventRow], int]:
    """중복된 이벤트 ID를 제거한다."""
    seen: set[str] = set()
    unique: list[EventRow] = []
    duplicates = 0

    for row in rows:
        if row["id"] in seen:
            duplicates += 1
            continue
        seen.add(row["id"])
        unique.append(row)

    return unique, duplicates


# Validation regex patterns
_CREATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_BATCH_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_row(row: EventRow) -> tuple[bool, str | None]:
    """EventRow의 유효성을 검증한다.

    Returns:
        (valid, error_message) 튜플
    """
    # id 검증
    if not row["id"]:
        return False, "id is empty"

    # type 검증
    if not row["type"]:
        return False, "type is empty"

    # actor_login 검증
    if not row["actor_login"]:
        return False, "actor_login is empty"

    # repo_name 검증
    if not row["repo_name"]:
        return False, "repo_name is empty"

    # payload JSON 검증
    try:
        json.loads(row["payload"])
    except (json.JSONDecodeError, TypeError) as e:
        return False, f"payload is not valid JSON: {e}"

    # created_at 형식 검증
    if not _CREATED_AT_RE.match(row["created_at"]):
        return False, f"created_at format invalid: {row['created_at']}"

    # batch_date 형식 검증
    if not _BATCH_DATE_RE.match(row["batch_date"]):
        return False, f"batch_date format invalid: {row['batch_date']}"

    return True, None


def transform_events(
    events: list[GitHubEvent],
    batch_date: str,
) -> tuple[list[EventRow], TransformStats]:
    """GitHubEvent 리스트를 EventRow 리스트로 변환한다.

    Pipeline:
    1. 입력 카운트
    2. 타입별 통계 수집
    3. to_event_row() 변환 + validate_row() 검증
    4. deduplicate() 중복 제거
    5. 출력 타입별 통계 수집
    6. 로그 출력
    """
    stats = TransformStats()
    stats.total_input = len(events)

    # 입력 타입별 카운트
    for event in events:
        stats.input_type_counts[event.type] = stats.input_type_counts.get(event.type, 0) + 1

    # 변환 + 검증
    valid_rows: list[EventRow] = []
    for event in events:
        try:
            row = to_event_row(event, batch_date)
            is_valid, error = validate_row(row)

            if not is_valid:
                stats.validation_errors += 1
                error_msg = f"Validation failed for event {row['id']}: {error}"
                stats.error_details.append(error_msg)
                logger.warning(error_msg)
                continue

            valid_rows.append(row)

        except Exception as e:
            stats.validation_errors += 1
            error_msg = f"Transform failed for event {event.id}: {e}"
            stats.error_details.append(error_msg)
            logger.error(error_msg)
            continue

    # 중복 제거
    unique_rows, duplicates = deduplicate(valid_rows)
    stats.duplicates_removed = duplicates

    # 출력 타입별 카운트
    for row in unique_rows:
        stats.output_type_counts[row["type"]] = stats.output_type_counts.get(row["type"], 0) + 1

    stats.total_output = len(unique_rows)

    # 로그 출력
    logger.info(
        "Transform complete: input=%d, output=%d, duplicates=%d, errors=%d",
        stats.total_input,
        stats.total_output,
        stats.duplicates_removed,
        stats.validation_errors,
    )

    return unique_rows, stats


class DailyStatsRow(TypedDict):
    """D1 daily_stats 테이블 행 타입."""

    date: str
    org_name: str
    repo_name: str
    event_type: str
    count: int


def compute_daily_stats(rows: list[EventRow]) -> list[DailyStatsRow]:
    """EventRow 리스트에서 일별 통계를 집계한다."""
    counter: dict[tuple[str, str, str, str], int] = {}
    for row in rows:
        key = (row["batch_date"], row["org_name"] or "", row["repo_name"], row["type"])
        counter[key] = counter.get(key, 0) + 1
    return [
        DailyStatsRow(date=k[0], org_name=k[1], repo_name=k[2], event_type=k[3], count=v)
        for k, v in sorted(counter.items())
    ]
