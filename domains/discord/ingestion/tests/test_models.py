"""DiscordMessage 모델 테스트."""

from __future__ import annotations

from discord_etl.models import (
    DISCORD_MESSAGES_COLUMNS,
    DiscordMessage,
)


class TestFromApiResponse:
    """from_api_response 변환 테스트."""

    def test_normal_message(self, sample_discord_message: dict) -> None:
        msg = DiscordMessage.from_api_response(
            sample_discord_message, channel_name="공지사항", batch_date="2024-06-15",
        )

        assert msg.id == "1234567890123456789"
        assert msg.channel_id == "944039671707607060"
        assert msg.channel_name == "공지사항"
        assert msg.author_id == "111222333444555666"
        assert msg.author_username == "testuser"
        assert msg.content == "안녕하세요!"
        assert msg.message_type == 0
        assert msg.referenced_message_id is None
        assert msg.mention_count == 0
        assert msg.pinned is False
        assert msg.attachment_count == 0
        assert msg.embed_count == 0
        assert msg.reaction_count == 0
        assert msg.batch_date == "2024-06-15"
        assert "2024-06-15" in msg.created_at

    def test_reply_message(self, sample_reply_message: dict) -> None:
        msg = DiscordMessage.from_api_response(sample_reply_message)

        assert msg.id == "1234567890123456790"
        assert msg.message_type == 19
        assert msg.referenced_message_id == "1234567890123456789"

    def test_message_with_mentions(self, sample_discord_message: dict) -> None:
        sample_discord_message["mentions"] = [
            {"id": "111", "username": "user1"},
            {"id": "222", "username": "user2"},
        ]
        msg = DiscordMessage.from_api_response(sample_discord_message)

        assert msg.mention_count == 2

    def test_missing_author(self, sample_discord_message: dict) -> None:
        del sample_discord_message["author"]
        msg = DiscordMessage.from_api_response(sample_discord_message)

        assert msg.author_id == ""
        assert msg.author_username == ""

    def test_attachment_embed_reaction_counts(self, sample_discord_message: dict) -> None:
        sample_discord_message["attachments"] = [{"url": "https://example.com/file.png"}]
        sample_discord_message["embeds"] = [{"type": "rich"}, {"type": "image"}]
        sample_discord_message["reactions"] = [{"emoji": {"name": "👍"}, "count": 3}]
        msg = DiscordMessage.from_api_response(sample_discord_message)

        assert msg.attachment_count == 1
        assert msg.embed_count == 2
        assert msg.reaction_count == 1

    def test_edited_at_conversion(self, sample_discord_message: dict) -> None:
        sample_discord_message["edited_timestamp"] = "2024-06-15T11:00:00.000000+00:00"
        msg = DiscordMessage.from_api_response(sample_discord_message)

        assert msg.edited_at is not None
        assert "2024-06-15" in msg.edited_at


class TestToD1Row:
    """to_d1_row 변환 테스트."""

    def test_d1_row_keys(self, sample_discord_message: dict) -> None:
        msg = DiscordMessage.from_api_response(
            sample_discord_message, channel_name="테스트", batch_date="2024-06-15",
        )
        row = msg.to_d1_row()

        for col in DISCORD_MESSAGES_COLUMNS:
            assert col in row, f"Missing column: {col}"

    def test_d1_row_values(self, sample_discord_message: dict) -> None:
        msg = DiscordMessage.from_api_response(
            sample_discord_message, channel_name="테스트", batch_date="2024-06-15",
        )
        row = msg.to_d1_row()

        assert row["id"] == "1234567890123456789"
        assert row["channel_name"] == "테스트"
        assert row["pinned"] == 0  # bool -> int 변환
        assert row["attachment_count"] == 0
        assert row["embed_count"] == 0
        assert row["reaction_count"] == 0
        assert row["batch_date"] == "2024-06-15"
        assert isinstance(row["created_at"], str)

    def test_d1_row_pinned_true(self, sample_discord_message: dict) -> None:
        sample_discord_message["pinned"] = True
        msg = DiscordMessage.from_api_response(sample_discord_message)
        row = msg.to_d1_row()

        assert row["pinned"] == 1

    def test_d1_row_count_fields(self, sample_discord_message: dict) -> None:
        sample_discord_message["attachments"] = [{"url": "https://example.com/file.png"}]
        sample_discord_message["embeds"] = [{"type": "rich"}]
        sample_discord_message["reactions"] = [{"emoji": {"name": "👍"}, "count": 3}]
        msg = DiscordMessage.from_api_response(sample_discord_message)
        row = msg.to_d1_row()

        assert row["attachment_count"] == 1
        assert row["embed_count"] == 1
        assert row["reaction_count"] == 1
