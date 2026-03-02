from __future__ import annotations

import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx

from gharchive_etl.dl_models import DL_TABLE_COLUMNS, TABLE_TO_EVENT_TYPE

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
KNOWN_KEY_COLUMN_DESCRIPTIONS: dict[str, str] = {
    "event_id": "GitHub 이벤트를 고유하게 식별하는 ID입니다.",
    "repo_name": "이벤트가 발생한 저장소 전체 이름(owner/repo)입니다.",
    "organization": "이벤트가 속한 조직 로그인 이름입니다.",
    "user_login": "이벤트를 발생시킨 사용자 로그인입니다.",
    "ts_kst": "이벤트 발생 시각(한국 시간, KST)입니다.",
    "base_date": "ETL 배치 기준일(YYYY-MM-DD)입니다.",
    "source": "수집 소스(gharchive 또는 rest_api)입니다.",
    "ref_full": "Git ref 전체 경로입니다(예: refs/heads/main).",
    "ref_name": "브랜치/태그의 짧은 ref 이름입니다.",
    "head_sha": "이벤트 시점의 HEAD 커밋 SHA입니다.",
    "before_sha": "이벤트 직전 커밋 SHA입니다.",
    "pr_number": "Pull Request 번호입니다.",
    "issue_number": "Issue 번호입니다.",
    "comment_id": "댓글 고유 ID입니다.",
    "review_id": "리뷰 고유 ID입니다.",
    "review_comment_id": "리뷰 댓글 고유 ID입니다.",
    "action": "이벤트에서 발생한 동작 유형입니다.",
    "commit_sha": "커밋 SHA 식별자입니다.",
    "pr_title": "Pull Request 제목입니다.",
    "issue_title": "Issue 제목입니다.",
    "body": "본문 텍스트입니다.",
    "state": "이슈/리뷰의 상태 값입니다.",
    "release_id": "릴리스 고유 ID입니다.",
    "release_tag_name": "릴리스 태그 이름입니다.",
}
PII_COLUMN_NAMES = {
    "commit_author_email",
}


@dataclass
class SyncError:
    dataset_id: str
    stage: str
    message: str


@dataclass
class SyncSummary:
    datasets_total: int = 0
    datasets_succeeded: int = 0
    dataset_errors: list[SyncError] = field(default_factory=list)
    lineage_errors: list[SyncError] = field(default_factory=list)

    @property
    def errors(self) -> list[SyncError]:
        return [*self.dataset_errors, *self.lineage_errors]


def _table_suffix(table_name: str) -> str:
    return table_name.removeprefix("dl_").replace("_", "-")


def _dataset_id_from_table(table_name: str) -> str:
    return f"github.{_table_suffix(table_name)}.v1"


def _infer_data_type(column_name: str) -> str:
    if column_name.startswith("is_"):
        return "INTEGER"

    integer_like_exact = {
        "count",
        "additions",
        "deletions",
        "changed_files",
        "pr_number",
        "issue_number",
        "review_id",
        "review_comment_id",
        "comment_id",
        "member_id",
        "forkee_id",
        "pr_author_id",
        "issue_author_id",
        "commenter_id",
        "reviewer_id",
        "commits_count",
        "issue_comments_count",
        "review_comments_count",
    }

    if column_name in integer_like_exact:
        return "INTEGER"
    if column_name.endswith("_id") and column_name not in {"event_id"}:
        return "INTEGER"
    return "TEXT"


def _event_display_name(table_name: str) -> str:
    event_type = TABLE_TO_EVENT_TYPE.get(table_name)
    if not event_type:
        return table_name

    core = event_type.removesuffix("Event")
    spaced = re.sub(r"(?<!^)([A-Z])", r" \1", core).strip()
    return f"{spaced} Events"


def _column_description(table_name: str, column_name: str) -> str:
    known = KNOWN_KEY_COLUMN_DESCRIPTIONS.get(column_name)
    if known:
        return known

    if column_name.startswith("is_"):
        return f"`{column_name}` 조건 충족 여부를 나타내는 불리언 플래그입니다."

    if column_name.endswith("_id"):
        return f"연관 엔터티를 식별하는 `{column_name}` 키 값입니다."

    if column_name.endswith("_url"):
        return f"원본 리소스를 조회할 수 있는 `{column_name}` URL입니다."

    if column_name.endswith("_count"):
        return f"집계 개수를 나타내는 `{column_name}` 수치입니다."

    return f"`{table_name}` 분석에 사용하는 `{column_name}` 속성입니다."


def _dataset_description(table_name: str, event_display_name: str) -> str:
    return (
        f"`{table_name}` 테이블은 {event_display_name} 이벤트를 저장합니다. "
        "gharchive와 rest_api 소스를 통합해 생성되며, "
        "리포지토리 활동 추세 분석과 운영 모니터링에 활용할 수 있습니다."
    )


def build_column_metadata(table_name: str, columns: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "column_name": column_name,
            "data_type": _infer_data_type(column_name),
            "description": _column_description(table_name, column_name),
            "is_pii": column_name in PII_COLUMN_NAMES,
            "examples": None,
        }
        for column_name in columns
    ]


def build_lineage_graph(dataset_id: str, dataset_label: str) -> dict[str, Any]:
    raw_source_dataset_id = "github.raw-events.v1"
    rest_source_dataset_id = "github.rest-events.v1"
    nodes = [
        {
            "id": dataset_id,
            "type": "dataset",
            "position": {"x": 0, "y": 0},
            "data": {
                "datasetId": dataset_id,
                "label": dataset_label,
                "domain": "github",
            },
        },
        {
            "id": raw_source_dataset_id,
            "type": "dataset",
            "position": {"x": -280, "y": -100},
            "data": {
                "datasetId": raw_source_dataset_id,
                "label": "GitHub Raw Events",
                "domain": "github",
            },
        },
        {
            "id": rest_source_dataset_id,
            "type": "dataset",
            "position": {"x": -280, "y": 100},
            "data": {
                "datasetId": rest_source_dataset_id,
                "label": "GitHub REST Events",
                "domain": "github",
            },
        },
    ]
    edges: list[dict[str, Any]] = [
        {
            "id": f"{raw_source_dataset_id}->{dataset_id}:ingest-gharchive",
            "source": raw_source_dataset_id,
            "target": dataset_id,
            "data": {"step": "ingest-gharchive"},
            "label": "ingest-gharchive",
        },
        {
            "id": f"{rest_source_dataset_id}->{dataset_id}:ingest-rest-api",
            "source": rest_source_dataset_id,
            "target": dataset_id,
            "data": {"step": "ingest-rest-api"},
            "label": "ingest-rest-api",
        },
        {
            "id": f"{raw_source_dataset_id}->{dataset_id}:transform-load",
            "source": raw_source_dataset_id,
            "target": dataset_id,
            "data": {"step": "transform-load"},
            "label": "transform-load",
        },
    ]

    return {
        "version": 1,
        "nodes": nodes,
        "edges": edges,
    }


def build_dataset_snapshots() -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for table_name, columns in sorted(DL_TABLE_COLUMNS.items()):
        dataset_id = _dataset_id_from_table(table_name)
        event_display_name = _event_display_name(table_name)
        dataset_name = f"{event_display_name} ({table_name})"
        snapshots.append(
            {
                "dataset_id": dataset_id,
                "snapshot": {
                    "dataset": {
                        "id": dataset_id,
                        "domain": "github",
                        "name": table_name,
                        "description": _dataset_description(table_name, event_display_name),
                        "schema_json": {
                            "version": 1,
                            "source_table": table_name,
                            "display_name": event_display_name,
                        },
                        "owner": "github-ingestion",
                        "tags": ["github", "etl", "auto-sync"],
                    },
                    "columns": build_column_metadata(table_name, columns),
                    "lineage": build_lineage_graph(dataset_id, dataset_name),
                },
            }
        )
    return snapshots


def _backoff_seconds(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    delay = min(base * (2**attempt), cap)
    jitter = random.uniform(0, 0.2 * delay)
    return delay + jitter


def _retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    if value.isdigit():
        return float(value)
    return None


def _request_with_retry(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any],
    timeout_sec: float = 10.0,
    max_retries: int = 3,
) -> tuple[bool, int | None, str | None]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout_sec) as client:
        for attempt in range(max_retries + 1):
            try:
                response = client.request(method, url, headers=headers, json=payload)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= max_retries:
                    return False, None, str(exc)
                time.sleep(_backoff_seconds(attempt))
                continue

            if response.status_code < 400:
                return True, response.status_code, None

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
                time.sleep(retry_after if retry_after is not None else _backoff_seconds(attempt))
                continue

            return False, response.status_code, response.text

    return False, None, "unknown retry loop failure"


def put_dataset_snapshot(
    base_url: str,
    token: str,
    dataset_id: str,
    payload: dict[str, Any],
) -> tuple[bool, int | None, str | None]:
    encoded_id = quote(dataset_id, safe="")
    url = f"{base_url.rstrip('/')}/catalog/datasets/{encoded_id}/snapshot"
    return _request_with_retry(method="PUT", url=url, token=token, payload=payload)


def put_lineage(
    base_url: str,
    token: str,
    dataset_id: str,
    lineage: dict[str, Any],
) -> tuple[bool, int | None, str | None]:
    encoded_id = quote(dataset_id, safe="")
    url = f"{base_url.rstrip('/')}/catalog/lineage/{encoded_id}"
    return _request_with_retry(method="PUT", url=url, token=token, payload=lineage)


def sync_catalog(
    *,
    base_url: str,
    token: str,
    dry_run: bool = False,
) -> SyncSummary:
    summary = SyncSummary()
    snapshots = build_dataset_snapshots()
    summary.datasets_total = len(snapshots)

    for item in snapshots:
        dataset_id = item["dataset_id"]
        snapshot = item["snapshot"]
        lineage = snapshot.get("lineage")

        if dry_run:
            logger.info(
                "[sync-catalog][dry-run] dataset=%s payload=%s", dataset_id, json.dumps(snapshot)
            )
            summary.datasets_succeeded += 1
            continue

        ok_snapshot, status_snapshot, detail_snapshot = put_dataset_snapshot(
            base_url=base_url,
            token=token,
            dataset_id=dataset_id,
            payload=snapshot,
        )
        if not ok_snapshot:
            summary.dataset_errors.append(
                SyncError(
                    dataset_id=dataset_id,
                    stage="snapshot",
                    message=f"status={status_snapshot}, detail={detail_snapshot}",
                )
            )
            continue

        if isinstance(lineage, dict):
            ok_lineage, status_lineage, detail_lineage = put_lineage(
                base_url=base_url,
                token=token,
                dataset_id=dataset_id,
                lineage=lineage,
            )
            if not ok_lineage:
                summary.lineage_errors.append(
                    SyncError(
                        dataset_id=dataset_id,
                        stage="lineage",
                        message=f"status={status_lineage}, detail={detail_lineage}",
                    )
                )

        summary.datasets_succeeded += 1

    return summary
