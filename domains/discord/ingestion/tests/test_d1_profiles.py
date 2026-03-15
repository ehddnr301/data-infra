from __future__ import annotations

from unittest.mock import MagicMock, patch

from discord_etl.config import D1Config
from discord_etl.d1 import (
    D1InsertResult,
    get_missing_profile_count,
    list_missing_profile_targets,
    upsert_user_profiles_batch,
)
from discord_etl.models import DiscordUserProfile


def _d1_config() -> D1Config:
    return D1Config(database_id="db", account_id="acc", api_token="token")


class TestMissingProfileTargets:
    @patch("discord_etl.d1.query_rows")
    def test_get_missing_profile_count(self, mock_query: MagicMock) -> None:
        mock_query.return_value = [{"cnt": 3}]
        count = get_missing_profile_count(_d1_config())
        assert count == 3

    @patch("discord_etl.d1.query_rows")
    def test_list_missing_profile_targets(self, mock_query: MagicMock) -> None:
        mock_query.return_value = [
            {
                "user_id": "u1",
                "last_seen_at": "2026-03-12T00:00:00+00:00",
                "message_count": 12,
            },
            {
                "user_id": "u2",
                "last_seen_at": "2026-03-11T00:00:00+00:00",
                "message_count": 4,
            },
        ]

        targets = list_missing_profile_targets(100, _d1_config())
        assert len(targets) == 2
        assert targets[0].user_id == "u1"
        assert targets[0].message_count == 12


class TestUpsertProfiles:
    @patch("discord_etl.d1._d1_query")
    def test_upsert_user_profiles_batch(self, mock_query: MagicMock) -> None:
        profile = DiscordUserProfile(
            user_id="u1",
            username="tester",
            global_name="Tester",
            avatar=None,
            banner=None,
            accent_color=None,
            bio="",
            pronouns="",
            mutual_guild_count=1,
            mutual_friend_count=0,
            connected_account_count=0,
            source="users_profile_api",
            source_endpoint="/users/{id}/profile",
            fetched_at="2026-03-12T00:00:00+00:00",
            raw_payload='{"user":{"id":"u1"}}',
        )

        result: D1InsertResult = upsert_user_profiles_batch([profile], _d1_config())
        assert result.rows_inserted == 1
        assert result.batches_executed == 1
        assert result.errors == []
        mock_query.assert_called_once()
