from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from threading import Lock
from typing import Any, Literal


@dataclass
class PlanRecord:
    plan_id: str
    created_at: float
    expires_at: float
    status: Literal["pending", "approved", "rejected", "expired"]
    request_id: str
    slack_user_id: str
    slack_channel_id: str
    dataset_id: str
    payload: dict[str, Any]
    message_ts: str | None = None


class PlanStore:
    def __init__(self, approval_ttl_seconds: int) -> None:
        self._ttl_seconds = approval_ttl_seconds
        self._items: dict[str, PlanRecord] = {}
        self._lock = Lock()

    def create(
        self,
        *,
        request_id: str,
        slack_user_id: str,
        slack_channel_id: str,
        dataset_id: str,
        payload: dict[str, Any],
    ) -> PlanRecord:
        now = time.time()
        plan_id = uuid.uuid4().hex[:12]
        record = PlanRecord(
            plan_id=plan_id,
            created_at=now,
            expires_at=now + self._ttl_seconds,
            status="pending",
            request_id=request_id,
            slack_user_id=slack_user_id,
            slack_channel_id=slack_channel_id,
            dataset_id=dataset_id,
            payload=payload,
        )
        with self._lock:
            self._items[plan_id] = record
        return record

    def get(self, plan_id: str) -> PlanRecord | None:
        with self._lock:
            record = self._items.get(plan_id)
            if record is None:
                return None
            if record.status == "pending" and time.time() > record.expires_at:
                record.status = "expired"
            return record

    def set_message_ts(self, plan_id: str, message_ts: str) -> None:
        with self._lock:
            record = self._items.get(plan_id)
            if record is not None:
                record.message_ts = message_ts

    def mark(self, plan_id: str, status: Literal["approved", "rejected", "expired"]) -> None:
        with self._lock:
            record = self._items.get(plan_id)
            if record is not None:
                record.status = status

    def cleanup_expired(self) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            for plan_id in list(self._items.keys()):
                record = self._items[plan_id]
                if record.status in {"approved", "rejected", "expired"} and now > record.expires_at:
                    self._items.pop(plan_id, None)
                    removed += 1
                elif record.status == "pending" and now > record.expires_at:
                    record.status = "expired"
        return removed

    def backlog_size(self) -> int:
        with self._lock:
            return sum(1 for item in self._items.values() if item.status == "pending")
