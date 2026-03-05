from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
import pytest
from config import Settings
from planner import PlanDraft, Planner


def _build_settings() -> Settings:
    return Settings.model_construct(
        slack_bot_token="xoxb-test",
        slack_signing_secret="secret",
        slack_channel_id="C123",
        anthropic_api_key="test",
        anthropic_model="claude-sonnet-4-5-20250929",
        anthropic_timeout_seconds=30.0,
        anthropic_max_retries=2,
        anthropic_max_tokens=1024,
        planner_prompt_max_columns=80,
        planner_fallback_max_columns=30,
        catalog_api_base_url="http://example.com",
        catalog_internal_bearer="token",
        run_mode="dry-run",
        write_enabled=False,
        approval_ttl_seconds=300,
        max_retry_attempts=3,
        retry_backoff_ms=1000,
        app_version="0.1.0",
    )


def test_generate_plan_maps_descriptions(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run() -> tuple[str, dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            planner = Planner(_build_settings(), client, logging.getLogger("planner-test"))

            async def fake_snapshot(request_id: str, *, dataset_id: str | None = None):
                assert dataset_id is None
                return {
                    "dataset": {
                        "id": "github.push-events.v1",
                        "domain": "github",
                        "name": "Push Events",
                        "description": "old",
                        "schema_json": {"version": 1},
                        "lineage_json": '{"version":1,"nodes":[],"edges":[]}',
                        "owner": "github-ingestion",
                        "tags": ["github"],
                    },
                    "columns": [
                        {
                            "column_name": "repo_name",
                            "data_type": "text",
                            "description": "old desc",
                        },
                    ],
                }

            async def fake_draft(seed_text: str, snapshot):
                return PlanDraft(
                    table_description="new table description",
                    column_descriptions={"repo_name": "repository name"},
                    usage_examples=["monthly trend"],
                    purpose="track activity",
                )

            monkeypatch.setattr(planner, "_fetch_catalog_snapshot", fake_snapshot)
            monkeypatch.setattr(planner, "_generate_draft", fake_draft)

            return await planner.generate_plan("seed", "req-1")

    dataset_id, payload = asyncio.run(run())

    assert dataset_id == "github.push-events.v1"
    assert payload["dataset"]["description"] == "new table description"
    assert payload["columns"][0]["description"] == "repository name"
    assert payload["purpose"] == "track activity"
    assert payload["lineage"]["version"] == 1


def test_fetch_catalog_snapshot_with_selected_dataset() -> None:
    async def run() -> tuple[dict[str, Any], list[str]]:
        called_paths: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            called_paths.append(request.url.path)
            if request.url.path == "/api/catalog/datasets/github.watch-events.v1":
                return httpx.Response(
                    200,
                    json={
                        "success": True,
                        "data": {
                            "id": "github.watch-events.v1",
                            "domain": "github",
                            "name": "Watch Events",
                            "description": "watch dataset",
                        },
                    },
                )
            if request.url.path == "/api/catalog/datasets/github.watch-events.v1/columns":
                return httpx.Response(
                    200,
                    json={
                        "success": True,
                        "data": [
                            {
                                "dataset_id": "github.watch-events.v1",
                                "column_name": "repo_name",
                                "data_type": "text",
                                "description": "repo",
                                "is_pii": False,
                            }
                        ],
                    },
                )
            return httpx.Response(404, json={"success": False})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="http://example.com") as client:
            planner = Planner(_build_settings(), client, logging.getLogger("planner-test"))
            snapshot = await planner._fetch_catalog_snapshot(
                "req-2",
                dataset_id="github.watch-events.v1",
            )
            return snapshot, called_paths

    snapshot, called_paths = asyncio.run(run())
    assert snapshot["dataset"]["id"] == "github.watch-events.v1"
    assert called_paths == [
        "/api/catalog/datasets/github.watch-events.v1",
        "/api/catalog/datasets/github.watch-events.v1/columns",
    ]


def test_generate_plan_omits_invalid_lineage_string(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run() -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            planner = Planner(_build_settings(), client, logging.getLogger("planner-test"))

            async def fake_snapshot(request_id: str, *, dataset_id: str | None = None):
                return {
                    "dataset": {
                        "id": "github.push-events.v1",
                        "domain": "github",
                        "name": "Push Events",
                        "description": "old",
                        "lineage_json": "not-json",
                    },
                    "columns": [],
                }

            async def fake_draft(seed_text: str, snapshot):
                return PlanDraft(
                    table_description="new table description",
                    column_descriptions={},
                    usage_examples=["monthly trend"],
                    purpose="track activity",
                )

            monkeypatch.setattr(planner, "_fetch_catalog_snapshot", fake_snapshot)
            monkeypatch.setattr(planner, "_generate_draft", fake_draft)
            _dataset_id, payload = await planner.generate_plan("seed", "req-1")
            return payload

    payload = asyncio.run(run())
    assert "lineage" not in payload


def test_generate_draft_retries_with_compact_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> tuple[PlanDraft, list[tuple[int, int]]]:
        async with httpx.AsyncClient() as client:
            planner = Planner(_build_settings(), client, logging.getLogger("planner-test"))
            calls: list[tuple[int, int]] = []

            async def fake_request_draft(
                *,
                seed_text: str,
                prompt_snapshot: dict[str, Any],
                max_tokens: int,
            ) -> PlanDraft:
                calls.append((prompt_snapshot["summary"]["columns_in_prompt"], max_tokens))
                if len(calls) == 1:
                    raise TimeoutError("Request timed out or interrupted")
                return PlanDraft(
                    table_description="fallback description",
                    column_descriptions={},
                    usage_examples=["example"],
                    purpose="fallback purpose",
                )

            monkeypatch.setattr(planner, "_request_draft", fake_request_draft)
            snapshot = {
                "dataset": {"id": "d1", "domain": "github", "name": "events"},
                "columns": [{"column_name": f"col_{i}", "data_type": "text"} for i in range(100)],
            }
            draft = await planner._generate_draft(seed_text="seed", snapshot=snapshot)
            return draft, calls

    draft, calls = asyncio.run(run())
    assert draft.table_description == "fallback description"
    assert calls[0] == (80, 1024)
    assert calls[1] == (30, 512)
