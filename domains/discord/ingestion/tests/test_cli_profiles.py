from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from discord_etl.cli import main
from discord_etl.client import DiscordApiError
from discord_etl.config import (
    AppConfig,
    ChannelConfig,
    D1Config,
    DiscordApiConfig,
    ProfileEnrichmentConfig,
)
from discord_etl.d1 import D1InsertResult
from discord_etl.models import ProfileTarget


def _config(enabled: bool = True) -> AppConfig:
    return AppConfig(
        discord=DiscordApiConfig(),
        channels=[ChannelConfig(name="test", id="123")],
        d1=D1Config(database_id="db", account_id="acc", api_token="token"),
        profile_enrichment=ProfileEnrichmentConfig(
            enabled=enabled,
            guild_id="944032730050621450",
            max_users_per_run=100,
        ),
    )


class TestVerifyProfileApiCommand:
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_verify_profile_api_success(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        tmp_config_file: Path,
    ) -> None:
        runner = CliRunner()
        mock_load_config.return_value = _config(enabled=True)
        mock_client = mock_client_cls.return_value
        mock_client.fetch_user_profile.return_value = {
            "user": {"id": "u1", "username": "tester", "global_name": "Tester"},
            "user_profile": {"bio": "", "pronouns": ""},
            "mutual_guilds": [],
            "connected_accounts": [],
        }

        result = runner.invoke(
            main,
            ["verify-profile-api", "--user-id", "u1", "--config", str(tmp_config_file)],
        )

        assert result.exit_code == 0
        assert "[OK]" in result.output
        mock_client.fetch_user_profile.assert_called_once_with(
            "u1",
            "944032730050621450",
            type="popout",
            with_mutual_guilds=True,
            with_mutual_friends=True,
            with_mutual_friends_count=False,
            request_timeout_sec=30,
            max_retries=3,
            extra_headers={},
        )


class TestEnrichProfilesCommand:
    @patch("discord_etl.cli.upsert_user_profiles_batch")
    @patch("discord_etl.cli.list_missing_profile_targets")
    @patch("discord_etl.cli.get_missing_profile_count")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_enrich_profiles_success(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_missing_count: MagicMock,
        mock_list_targets: MagicMock,
        mock_upsert: MagicMock,
        tmp_config_file: Path,
    ) -> None:
        runner = CliRunner()
        mock_load_config.return_value = _config(enabled=True)
        mock_missing_count.return_value = 1
        mock_list_targets.return_value = [
            ProfileTarget(user_id="u1", last_seen_at="2026-03-12T00:00:00+00:00", message_count=10),
        ]
        mock_client = mock_client_cls.return_value
        mock_client.fetch_user_profile.return_value = {
            "user": {"id": "u1", "username": "tester", "global_name": "Tester"},
            "user_profile": {"bio": "", "pronouns": ""},
            "mutual_guilds": [],
            "connected_accounts": [],
        }
        mock_upsert.return_value = D1InsertResult(total_rows=1, rows_inserted=1, batches_executed=1)

        result = runner.invoke(
            main,
            ["enrich-profiles", "--config", str(tmp_config_file)],
        )

        assert result.exit_code == 0
        assert "enrich-profiles summary" in result.output

    @patch("discord_etl.cli.load_config")
    def test_enrich_profiles_disabled(
        self, mock_load_config: MagicMock, tmp_config_file: Path
    ) -> None:
        runner = CliRunner()
        mock_load_config.return_value = _config(enabled=False)

        result = runner.invoke(
            main,
            ["enrich-profiles", "--config", str(tmp_config_file)],
        )

        assert result.exit_code == 0
        assert "disabled" in result.output

    @patch("discord_etl.cli.upsert_user_profiles_batch")
    @patch("discord_etl.cli.list_missing_profile_targets")
    @patch("discord_etl.cli.get_missing_profile_count")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_enrich_profiles_forbidden_is_skipped(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_missing_count: MagicMock,
        mock_list_targets: MagicMock,
        mock_upsert: MagicMock,
        tmp_config_file: Path,
    ) -> None:
        runner = CliRunner()
        mock_load_config.return_value = _config(enabled=True)
        mock_missing_count.return_value = 1
        mock_list_targets.return_value = [
            ProfileTarget(user_id="u1", last_seen_at="2026-03-12T00:00:00+00:00", message_count=10),
        ]
        mock_client = mock_client_cls.return_value
        mock_client.fetch_user_profile.side_effect = DiscordApiError(403, "forbidden")
        mock_upsert.return_value = D1InsertResult()

        result = runner.invoke(
            main,
            ["enrich-profiles", "--config", str(tmp_config_file)],
        )

        assert result.exit_code == 0
        assert "skipped_403=1" in result.output

    @patch("discord_etl.cli.upsert_user_profiles_batch")
    @patch("discord_etl.cli.list_missing_profile_targets")
    @patch("discord_etl.cli.get_missing_profile_count")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_enrich_profiles_stops_on_429(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_missing_count: MagicMock,
        mock_list_targets: MagicMock,
        mock_upsert: MagicMock,
        tmp_config_file: Path,
    ) -> None:
        runner = CliRunner()
        mock_load_config.return_value = _config(enabled=True)
        mock_missing_count.return_value = 1
        mock_list_targets.return_value = [
            ProfileTarget(user_id="u1", last_seen_at="2026-03-12T00:00:00+00:00", message_count=10),
        ]
        mock_client = mock_client_cls.return_value
        mock_client.fetch_user_profile.side_effect = DiscordApiError(429, "rate limited")
        mock_upsert.return_value = D1InsertResult()

        result = runner.invoke(
            main,
            ["enrich-profiles", "--config", str(tmp_config_file)],
        )

        assert result.exit_code == 1
        assert "throttled_429=1" in result.output

    @patch("discord_etl.cli.upsert_user_profiles_batch")
    @patch("discord_etl.cli.list_missing_profile_targets")
    @patch("discord_etl.cli.get_missing_profile_count")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_enrich_profiles_marks_not_found(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_missing_count: MagicMock,
        mock_list_targets: MagicMock,
        mock_upsert: MagicMock,
        tmp_config_file: Path,
    ) -> None:
        runner = CliRunner()
        mock_load_config.return_value = _config(enabled=True)
        mock_missing_count.return_value = 1
        mock_list_targets.return_value = [
            ProfileTarget(
                user_id="u404", last_seen_at="2026-03-12T00:00:00+00:00", message_count=1
            ),
        ]
        mock_client = mock_client_cls.return_value
        mock_client.fetch_user_profile.side_effect = DiscordApiError(404, "not found")
        mock_upsert.return_value = D1InsertResult(total_rows=1, rows_inserted=1, batches_executed=1)

        result = runner.invoke(
            main,
            ["enrich-profiles", "--config", str(tmp_config_file)],
        )

        assert result.exit_code == 0
        assert "not_found_marked=1" in result.output

    @patch("discord_etl.cli.upsert_user_profiles_batch")
    @patch("discord_etl.cli.list_missing_profile_targets")
    @patch("discord_etl.cli.get_missing_profile_count")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_enrich_profiles_passes_profile_retry_settings(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_missing_count: MagicMock,
        mock_list_targets: MagicMock,
        mock_upsert: MagicMock,
        tmp_config_file: Path,
    ) -> None:
        runner = CliRunner()
        mock_load_config.return_value = _config(enabled=True)
        mock_missing_count.return_value = 1
        mock_list_targets.return_value = [
            ProfileTarget(user_id="u1", last_seen_at="2026-03-12T00:00:00+00:00", message_count=10),
        ]
        mock_client = mock_client_cls.return_value
        mock_client.fetch_user_profile.return_value = {
            "user": {"id": "u1", "username": "tester", "global_name": "Tester"},
            "user_profile": {"bio": "", "pronouns": ""},
            "mutual_guilds": [],
            "connected_accounts": [],
        }
        mock_upsert.return_value = D1InsertResult(total_rows=1, rows_inserted=1, batches_executed=1)

        result = runner.invoke(
            main,
            ["enrich-profiles", "--config", str(tmp_config_file)],
        )

        assert result.exit_code == 0
        mock_client.fetch_user_profile.assert_called_once_with(
            "u1",
            "944032730050621450",
            type="popout",
            with_mutual_guilds=True,
            with_mutual_friends=True,
            with_mutual_friends_count=False,
            request_timeout_sec=30,
            max_retries=3,
            extra_headers={},
        )

    @patch("discord_etl.cli.upsert_user_profiles_batch")
    @patch("discord_etl.cli.list_missing_profile_targets")
    @patch("discord_etl.cli.get_missing_profile_count")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_backfill_profiles_safe_stops_on_401(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_missing_count: MagicMock,
        mock_list_targets: MagicMock,
        mock_upsert: MagicMock,
        tmp_config_file: Path,
    ) -> None:
        runner = CliRunner()
        mock_load_config.return_value = _config(enabled=True)
        mock_missing_count.return_value = 1
        mock_list_targets.return_value = [
            ProfileTarget(
                user_id="u401", last_seen_at="2026-03-12T00:00:00+00:00", message_count=1
            ),
        ]
        mock_client = mock_client_cls.return_value
        mock_client.fetch_user_profile.side_effect = DiscordApiError(401, "unauthorized")
        mock_upsert.return_value = D1InsertResult(total_rows=0, rows_inserted=0, batches_executed=0)

        result = runner.invoke(
            main,
            ["backfill-profiles-safe", "--config", str(tmp_config_file)],
        )

        assert result.exit_code == 1
        assert "auth/permission issue" in result.output

    @patch("discord_etl.cli.upsert_user_profiles_batch")
    @patch("discord_etl.cli.list_missing_profile_targets")
    @patch("discord_etl.cli.get_missing_profile_count")
    @patch("discord_etl.cli.DiscordClient")
    @patch("discord_etl.cli.load_config")
    def test_backfill_profiles_safe_aborts_on_consecutive_429(
        self,
        mock_load_config: MagicMock,
        mock_client_cls: MagicMock,
        mock_missing_count: MagicMock,
        mock_list_targets: MagicMock,
        mock_upsert: MagicMock,
        tmp_config_file: Path,
    ) -> None:
        runner = CliRunner()
        config = _config(enabled=True)
        config.profile_enrichment.max_consecutive_429 = 1
        config.profile_enrichment.cooldown_on_429_sec = 1
        mock_load_config.return_value = config
        mock_missing_count.return_value = 1
        mock_list_targets.return_value = [
            ProfileTarget(
                user_id="u429", last_seen_at="2026-03-12T00:00:00+00:00", message_count=1
            ),
        ]
        mock_client = mock_client_cls.return_value
        mock_client.fetch_user_profile.side_effect = DiscordApiError(429, "rate limited")
        mock_upsert.return_value = D1InsertResult()

        result = runner.invoke(
            main,
            ["backfill-profiles-safe", "--config", str(tmp_config_file)],
        )

        assert result.exit_code == 1
        assert "too many consecutive 429" in result.output
