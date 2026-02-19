"""JSON 구조화 로깅 설정."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """JSON 형태로 로그 레코드를 포매팅한다."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in (
            "event_code", "channel_id", "duration_ms",
            "count", "retry_after",
        ):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(*, json_format: bool = True, level: int = logging.INFO) -> None:
    """discord_etl 로거에 포매터를 설정한다."""
    root = logging.getLogger("discord_etl")
    root.setLevel(level)
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        JsonFormatter() if json_format
        else logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
