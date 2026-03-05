from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from config import Settings, load_settings
from fastapi import FastAPI
from health import router as health_router
from logging_config import setup_logging
from store import PlanStore
from webhook import router as webhook_router


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = setup_logging()
        self.http_client = httpx.AsyncClient()
        self.plan_store = PlanStore(settings.approval_ttl_seconds)
        self.started_at = time.time()

    async def close(self) -> None:
        await self.http_client.aclose()

    async def readiness_checks(self) -> dict[str, dict[str, Any]]:
        config_check = "ok"

        slack_check = "ok"
        try:
            response = await self.http_client.post(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {self.settings.slack_bot_token}"},
                timeout=5.0,
            )
            if response.status_code >= 400 or not response.json().get("ok"):
                slack_check = "fail"
        except Exception:
            slack_check = "fail"

        catalog_check = "ok"
        try:
            base_url = str(self.settings.catalog_api_base_url).rstrip("/")
            response = await self.http_client.get(f"{base_url}/api/health", timeout=5.0)
            if response.status_code >= 400:
                catalog_check = "fail"
        except Exception:
            catalog_check = "fail"

        plan_store_check = "ok" if self.plan_store.backlog_size() < 100 else "fail"

        return {
            "config": {"status": config_check},
            "slack_api": {"status": slack_check},
            "catalog_api": {"status": catalog_check},
            "plan_store": {"status": plan_store_check},
        }


@asynccontextmanager
async def lifespan(app_: FastAPI):
    settings = load_settings()
    runtime = Runtime(settings)
    app_.state.runtime = runtime
    try:
        yield
    finally:
        await runtime.close()


app = FastAPI(title="OpenClaw", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(webhook_router)
