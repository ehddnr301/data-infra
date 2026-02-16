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

        # extra 필드 병합 (event_code, date, hour, duration_ms, counts 등)
        for key in ("event_code", "date", "hour", "duration_ms", "counts", "failed_hours"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(*, json_format: bool = True, level: int = logging.INFO) -> None:
    """루트 로거에 JSON 포매터를 설정한다.

    Args:
        json_format: True이면 JSON 포맷, False이면 기본 포맷
        level: 로그 레벨
    """
    root = logging.getLogger("gharchive_etl")
    root.setLevel(level)

    # 기존 핸들러 제거 (중복 방지)
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(level)

    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root.addHandler(handler)
