"""Discord REST API 클라이언트.

User Token 인증으로 채널 메시지를 조회한다.
- httpx 기반 HTTP 클라이언트
- Rate limit (429) 자동 대기
- Exponential backoff 재시도
"""

from __future__ import annotations

import logging
import os
import random
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from discord_etl.config import DiscordApiConfig

logger = logging.getLogger(__name__)


class DiscordApiError(Exception):
    """Discord API 호출 실패."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Discord API error {status_code}: {message}")


class DiscordClient:
    """Discord REST API 클라이언트."""

    def __init__(self, config: DiscordApiConfig, token: str | None = None):
        self._config = config
        self._token = token or os.environ.get("DISCORD_USER_TOKEN", "")
        if not self._token:
            raise RuntimeError("DISCORD_USER_TOKEN 환경변수가 설정되지 않았습니다.")
        self._base_url = config.api_base.rstrip("/")
        self._request_timeout = 30.0
        self._headers = {
            "Authorization": self._token,
            "Content-Type": "application/json",
        }

    def fetch_messages(
        self,
        channel_id: str,
        *,
        before: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """채널 메시지를 조회한다.

        Args:
            channel_id: 대상 채널 snowflake ID
            before: 이 ID 이전의 메시지를 조회 (pagination cursor)
            limit: 조회 건수 (기본값: config.limit)

        Returns:
            Message 객체 배열 (최신->오래된 순)

        Raises:
            DiscordApiError: API 에러 (재시도 실패 후)
        """
        url = f"{self._base_url}/channels/{channel_id}/messages"
        params: dict[str, str | int] = {"limit": limit or self._config.limit}
        if before:
            params["before"] = before

        response = self._request_json(url, params=params, context={"channel_id": channel_id})
        if isinstance(response, list):
            return response
        raise DiscordApiError(0, "Unexpected response payload type for channel messages")

    def fetch_user_profile(
        self,
        user_id: str,
        guild_id: str,
        *,
        type: str = "popout",
        with_mutual_guilds: bool = True,
        with_mutual_friends: bool = True,
        with_mutual_friends_count: bool = False,
        request_timeout_sec: int | None = None,
        max_retries: int | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict:
        url = f"{self._base_url}/users/{user_id}/profile"
        params: dict[str, str | int] = {
            "type": type,
            "with_mutual_guilds": _bool_to_query(with_mutual_guilds),
            "with_mutual_friends": _bool_to_query(with_mutual_friends),
            "with_mutual_friends_count": _bool_to_query(with_mutual_friends_count),
            "guild_id": guild_id,
        }
        response = self._request_json(
            url,
            params=params,
            context={"user_id": user_id},
            timeout_sec=float(request_timeout_sec) if request_timeout_sec is not None else None,
            max_retries=max_retries,
            extra_headers=extra_headers,
        )
        if isinstance(response, dict):
            return response
        raise DiscordApiError(0, "Unexpected response payload type for user profile")

    def _request_json(
        self,
        url: str,
        *,
        params: dict[str, str | int] | None = None,
        context: dict[str, str] | None = None,
        timeout_sec: float | None = None,
        max_retries: int | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict | list:
        last_exc: Exception | None = None
        retry_limit = self._config.max_retries if max_retries is None else max_retries
        timeout = self._request_timeout if timeout_sec is None else timeout_sec
        request_headers = self._headers | (extra_headers or {})

        for attempt in range(retry_limit + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.get(url, headers=request_headers, params=params)

                if resp.status_code == 429:
                    retry_after = _parse_retry_after(resp)
                    last_exc = DiscordApiError(
                        429,
                        f"Rate limited (429). retry_after={retry_after}",
                    )
                    logger.warning(
                        "Rate limited (429). Waiting %.1fs",
                        retry_after,
                        extra={
                            "event_code": "RATE_LIMITED",
                            "retry_after": retry_after,
                            **(context or {}),
                        },
                    )
                    if attempt >= retry_limit:
                        raise last_exc
                    time.sleep(retry_after)
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code
                if status in (401, 403, 404):
                    raise DiscordApiError(status, str(e)) from e
                if status >= 500 and attempt < retry_limit:
                    wait = _backoff_wait(attempt, self._config.backoff_factor)
                    logger.warning(
                        "Retry %d/%d after %.1fs: %s",
                        attempt + 1,
                        retry_limit,
                        wait,
                        e,
                    )
                    time.sleep(wait)
                    continue
                raise DiscordApiError(status, str(e)) from e

            except httpx.TimeoutException as e:
                last_exc = e
                if attempt < retry_limit:
                    wait = _backoff_wait(attempt, self._config.backoff_factor)
                    logger.warning(
                        "Timeout retry %d/%d after %.1fs",
                        attempt + 1,
                        retry_limit,
                        wait,
                    )
                    time.sleep(wait)
                    continue
                raise DiscordApiError(0, f"Timeout: {e}") from e

        raise DiscordApiError(0, f"Max retries exceeded: {last_exc}")


def _parse_retry_after(resp: httpx.Response) -> float:
    """429 응답에서 대기 시간을 파싱한다."""
    header_value = resp.headers.get("retry-after")
    if header_value:
        try:
            return max(float(header_value), 0.0)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(header_value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                now = datetime.now(tz=UTC)
                return max((retry_at - now).total_seconds(), 0.0)
            except Exception:
                pass

    try:
        body = resp.json()
        return float(body.get("retry_after", 5.0))
    except Exception:
        return 5.0  # 파싱 실패 시 보수적 5초


def _backoff_wait(attempt: int, backoff_factor: float) -> float:
    """지수 백오프 + 지터 대기 시간을 계산한다."""
    base = backoff_factor * (2**attempt)
    jitter = random.uniform(0, base * 0.5)
    return base + jitter


def _bool_to_query(value: bool) -> str:
    return "true" if value else "false"
