from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    uptime_s = int(time.time() - runtime.started_at)
    return {
        "status": "ok",
        "timestamp": _iso_now(),
        "uptime_s": uptime_s,
        "version": runtime.settings.app_version,
    }


@router.get("/health/ready")
async def readiness(request: Request) -> JSONResponse:
    runtime = request.app.state.runtime
    checks = await runtime.readiness_checks()
    failed = sum(1 for check in checks.values() if check["status"] == "fail")

    status = "ready"
    if failed == len(checks):
        status = "unhealthy"
    elif failed > 0:
        status = "degraded"

    code = 503 if status == "unhealthy" else 200
    body = {
        "status": status,
        "checks": checks,
        "timestamp": _iso_now(),
    }
    return JSONResponse(content=body, status_code=code)
