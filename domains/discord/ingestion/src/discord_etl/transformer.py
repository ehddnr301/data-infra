"""Discord 메시지 정규화 변환기.

JSONL 원본(Discord API 응답) → D1 discord_messages 행 변환.
027 스키마에 맞춰 카운트 기반 컬럼으로 평탄화한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def transform_message(raw: dict[str, Any], *, channel_name: str, batch_date: str) -> dict[str, Any]:
    """Discord API Message 객체 → discord_messages 행 dict."""
    author = raw.get("author", {})
    referenced = raw.get("referenced_message")
    mentions = raw.get("mentions", [])
    timestamp = raw.get("timestamp", "")
    edited = raw.get("edited_timestamp")

    return {
        "id": raw["id"],
        "channel_id": raw["channel_id"],
        "channel_name": channel_name,
        "author_id": author.get("id", ""),
        "author_username": author.get("username", ""),
        "content": raw.get("content", ""),
        "message_type": raw.get("type", 0),
        "referenced_message_id": referenced["id"] if referenced else None,
        "attachment_count": len(raw.get("attachments", [])),
        "embed_count": len(raw.get("embeds", [])),
        "reaction_count": len(raw.get("reactions", [])),
        "mention_count": len(mentions),
        "pinned": 1 if raw.get("pinned", False) else 0,
        "created_at": _normalize_timestamp(timestamp),
        "edited_at": _normalize_timestamp(edited) if edited else None,
        "batch_date": batch_date,
    }


def _normalize_timestamp(ts: str) -> str:
    """Discord 타임스탬프를 ISO 8601 UTC로 정규화."""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return ts
