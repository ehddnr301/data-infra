from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx

from gharchive_etl.dl_models import DL_TABLE_COLUMNS

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
KNOWN_KEY_COLUMN_DESCRIPTIONS: dict[str, str] = {
    "event_id": "GitHub event unique identifier.",
    "repo_name": "Repository full name (owner/repo).",
    "organization": "Organization login associated with the event.",
    "user_login": "Actor login that triggered the event.",
    "ts_kst": "Event timestamp converted to KST timezone.",
    "base_date": "ETL batch base date (YYYY-MM-DD).",
    "source": "Ingestion source channel.",
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


def _column_description(table_name: str, column_name: str) -> str:
    known = KNOWN_KEY_COLUMN_DESCRIPTIONS.get(column_name)
    if known:
        return known
    return f"Column `{column_name}` generated from `{table_name}` table during ETL."


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


def build_lineage_graph(dataset_id: str) -> dict[str, Any]:
    source_dataset_id = "github.raw-events.v1"
    nodes = [
        {
            "id": dataset_id,
            "type": "dataset",
            "position": {"x": 0, "y": 0},
            "data": {
                "datasetId": dataset_id,
                "label": dataset_id,
                "domain": "github",
            },
        }
    ]
    edges: list[dict[str, Any]] = []

    if dataset_id != source_dataset_id:
        nodes.insert(
            0,
            {
                "id": source_dataset_id,
                "type": "dataset",
                "position": {"x": -260, "y": 0},
                "data": {
                    "datasetId": source_dataset_id,
                    "label": source_dataset_id,
                    "domain": "github",
                },
            },
        )
        edges.append(
            {
                "id": f"{source_dataset_id}->{dataset_id}",
                "source": source_dataset_id,
                "target": dataset_id,
                "data": {"step": "transform-load"},
                "label": "transform-load",
            }
        )

    return {
        "version": 1,
        "nodes": nodes,
        "edges": edges,
    }


def build_dataset_snapshots() -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for table_name, columns in sorted(DL_TABLE_COLUMNS.items()):
        dataset_id = _dataset_id_from_table(table_name)
        snapshots.append(
            {
                "dataset_id": dataset_id,
                "snapshot": {
                    "dataset": {
                        "id": dataset_id,
                        "domain": "github",
                        "name": f"GitHub {_table_suffix(table_name)}",
                        "description": f"Auto-synced metadata for `{table_name}`.",
                        "schema_json": {
                            "version": 1,
                            "source_table": table_name,
                        },
                        "owner": "github-ingestion",
                        "tags": ["github", "etl", "auto-sync"],
                    },
                    "columns": build_column_metadata(table_name, columns),
                    "lineage": build_lineage_graph(dataset_id),
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
