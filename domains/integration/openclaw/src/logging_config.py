from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

LOG_EXTRA_KEYS = (
    "event_code",
    "request_id",
    "plan_id",
    "slack_user_id",
    "slack_channel_id",
    "run_mode",
    "write_enabled",
    "approval_state",
    "latency_ms",
    "retry_count",
    "result",
    "failure_code",
    "failure_cause",
    "upstream_status",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": "clawbot",
            "message": record.getMessage(),
        }
        for key in LOG_EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                entry[key] = value
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("openclaw")
    logger.setLevel(level)
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger
