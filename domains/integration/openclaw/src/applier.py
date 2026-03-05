from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

import httpx
from config import Settings
from store import PlanRecord


def is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def backoff_seconds(attempt: int, base_ms: int) -> float:
    base = (base_ms / 1000.0) * (2**attempt)
    jitter = random.uniform(0, 0.2 * base)
    return base + jitter


class CatalogApplier:
    def __init__(
        self, settings: Settings, http_client: httpx.AsyncClient, logger: logging.Logger
    ) -> None:
        self._settings = settings
        self._http = http_client
        self._logger = logger

    async def apply_plan(self, record: PlanRecord) -> dict[str, Any]:
        if self._settings.run_mode == "dry-run" or not self._settings.write_enabled:
            self._logger.info(
                "apply blocked by dry-run guard",
                extra={
                    "event_code": "OCW0201",
                    "request_id": record.request_id,
                    "plan_id": record.plan_id,
                    "run_mode": self._settings.run_mode,
                    "write_enabled": self._settings.write_enabled,
                    "result": "degraded",
                    "approval_state": "blocked",
                },
            )
            return {"status": "blocked", "reason": "dry_run_mode"}

        start = time.perf_counter()
        base_url = str(self._settings.catalog_api_base_url).rstrip("/")
        url = f"{base_url}/api/catalog/datasets/{record.dataset_id}/snapshot"
        headers = {
            "Authorization": f"Bearer {self._settings.catalog_internal_bearer}",
            "Content-Type": "application/json",
        }

        last_status: int | None = None
        last_detail: str | None = None

        for attempt in range(self._settings.max_retry_attempts + 1):
            try:
                response = await self._http.put(
                    url, json=record.payload, headers=headers, timeout=10.0
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_detail = str(exc)
                if attempt >= self._settings.max_retry_attempts:
                    break
                wait = backoff_seconds(attempt, self._settings.retry_backoff_ms)
                self._logger.warning(
                    "retry scheduled after network failure",
                    extra={
                        "event_code": "OCW0301",
                        "request_id": record.request_id,
                        "plan_id": record.plan_id,
                        "retry_count": attempt + 1,
                        "failure_cause": last_detail,
                    },
                )
                await asyncio.sleep(wait)
                continue

            last_status = response.status_code
            if response.status_code < 400:
                latency_ms = int((time.perf_counter() - start) * 1000)
                self._logger.info(
                    "apply success",
                    extra={
                        "event_code": "OCW0203",
                        "request_id": record.request_id,
                        "plan_id": record.plan_id,
                        "latency_ms": latency_ms,
                        "result": "success",
                    },
                )
                return {
                    "status": "success",
                    "upstream_status": response.status_code,
                    "latency_ms": latency_ms,
                }

            if (
                is_retryable_status(response.status_code)
                and attempt < self._settings.max_retry_attempts
            ):
                wait = backoff_seconds(attempt, self._settings.retry_backoff_ms)
                self._logger.warning(
                    "retry scheduled after upstream failure",
                    extra={
                        "event_code": "OCW0301",
                        "request_id": record.request_id,
                        "plan_id": record.plan_id,
                        "retry_count": attempt + 1,
                        "upstream_status": response.status_code,
                    },
                )
                await asyncio.sleep(wait)
                continue

            last_detail = response.text
            break

        self._logger.error(
            "apply terminal failure",
            extra={
                "event_code": "OCW0901",
                "request_id": record.request_id,
                "plan_id": record.plan_id,
                "upstream_status": last_status,
                "failure_cause": last_detail,
                "result": "failed",
            },
        )
        return {
            "status": "failed",
            "upstream_status": last_status,
            "reason": last_detail or "unknown",
        }
