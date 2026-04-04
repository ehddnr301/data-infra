"""JSON 구조화 로깅 설정."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """로그 레코드를 JSON으로 포맷한다."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(*, json_log: bool = False, level: int = logging.INFO) -> None:
    """로깅을 설정한다."""
    root = logging.getLogger("pseudolab_etl")
    root.setLevel(level)

    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stderr)
    if json_log:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")
        )
    root.addHandler(handler)
