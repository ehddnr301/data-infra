"""transformer 변환 테스트."""

from __future__ import annotations

from typing import Any

from discord_etl.transformer import _normalize_timestamp, transform_message

CHANNEL_NAME = "test-channel"
BATCH_DATE = "2024-06-15"


class TestTransformBasicMessage:
    """기본 메시지 변환 테스트."""

    def test_transform_basic_message(self, sample_discord_message: dict[str, Any]) -> None:
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["id"] == "1234567890123456789"
        assert row["channel_id"] == "944039671707607060"
        assert row["channel_name"] == CHANNEL_NAME
        assert row["author_id"] == "111222333444555666"
        assert row["author_username"] == "testuser"
        assert row["content"] == "안녕하세요!"
        assert row["message_type"] == 0
        assert row["referenced_message_id"] is None
        assert row["batch_date"] == BATCH_DATE

    def test_transform_reply_message(self, sample_reply_message: dict[str, Any]) -> None:
        row = transform_message(
            sample_reply_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["message_type"] == 19
        assert row["referenced_message_id"] == "1234567890123456789"

    def test_transform_empty_content(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["content"] = ""
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["content"] == ""

    def test_transform_missing_content(self, sample_discord_message: dict[str, Any]) -> None:
        del sample_discord_message["content"]
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["content"] == ""


class TestTransformTimestamp:
    """타임스탬프 정규화 테스트."""

    def test_transform_timestamp_normalization(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["timestamp"] = "2024-06-15T10:30:00.000000+00:00"
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["created_at"] == "2024-06-15T10:30:00Z"

    def test_transform_timestamp_with_offset(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["timestamp"] = "2024-06-15T19:30:00+09:00"
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["created_at"] == "2024-06-15T10:30:00Z"

    def test_transform_edited_at(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["edited_timestamp"] = "2024-06-15T11:00:00+00:00"
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["edited_at"] == "2024-06-15T11:00:00Z"

    def test_transform_edited_at_none(self, sample_discord_message: dict[str, Any]) -> None:
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["edited_at"] is None


class TestTransformMissingFields:
    """필드 누락 시 기본값 테스트."""

    def test_transform_missing_author(self, sample_discord_message: dict[str, Any]) -> None:
        del sample_discord_message["author"]
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["author_id"] == ""
        assert row["author_username"] == ""

    def test_transform_missing_mentions(self, sample_discord_message: dict[str, Any]) -> None:
        del sample_discord_message["mentions"]
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["mention_count"] == 0

    def test_transform_missing_attachments(self, sample_discord_message: dict[str, Any]) -> None:
        del sample_discord_message["attachments"]
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["attachment_count"] == 0


class TestTransformPinned:
    """pinned 플래그 변환 테스트."""

    def test_transform_pinned_true(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["pinned"] = True
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["pinned"] == 1

    def test_transform_pinned_false(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["pinned"] = False
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["pinned"] == 0


class TestTransformCounts:
    """카운트 컬럼 변환 테스트."""

    def test_transform_attachment_count(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["attachments"] = [
            {"url": "https://example.com/a.png"},
            {"url": "https://example.com/b.png"},
        ]
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["attachment_count"] == 2

    def test_transform_embed_count(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["embeds"] = [{"title": "embed1"}, {"title": "embed2"}]
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["embed_count"] == 2

    def test_transform_reaction_count(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["reactions"] = [
            {"emoji": {"name": "👍"}, "count": 3},
        ]
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["reaction_count"] == 1

    def test_transform_mention_count(self, sample_discord_message: dict[str, Any]) -> None:
        sample_discord_message["mentions"] = [
            {"id": "111", "username": "user1"},
            {"id": "222", "username": "user2"},
            {"id": "333", "username": "user3"},
        ]
        row = transform_message(
            sample_discord_message, channel_name=CHANNEL_NAME, batch_date=BATCH_DATE,
        )

        assert row["mention_count"] == 3


class TestNormalizeTimestamp:
    """_normalize_timestamp 단위 테스트."""

    def test_utc_timestamp(self) -> None:
        result = _normalize_timestamp("2024-06-15T10:30:00+00:00")
        assert result == "2024-06-15T10:30:00Z"

    def test_offset_timestamp(self) -> None:
        result = _normalize_timestamp("2024-06-15T19:30:00+09:00")
        assert result == "2024-06-15T10:30:00Z"

    def test_invalid_timestamp(self) -> None:
        result = _normalize_timestamp("not-a-timestamp")
        assert result == "not-a-timestamp"

    def test_empty_timestamp(self) -> None:
        result = _normalize_timestamp("")
        assert result == ""
