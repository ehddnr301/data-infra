"""PostgreSQL → D1(SQLite) 타입 매핑."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID

# PostgreSQL → D1 타입 매핑
_INTEGER_TYPES = frozenset({"boolean", "integer", "bigint", "smallint", "serial", "bigserial"})


def pg_to_d1_type(pg_type: str) -> str:
    """PostgreSQL 타입을 D1(SQLite) 타입으로 변환한다."""
    normalized = pg_type.lower().strip()
    if normalized in _INTEGER_TYPES:
        return "INTEGER"
    return "TEXT"


def convert_value(value: Any, pg_type: str) -> Any:
    """Python 값을 D1 호환 형태로 변환한다."""
    if value is None:
        return None

    normalized = pg_type.lower().strip()

    if normalized == "boolean":
        return 1 if value else 0

    if normalized in ("integer", "bigint", "smallint", "serial", "bigserial"):
        return int(value)

    if normalized == "jsonb":
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    if normalized == "array":
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)):
            return json.dumps(list(value), ensure_ascii=False)
        return json.dumps(value, ensure_ascii=False)

    if normalized in ("timestamp with time zone", "timestamp without time zone"):
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    if normalized == "date":
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    if normalized == "uuid":
        if isinstance(value, UUID):
            return str(value)
        return str(value)

    return str(value)
