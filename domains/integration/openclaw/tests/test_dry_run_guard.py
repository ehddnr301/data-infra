from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx
from applier import CatalogApplier
from store import PlanRecord


@dataclass
class SettingsStub:
    run_mode: str = "dry-run"
    write_enabled: bool = False
    catalog_api_base_url: str = "http://example.com"
    catalog_internal_bearer: str = "token"
    max_retry_attempts: int = 3
    retry_backoff_ms: int = 1000


def test_apply_blocked_in_dry_run() -> None:
    async def run() -> dict[str, str]:
        settings = SettingsStub()
        async with httpx.AsyncClient() as client:
            applier = CatalogApplier(
                settings=settings,
                http_client=client,
                logger=__import__("logging").getLogger("t"),
            )
            plan = PlanRecord(
                plan_id="plan-1",
                created_at=0,
                expires_at=999999,
                status="pending",
                request_id="req-1",
                slack_user_id="U1",
                slack_channel_id="C1",
                dataset_id="github.push-events.v1",
                payload={"dataset": {"id": "github.push-events.v1"}, "columns": []},
            )
            return await applier.apply_plan(plan)

    result = asyncio.run(run())
    assert result["status"] == "blocked"
    assert result["reason"] == "dry_run_mode"
