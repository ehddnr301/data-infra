"""Discord API 클라이언트 테스트 (httpx mock)."""

from __future__ import annotations

import pytest
from discord_etl.client import DiscordApiError, DiscordClient
from discord_etl.config import DiscordApiConfig


@pytest.fixture()
def api_config() -> DiscordApiConfig:
    return DiscordApiConfig(
        limit=50,
        max_retries=1,
        backoff_factor=0.01,
        delay_sec=0,
    )


class TestFetchMessages:
    """fetch_messages 테스트."""

    def test_success(
        self,
        httpx_mock,
        api_config: DiscordApiConfig,
        sample_discord_message: dict,
    ) -> None:
        httpx_mock.add_response(json=[sample_discord_message])

        client = DiscordClient(api_config, token="test-token")
        result = client.fetch_messages("944039671707607060")

        assert len(result) == 1
        assert result[0]["id"] == "1234567890123456789"

    def test_with_before_param(
        self,
        httpx_mock,
        api_config: DiscordApiConfig,
        sample_discord_message: dict,
    ) -> None:
        httpx_mock.add_response(json=[sample_discord_message])

        client = DiscordClient(api_config, token="test-token")
        result = client.fetch_messages(
            "944039671707607060",
            before="9999999999999999999",
        )

        assert len(result) == 1
        request = httpx_mock.get_request()
        assert "before=9999999999999999999" in str(request.url)

    def test_empty_response(
        self,
        httpx_mock,
        api_config: DiscordApiConfig,
    ) -> None:
        httpx_mock.add_response(json=[])

        client = DiscordClient(api_config, token="test-token")
        result = client.fetch_messages("944039671707607060")

        assert result == []

    def test_rate_limit_retry(
        self,
        httpx_mock,
        api_config: DiscordApiConfig,
        sample_discord_message: dict,
    ) -> None:
        httpx_mock.add_response(
            status_code=429,
            json={"retry_after": 0.01, "message": "rate limited"},
        )
        httpx_mock.add_response(json=[sample_discord_message])

        client = DiscordClient(api_config, token="test-token")
        result = client.fetch_messages("944039671707607060")

        assert len(result) == 1

    def test_forbidden_error(
        self,
        httpx_mock,
        api_config: DiscordApiConfig,
    ) -> None:
        httpx_mock.add_response(
            status_code=403,
            json={"message": "Missing Access"},
        )

        client = DiscordClient(api_config, token="test-token")

        with pytest.raises(DiscordApiError) as exc_info:
            client.fetch_messages("000000000000000000")
        assert exc_info.value.status_code == 403

    def test_not_found_error(
        self,
        httpx_mock,
        api_config: DiscordApiConfig,
    ) -> None:
        httpx_mock.add_response(
            status_code=404,
            json={"message": "Unknown Channel"},
        )

        client = DiscordClient(api_config, token="test-token")

        with pytest.raises(DiscordApiError) as exc_info:
            client.fetch_messages("000000000000000000")
        assert exc_info.value.status_code == 404

    def test_server_error_retry(
        self,
        httpx_mock,
        api_config: DiscordApiConfig,
        sample_discord_message: dict,
    ) -> None:
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(json=[sample_discord_message])

        client = DiscordClient(api_config, token="test-token")
        result = client.fetch_messages("944039671707607060")

        assert len(result) == 1

    def test_server_error_exhausted(
        self,
        httpx_mock,
        api_config: DiscordApiConfig,
    ) -> None:
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=500)

        client = DiscordClient(api_config, token="test-token")

        with pytest.raises(DiscordApiError) as exc_info:
            client.fetch_messages("944039671707607060")
        assert exc_info.value.status_code == 500


class TestClientInit:
    """클라이언트 초기화 테스트."""

    def test_missing_token(
        self, api_config: DiscordApiConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DISCORD_USER_TOKEN", raising=False)

        with pytest.raises(RuntimeError, match="DISCORD_USER_TOKEN"):
            DiscordClient(api_config)

    def test_token_from_env(
        self,
        api_config: DiscordApiConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("DISCORD_USER_TOKEN", "env-token")

        client = DiscordClient(api_config)
        assert client._token == "env-token"


class TestFetchUserProfile:
    def test_success(self, httpx_mock, api_config: DiscordApiConfig) -> None:
        payload = {
            "user": {"id": "111", "username": "tester"},
            "user_profile": {"bio": ""},
        }
        httpx_mock.add_response(json=payload)

        client = DiscordClient(api_config, token="test-token")
        result = client.fetch_user_profile("111", "944032730050621450")

        assert result["user"]["id"] == "111"
        request = httpx_mock.get_request()
        assert "with_mutual_guilds=true" in str(request.url)
        assert "guild_id=944032730050621450" in str(request.url)

    def test_unauthorized(self, httpx_mock, api_config: DiscordApiConfig) -> None:
        httpx_mock.add_response(status_code=401, json={"message": "Unauthorized"})

        client = DiscordClient(api_config, token="test-token")
        with pytest.raises(DiscordApiError) as exc_info:
            client.fetch_user_profile("111", "944032730050621450")

        assert exc_info.value.status_code == 401

    def test_forbidden(self, httpx_mock, api_config: DiscordApiConfig) -> None:
        httpx_mock.add_response(status_code=403, json={"message": "Forbidden"})

        client = DiscordClient(api_config, token="test-token")
        with pytest.raises(DiscordApiError) as exc_info:
            client.fetch_user_profile("111", "944032730050621450")

        assert exc_info.value.status_code == 403

    def test_not_found(self, httpx_mock, api_config: DiscordApiConfig) -> None:
        httpx_mock.add_response(status_code=404, json={"message": "Unknown User"})

        client = DiscordClient(api_config, token="test-token")
        with pytest.raises(DiscordApiError) as exc_info:
            client.fetch_user_profile("111", "944032730050621450")

        assert exc_info.value.status_code == 404

    def test_rate_limit_retry(self, httpx_mock, api_config: DiscordApiConfig) -> None:
        httpx_mock.add_response(status_code=429, json={"retry_after": 0.01})
        httpx_mock.add_response(json={"user": {"id": "111"}})

        client = DiscordClient(api_config, token="test-token")
        result = client.fetch_user_profile("111", "944032730050621450")

        assert result["user"]["id"] == "111"

    def test_rate_limit_retry_uses_retry_after_header(
        self, httpx_mock, api_config: DiscordApiConfig
    ) -> None:
        httpx_mock.add_response(
            status_code=429,
            text="<html>Access denied</html>",
            headers={"retry-after": "0.01"},
        )
        httpx_mock.add_response(json={"user": {"id": "111"}})

        client = DiscordClient(api_config, token="test-token")
        result = client.fetch_user_profile("111", "944032730050621450")

        assert result["user"]["id"] == "111"

    def test_profile_specific_retry_limit(self, httpx_mock, api_config: DiscordApiConfig) -> None:
        httpx_mock.add_response(status_code=500)

        client = DiscordClient(api_config, token="test-token")
        with pytest.raises(DiscordApiError) as exc_info:
            client.fetch_user_profile("111", "944032730050621450", max_retries=0)

        assert exc_info.value.status_code == 500

    def test_rate_limit_exhausted_returns_429(
        self, httpx_mock, api_config: DiscordApiConfig
    ) -> None:
        httpx_mock.add_response(status_code=429, json={"retry_after": 0.01})
        httpx_mock.add_response(status_code=429, json={"retry_after": 0.01})

        client = DiscordClient(api_config, token="test-token")
        with pytest.raises(DiscordApiError) as exc_info:
            client.fetch_user_profile("111", "944032730050621450", max_retries=1)

        assert exc_info.value.status_code == 429
