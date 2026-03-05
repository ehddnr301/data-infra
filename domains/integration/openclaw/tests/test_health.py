from __future__ import annotations

import os

from app import app
from fastapi.testclient import TestClient


def _set_required_env() -> None:
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
    os.environ["SLACK_SIGNING_SECRET"] = "secret"
    os.environ["SLACK_CHANNEL_ID"] = "C123"
    os.environ["ANTHROPIC_API_KEY"] = "test"
    os.environ["CATALOG_API_BASE_URL"] = "http://127.0.0.1:8787"
    os.environ["CATALOG_INTERNAL_BEARER"] = "token"


def test_health_endpoint_contract() -> None:
    _set_required_env()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert isinstance(body["timestamp"], str)
        assert isinstance(body["uptime_s"], int)
        assert isinstance(body["version"], str)


def test_readiness_endpoint_contract() -> None:
    _set_required_env()
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code in {200, 503}
        body = response.json()
        assert body["status"] in {"ready", "degraded", "unhealthy"}
        assert set(body["checks"].keys()) == {"config", "slack_api", "catalog_api", "plan_store"}
