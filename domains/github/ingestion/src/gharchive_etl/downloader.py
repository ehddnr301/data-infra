"""gharchive.org 시간별 ndjson.gz 스트리밍 다운로드 + 모델 변환 파이프라인.

핵심 설계:
- zlib.decompressobj로 진정한 상수 메모리 스트리밍
- retry 2계층: 연결 수준(안전) vs 스트림 중단(caller 위임)
- safe_parse_event로 ValidationError 격리
- process_hour로 download → parse → filter 파이프라인 통합
"""

from __future__ import annotations

import logging
import random
import time
import zlib
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import orjson
from pydantic import ValidationError

from gharchive_etl.config import AppConfig, HttpConfig
from gharchive_etl.filter import filter_events
from gharchive_etl.models import GitHubEvent

logger = logging.getLogger(__name__)


# ── 404 재시도 설정 ──────────────────────────────────
MAX_404_RETRIES = 1
RETRY_404_DELAY_SEC = 15

# ── 데이터 클래스 ─────────────────────────────────────


@dataclass
class HourStats:
    """시간 단위 처리 통계."""

    date: str
    hour: int
    downloaded: int = 0
    parsed: int = 0
    invalid: int = 0
    filtered_in: int = 0
    duration_ms: float = 0.0
    skipped_404: bool = False
    error: str | None = None


# ── 유틸 함수 ─────────────────────────────────────────


def build_hour_url(date: str, hour: int, base_url: str) -> str:
    """gharchive 시간별 파일 URL을 생성한다.

    Args:
        date: 날짜 (예: "2024-01-15")
        hour: 시간 (0~23)
        base_url: gharchive base URL

    Returns:
        완전한 다운로드 URL
    """
    return f"{base_url.rstrip('/')}/{date}-{hour}.json.gz"


# ── 스트리밍 다운로더 ────────────────────────────────


class DownloadError(Exception):
    """다운로드 실패 예외."""


class HourNotFoundError(Exception):
    """시간대 파일 404 예외."""


def iter_ndjson_events(
    date: str,
    hour: int,
    config: HttpConfig,
    base_url: str,
) -> Iterator[dict]:
    """gharchive 시간별 ndjson.gz를 스트리밍 파싱하여 이벤트 dict를 yield한다.

    - zlib.decompressobj로 상수 메모리 스트리밍
    - 404 → 경고 로그 + 빈 이터레이터
    - JSON 파싱 실패 → 경고 로그 + 스킵
    - 연결 수준 오류 → retry/backoff (이벤트 yield 전이므로 안전)
    - 스트림 중단 → DownloadError 발생 (caller에서 재시도)

    Args:
        date: 날짜 (예: "2024-01-15")
        hour: 시간 (0~23)
        config: HTTP 설정
        base_url: gharchive base URL

    Yields:
        파싱된 이벤트 dict

    Raises:
        DownloadError: 최종 실패 시
    """
    url = build_hour_url(date, hour, base_url)
    parse_errors = 0

    # 연결 수준 retry (이벤트 yield 전이므로 중복 없음)
    last_exc: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            with (
                httpx.Client(
                    timeout=config.download_timeout_sec,
                    headers={"User-Agent": config.user_agent},
                ) as client,
                client.stream("GET", url) as response,
            ):
                if response.status_code == 404:
                    logger.warning(
                        "Hour file not found: %s-%d",
                        date,
                        hour,
                        extra={"event_code": "HOUR_NOT_FOUND", "date": date, "hour": hour},
                    )
                    raise HourNotFoundError(f"Hour file not found: {date}-{hour}")

                response.raise_for_status()

                # 스트리밍 gzip 해제 + ndjson 파싱
                decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
                line_buffer = b""

                for chunk in response.iter_bytes(chunk_size=65536):
                    try:
                        decompressed = decompressor.decompress(chunk)
                    except zlib.error as exc:
                        logger.warning(
                            "Gzip decompression error: %s",
                            exc,
                            extra={
                                "event_code": "PARSE_ERROR",
                                "date": date,
                                "hour": hour,
                            },
                        )
                        raise DownloadError(
                            f"Gzip decompression failed for {date}-{hour}: {exc}"
                        ) from exc

                    line_buffer += decompressed

                    while b"\n" in line_buffer:
                        line, line_buffer = line_buffer.split(b"\n", 1)
                        if not line:
                            continue
                        try:
                            yield orjson.loads(line)
                        except orjson.JSONDecodeError:
                            parse_errors += 1
                            logger.warning(
                                "JSON parse error (line skipped), total errors: %d",
                                parse_errors,
                                extra={
                                    "event_code": "PARSE_ERROR",
                                    "date": date,
                                    "hour": hour,
                                },
                            )

                # gzip 스트림 종료: 잔여 데이터 flush
                try:
                    remaining = decompressor.flush()
                    if remaining:
                        line_buffer += remaining
                except zlib.error as exc:
                    logger.warning(
                        "Gzip flush error (stream may be truncated): %s",
                        exc,
                        extra={
                            "event_code": "PARSE_ERROR",
                            "date": date,
                            "hour": hour,
                        },
                    )

                # 남은 버퍼 처리 (개행 없이 끝나는 마지막 레코드)
                if line_buffer.strip():
                    try:
                        yield orjson.loads(line_buffer)
                    except orjson.JSONDecodeError:
                        parse_errors += 1
                        logger.warning(
                            "JSON parse error (final line skipped), total errors: %d",
                            parse_errors,
                            extra={
                                "event_code": "PARSE_ERROR",
                                "date": date,
                                "hour": hour,
                            },
                        )

                # 정상 완료
                return

        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if attempt < config.max_retries:
                wait = _backoff_wait(attempt, config.backoff_factor)
                logger.warning(
                    "HTTP %d for %s-%d, retrying in %.1fs (attempt %d/%d)",
                    exc.response.status_code,
                    date,
                    hour,
                    wait,
                    attempt + 1,
                    config.max_retries,
                    extra={
                        "event_code": "RETRY_ATTEMPT",
                        "date": date,
                        "hour": hour,
                    },
                )
                time.sleep(wait)
            else:
                raise DownloadError(
                    f"HTTP error after {config.max_retries} retries for {date}-{hour}: {exc}"
                ) from exc

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < config.max_retries:
                wait = _backoff_wait(attempt, config.backoff_factor)
                logger.warning(
                    "Connection error for %s-%d: %s, retrying in %.1fs (attempt %d/%d)",
                    date,
                    hour,
                    type(exc).__name__,
                    wait,
                    attempt + 1,
                    config.max_retries,
                    extra={
                        "event_code": "RETRY_ATTEMPT",
                        "date": date,
                        "hour": hour,
                    },
                )
                time.sleep(wait)
            else:
                raise DownloadError(
                    f"Connection failed after {config.max_retries} retries for {date}-{hour}: {exc}"
                ) from exc

        except DownloadError:
            # gzip 손상 등 스트림 중단 → caller에서 재시도
            raise

    # 도달 불가하지만 안전을 위해
    raise DownloadError(f"Unexpected retry exhaustion for {date}-{hour}: {last_exc}")


def _backoff_wait(attempt: int, backoff_factor: float) -> float:
    """지수 백오프 + jitter 대기 시간 계산."""
    base = backoff_factor * (2**attempt)
    jitter = random.uniform(0, base * 0.5)
    return base + jitter


# ── 모델 변환 ────────────────────────────────────────


def safe_parse_event(raw: dict) -> GitHubEvent | None:
    """raw dict를 GitHubEvent로 안전하게 변환한다.

    ValidationError 발생 시 None을 반환하고 경고 로그를 남긴다.
    """
    try:
        return GitHubEvent.model_validate(raw)
    except ValidationError:
        logger.warning(
            "Event validation failed: id=%s, type=%s",
            raw.get("id", "unknown"),
            raw.get("type", "unknown"),
            extra={"event_code": "VALIDATION_ERROR"},
        )
        return None


# ── 시간 단위 파이프라인 ─────────────────────────────


def process_hour(
    date: str,
    hour: int,
    config: AppConfig,
) -> tuple[list[GitHubEvent], HourStats]:
    """한 시간 분량의 이벤트를 다운로드 → 파싱 → 필터링한다.

    스트림 중단(DownloadError) 시 부분 결과를 폐기하고 전체 재시도한다.

    Returns:
        (필터 통과 이벤트 리스트, 시간 통계)
    """
    stats = HourStats(date=date, hour=hour)
    start = time.monotonic()

    logger.info(
        "Processing %s-%d",
        date,
        hour,
        extra={"event_code": "HOUR_START", "date": date, "hour": hour},
    )

    # 스트림 중단 시 전체 재시도 (부분 결과 폐기)
    # 외부 루프: 404 재시도 (gharchive 업로드 지연 대응)
    last_exc: Exception | None = None
    for _404_attempt in range(MAX_404_RETRIES + 1):
        _got_404 = False
        for attempt in range(config.http.max_retries + 1):
            try:
                downloaded = 0
                parsed_count = 0
                invalid_count = 0
                parsed_events: list[GitHubEvent] = []

                for raw in iter_ndjson_events(date, hour, config.http, config.gharchive.base_url):
                    downloaded += 1
                    event = safe_parse_event(raw)
                    if event is None:
                        invalid_count += 1
                    else:
                        parsed_count += 1
                        parsed_events.append(event)

                # 필터 적용
                filtered = filter_events(parsed_events, config)

                stats.downloaded = downloaded
                stats.parsed = parsed_count
                stats.invalid = invalid_count
                stats.filtered_in = len(filtered)
                stats.duration_ms = (time.monotonic() - start) * 1000

                logger.info(
                    "Hour complete: %s-%d (downloaded=%d, parsed=%d, invalid=%d, filtered=%d, %.0fms)",
                    date,
                    hour,
                    downloaded,
                    parsed_count,
                    invalid_count,
                    len(filtered),
                    stats.duration_ms,
                    extra={
                        "event_code": "HOUR_COMPLETE",
                        "date": date,
                        "hour": hour,
                        "duration_ms": stats.duration_ms,
                        "counts": {
                            "downloaded": downloaded,
                            "parsed": parsed_count,
                            "invalid": invalid_count,
                            "filtered_in": len(filtered),
                        },
                    },
                )

                return filtered, stats

            except HourNotFoundError:
                if _404_attempt < MAX_404_RETRIES:
                    logger.warning(
                        "Hour file not found (404): %s-%d, retry %d/%d in %ds (gharchive upload delay)",
                        date,
                        hour,
                        _404_attempt + 1,
                        MAX_404_RETRIES,
                        RETRY_404_DELAY_SEC,
                        extra={
                            "event_code": "HOUR_NOT_FOUND_RETRY",
                            "date": date,
                            "hour": hour,
                        },
                    )
                    time.sleep(RETRY_404_DELAY_SEC)
                    _got_404 = True
                    break  # inner loop → continue outer 404 loop
                else:
                    stats.skipped_404 = True
                    stats.error = (
                        f"Hour file not found after {MAX_404_RETRIES + 1} attempts: {date}-{hour}"
                    )
                    stats.duration_ms = (time.monotonic() - start) * 1000
                    logger.error(
                        "Hour file missing after retries: %s-%d",
                        date,
                        hour,
                        extra={
                            "event_code": "NETWORK_ERROR",
                            "date": date,
                            "hour": hour,
                            "duration_ms": stats.duration_ms,
                        },
                    )
                    return [], stats

            except DownloadError as exc:
                last_exc = exc
                if attempt < config.http.max_retries:
                    wait = _backoff_wait(attempt, config.http.backoff_factor)
                    logger.warning(
                        "Stream interrupted for %s-%d, retrying entire hour (attempt %d/%d)",
                        date,
                        hour,
                        attempt + 1,
                        config.http.max_retries,
                        extra={
                            "event_code": "RETRY_ATTEMPT",
                            "date": date,
                            "hour": hour,
                        },
                    )
                    time.sleep(wait)
                else:
                    stats.error = str(exc)
                    stats.duration_ms = (time.monotonic() - start) * 1000
                    logger.error(
                        "Hour failed after retries: %s-%d: %s",
                        date,
                        hour,
                        exc,
                        extra={
                            "event_code": "NETWORK_ERROR",
                            "date": date,
                            "hour": hour,
                            "duration_ms": stats.duration_ms,
                        },
                    )
                    return [], stats

        if not _got_404:
            # inner loop exhausted without 404 — DownloadError path already returned
            break

    # 도달 불가
    stats.error = str(last_exc)
    stats.duration_ms = (time.monotonic() - start) * 1000
    return [], stats
