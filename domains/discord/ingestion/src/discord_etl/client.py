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
            raise RuntimeError(
                "DISCORD_USER_TOKEN 환경변수가 설정되지 않았습니다."
            )
        self._base_url = config.api_base.rstrip("/")

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

        headers = {
            "Authorization": self._token,
            "Content-Type": "application/json",
        }

        last_exc: Exception | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(url, headers=headers, params=params)

                # Rate limit 처리
                if resp.status_code == 429:
                    retry_after = _parse_retry_after(resp)
                    logger.warning(
                        "Rate limited (429). Waiting %.1fs",
                        retry_after,
                        extra={"event_code": "RATE_LIMITED",
                               "channel_id": channel_id,
                               "retry_after": retry_after},
                    )
                    time.sleep(retry_after)
                    continue  # 429는 재시도 횟수에 포함하지 않음

                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code
                # 403/404는 재시도 불가
                if status in (403, 404):
                    raise DiscordApiError(status, str(e)) from e
                # 5xx만 재시도
                if status >= 500 and attempt < self._config.max_retries:
                    wait = _backoff_wait(attempt, self._config.backoff_factor)
                    logger.warning(
                        "Retry %d/%d after %.1fs: %s",
                        attempt + 1, self._config.max_retries, wait, e,
                    )
                    time.sleep(wait)
                    continue
                raise DiscordApiError(status, str(e)) from e

            except httpx.TimeoutException as e:
                last_exc = e
                if attempt < self._config.max_retries:
                    wait = _backoff_wait(attempt, self._config.backoff_factor)
                    logger.warning(
                        "Timeout retry %d/%d after %.1fs",
                        attempt + 1, self._config.max_retries, wait,
                    )
                    time.sleep(wait)
                    continue
                raise DiscordApiError(0, f"Timeout: {e}") from e

        raise DiscordApiError(0, f"Max retries exceeded: {last_exc}")


def _parse_retry_after(resp: httpx.Response) -> float:
    """429 응답에서 대기 시간을 파싱한다."""
    try:
        body = resp.json()
        return float(body.get("retry_after", 5.0))
    except Exception:
        return 5.0  # 파싱 실패 시 보수적 5초


def _backoff_wait(attempt: int, backoff_factor: float) -> float:
    """지수 백오프 + 지터 대기 시간을 계산한다."""
    base = backoff_factor * (2 ** attempt)
    jitter = random.uniform(0, base * 0.5)
    return base + jitter
