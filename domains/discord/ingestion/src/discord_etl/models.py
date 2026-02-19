"""Discord 메시지 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel


class DiscordMessage(BaseModel):
    """Discord 메시지 모델.

    Discord REST API 응답의 Message 객체를 정규화한다.
    027 스키마: attachment/embed/reaction은 count만 저장.
    """

    id: str                                    # snowflake ID (PRIMARY KEY)
    channel_id: str
    channel_name: str = ""                     # 채널명 (수집 시 주입)
    author_id: str
    author_username: str
    content: str                               # 메시지 본문 전체 저장
    message_type: int = 0                      # 0=default, 19=reply 등
    referenced_message_id: str | None = None   # 답글 대상
    attachment_count: int = 0
    embed_count: int = 0
    reaction_count: int = 0
    mention_count: int = 0
    pinned: bool = False
    created_at: str = ""                       # ISO 8601 문자열
    edited_at: str | None = None
    batch_date: str = ""                       # YYYY-MM-DD

    @classmethod
    def from_api_response(cls, raw: dict, *, channel_name: str = "", batch_date: str = "") -> DiscordMessage:
        """Discord API 응답 dict -> DiscordMessage 변환.

        API 응답의 중첩 구조를 평탄화한다.
        """
        author = raw.get("author", {})
        referenced = raw.get("referenced_message")
        mentions = raw.get("mentions", [])

        timestamp_raw = raw.get("timestamp", "")
        edited_raw = raw.get("edited_timestamp")

        return cls(
            id=raw["id"],
            channel_id=raw["channel_id"],
            channel_name=channel_name,
            author_id=author.get("id", ""),
            author_username=author.get("username", ""),
            content=raw.get("content", ""),
            message_type=raw.get("type", 0),
            referenced_message_id=referenced["id"] if referenced else None,
            attachment_count=len(raw.get("attachments", [])),
            embed_count=len(raw.get("embeds", [])),
            reaction_count=len(raw.get("reactions", [])),
            mention_count=len(mentions),
            pinned=raw.get("pinned", False),
            created_at=str(timestamp_raw),
            edited_at=str(edited_raw) if edited_raw else None,
            batch_date=batch_date,
        )

    def to_d1_row(self) -> dict:
        """D1 INSERT용 dict 변환."""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "author_id": self.author_id,
            "author_username": self.author_username,
            "content": self.content,
            "message_type": self.message_type,
            "referenced_message_id": self.referenced_message_id,
            "attachment_count": self.attachment_count,
            "embed_count": self.embed_count,
            "reaction_count": self.reaction_count,
            "mention_count": self.mention_count,
            "pinned": 1 if self.pinned else 0,
            "created_at": self.created_at,
            "edited_at": self.edited_at,
            "batch_date": self.batch_date,
        }


# D1 테이블 정의
DISCORD_MESSAGES_TABLE = "discord_messages"
DISCORD_MESSAGES_COLUMNS = [
    "id", "channel_id", "channel_name", "author_id", "author_username",
    "content", "message_type", "referenced_message_id",
    "attachment_count", "embed_count", "reaction_count",
    "mention_count", "pinned", "created_at", "edited_at", "batch_date",
]

DISCORD_WATERMARKS_TABLE = "discord_watermarks"
