from __future__ import annotations

import httpx

from gharchive_etl.catalog_sync import (
    _request_with_retry,
    build_dataset_snapshots,
    build_lineage_graph,
    sync_catalog,
)
from gharchive_etl.dl_models import DL_TABLE_COLUMNS


def test_build_dataset_snapshots_contains_all_dl_tables() -> None:
    snapshots = build_dataset_snapshots()
    assert len(snapshots) == len(DL_TABLE_COLUMNS)

    dataset_ids = {item["dataset_id"] for item in snapshots}
    assert "github.push-events.v1" in dataset_ids
    assert "github.issue-comment-events.v1" in dataset_ids


def test_build_lineage_graph_dataset_only_nodes() -> None:
    graph = build_lineage_graph("github.push-events.v1", "Push Events (dl_push_events)")

    assert graph["version"] == 1
    assert all(node["type"] == "dataset" for node in graph["nodes"])
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 3
    steps = {edge["data"]["step"] for edge in graph["edges"]}
    assert steps == {"ingest-gharchive", "ingest-rest-api", "transform-load"}


def test_build_dataset_snapshots_name_and_description_rules() -> None:
    snapshots = build_dataset_snapshots()
    push_snapshot = next(
        item for item in snapshots if item["dataset_id"] == "github.push-events.v1"
    )
    dataset = push_snapshot["snapshot"]["dataset"]

    assert dataset["name"] == "dl_push_events"
    assert "`dl_push_events`" in dataset["description"]
    assert "gharchive" in dataset["description"]
    assert "rest_api" in dataset["description"]
    assert "활동 추세 분석" in dataset["description"]
    assert dataset["schema_json"]["display_name"] == "Push Events"
    assert "변경 파일" in dataset["purpose"]
    assert any("enriched/commits" in example for example in dataset["usage_examples"])
    assert any("R2 enrich 경로" in item for item in dataset["limitations"])


def test_build_dataset_snapshots_review_comment_examples_reference_enrich() -> None:
    snapshots = build_dataset_snapshots()
    review_snapshot = next(
        item
        for item in snapshots
        if item["dataset_id"] == "github.pull-request-review-comment-events.v1"
    )
    dataset = review_snapshot["snapshot"]["dataset"]

    assert any("diff_hunk" in example for example in dataset["usage_examples"])
    assert any("enriched/pr-files" in example for example in dataset["usage_examples"])
    assert any("diff_hunk" in item for item in dataset["limitations"])


def test_build_dataset_snapshots_column_description_rules() -> None:
    snapshots = build_dataset_snapshots()
    push_snapshot = next(
        item for item in snapshots if item["dataset_id"] == "github.push-events.v1"
    )
    columns = push_snapshot["snapshot"]["columns"]
    source_column = next(column for column in columns if column["column_name"] == "source")
    commit_url_column = next(column for column in columns if column["column_name"] == "commit_url")

    assert "gharchive 또는 rest_api" in source_column["description"]
    assert (
        commit_url_column["description"] == "원본 리소스를 조회할 수 있는 `commit_url` URL입니다."
    )


def test_sync_catalog_dry_run_has_no_errors() -> None:
    summary = sync_catalog(base_url="http://example.com/api", token="token", dry_run=True)

    assert summary.datasets_total == len(DL_TABLE_COLUMNS)
    assert summary.datasets_succeeded == len(DL_TABLE_COLUMNS)
    assert summary.errors == []


def test_sync_catalog_aggregates_snapshot_and_lineage_errors(monkeypatch) -> None:
    def fake_snapshot(*, base_url, token, dataset_id, payload):
        if dataset_id.endswith("push-events.v1"):
            return False, 400, "validation failed"
        return True, 200, None

    def fake_lineage(*, base_url, token, dataset_id, lineage):
        if dataset_id.endswith("issues-events.v1"):
            return False, 503, "service unavailable"
        return True, 200, None

    monkeypatch.setattr("gharchive_etl.catalog_sync.put_dataset_snapshot", fake_snapshot)
    monkeypatch.setattr("gharchive_etl.catalog_sync.put_lineage", fake_lineage)

    summary = sync_catalog(base_url="http://example.com/api", token="token", dry_run=False)

    assert any(err.stage == "snapshot" for err in summary.dataset_errors)
    assert any(err.stage == "lineage" for err in summary.lineage_errors)
    assert summary.datasets_succeeded == summary.datasets_total - 1


def test_request_with_retry_retries_on_503(monkeypatch) -> None:
    responses = [
        httpx.Response(503, request=httpx.Request("PUT", "http://example.com"), text="busy"),
        httpx.Response(200, request=httpx.Request("PUT", "http://example.com"), text="ok"),
    ]
    call_count = {"value": 0}

    def fake_request(self, method, url, headers, json):
        call_count["value"] += 1
        return responses.pop(0)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    monkeypatch.setattr("gharchive_etl.catalog_sync.time.sleep", lambda _: None)

    ok, status, detail = _request_with_retry(
        method="PUT",
        url="http://example.com",
        token="token",
        payload={"k": "v"},
        max_retries=2,
    )

    assert ok is True
    assert status == 200
    assert detail is None
    assert call_count["value"] == 2


def test_request_with_retry_does_not_retry_on_400(monkeypatch) -> None:
    call_count = {"value": 0}

    def fake_request(self, method, url, headers, json):
        call_count["value"] += 1
        return httpx.Response(400, request=httpx.Request("PUT", url), text="bad request")

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    monkeypatch.setattr("gharchive_etl.catalog_sync.time.sleep", lambda _: None)

    ok, status, detail = _request_with_retry(
        method="PUT",
        url="http://example.com",
        token="token",
        payload={"k": "v"},
        max_retries=3,
    )

    assert ok is False
    assert status == 400
    assert detail == "bad request"
    assert call_count["value"] == 1
