from __future__ import annotations

import asyncio
import os

import httpx
import pytest
from app import Runtime, app
from config import load_settings


def _set_required_env() -> None:
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
    os.environ["SLACK_SIGNING_SECRET"] = "secret"
    os.environ["SLACK_CHANNEL_ID"] = "C123"
    os.environ["ANTHROPIC_API_KEY"] = "test"
    os.environ["CATALOG_API_BASE_URL"] = "http://127.0.0.1:8787"
    os.environ["CATALOG_INTERNAL_BEARER"] = "token"


async def _request(path: str) -> httpx.Response:
    runtime = Runtime(load_settings())
    app.state.runtime = runtime
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path)
    finally:
        await runtime.close()


def test_health_endpoint_contract() -> None:
    _set_required_env()
    response = asyncio.run(_request("/health"))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["timestamp"], str)
    assert isinstance(body["uptime_s"], int)
    assert isinstance(body["version"], str)


def test_readiness_endpoint_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env()
    async def fake_readiness_checks(self: Runtime) -> dict[str, dict[str, str]]:
        return {
            "config": {"status": "ok"},
            "slack_api": {"status": "fail"},
            "catalog_api": {"status": "ok"},
            "plan_store": {"status": "ok"},
        }

    monkeypatch.setattr(Runtime, "readiness_checks", fake_readiness_checks)
    response = asyncio.run(_request("/health/ready"))
    assert response.status_code in {200, 503}
    body = response.json()
    assert body["status"] in {"ready", "degraded", "unhealthy"}
    assert set(body["checks"].keys()) == {"config", "slack_api", "catalog_api", "plan_store"}
