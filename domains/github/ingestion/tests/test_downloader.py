"""downloader 모듈 테스트.

2계층 모킹 전략:
- Layer 1: HTTP 레벨 (pytest-httpx) - 통합 테스트
- Layer 2: 내부 로직 (zlib + line_buffer) - 단위 테스트
"""

from __future__ import annotations

import gzip
import io
import zlib
from typing import Any
from unittest.mock import patch

import httpx
import orjson
import pytest
from gharchive_etl.config import AppConfig, HttpConfig
from gharchive_etl.downloader import (
    MAX_404_RETRIES,
    RETRY_404_DELAY_SEC,
    DownloadError,
    HourNotFoundError,
    build_hour_url,
    iter_ndjson_events,
    process_hour,
    safe_parse_event,
)
from pytest_httpx import HTTPXMock

# ── 헬퍼 함수 ────────────────────────────────────────


def _make_ndjson_gz(events: list[dict]) -> bytes:
    """이벤트 리스트를 ndjson.gz 바이트로 변환한다."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        for event in events:
            f.write(orjson.dumps(event))
            f.write(b"\n")
    return buf.getvalue()


def _make_ndjson_gz_no_trailing_newline(events: list[dict]) -> bytes:
    """마지막 이벤트 후 개행 없이 끝나는 ndjson.gz를 생성한다."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        for i, event in enumerate(events):
            f.write(orjson.dumps(event))
            if i < len(events) - 1:
                f.write(b"\n")
    return buf.getvalue()


def _make_ndjson_gz_with_bad_line(good_events: list[dict], bad_line: bytes) -> bytes:
    """정상 이벤트 사이에 깨진 JSON 라인을 삽입한다."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        for event in good_events[:1]:
            f.write(orjson.dumps(event))
            f.write(b"\n")
        f.write(bad_line)
        f.write(b"\n")
        for event in good_events[1:]:
            f.write(orjson.dumps(event))
            f.write(b"\n")
    return buf.getvalue()


def _sample_event(event_id: str = "12345", org_login: str = "pseudolab") -> dict[str, Any]:
    """테스트용 샘플 이벤트 dict."""
    return {
        "id": event_id,
        "type": "PushEvent",
        "actor": {"id": 1, "login": "testuser"},
        "repo": {"id": 100, "name": f"{org_login}/test-repo"},
        "org": {"id": 200, "login": org_login},
        "payload": {},
        "public": True,
        "created_at": "2024-01-15T10:30:00Z",
    }


def _http_config(**overrides: Any) -> HttpConfig:
    """테스트용 HttpConfig."""
    defaults = {
        "download_timeout_sec": 10,
        "max_retries": 2,
        "backoff_factor": 0.01,  # 테스트에서는 빠르게
        "max_concurrency": 1,
        "user_agent": "test/1.0",
    }
    defaults.update(overrides)
    return HttpConfig(**defaults)


def _app_config(**overrides: Any) -> AppConfig:
    """테스트용 AppConfig."""
    defaults = {
        "target_orgs": ["pseudolab"],
        "event_types": [],
        "exclude_repos": [],
        "http": _http_config().model_dump(),
    }
    defaults.update(overrides)
    return AppConfig(**defaults)


BASE_URL = "https://data.gharchive.org"


# ── Layer 2: 내부 로직 단위 테스트 ──────────────────


class TestBuildHourUrl:
    """build_hour_url 유틸 함수 테스트."""

    def test_basic(self) -> None:
        url = build_hour_url("2024-01-15", 10, "https://data.gharchive.org")
        assert url == "https://data.gharchive.org/2024-01-15-10.json.gz"

    def test_trailing_slash(self) -> None:
        url = build_hour_url("2024-01-15", 0, "https://data.gharchive.org/")
        assert url == "https://data.gharchive.org/2024-01-15-0.json.gz"

    def test_hour_23(self) -> None:
        url = build_hour_url("2024-12-31", 23, "https://data.gharchive.org")
        assert url == "https://data.gharchive.org/2024-12-31-23.json.gz"


class TestSafeParseEvent:
    """safe_parse_event 모델 변환 테스트."""

    def test_valid_event(self, sample_event_data: dict[str, Any]) -> None:
        event = safe_parse_event(sample_event_data)
        assert event is not None
        assert event.id == "12345678901"
        assert event.type == "PushEvent"

    def test_invalid_event_returns_none(self) -> None:
        """필수 필드 누락 시 None 반환."""
        result = safe_parse_event({"type": "PushEvent"})  # id 누락
        assert result is None

    def test_missing_actor_returns_none(self) -> None:
        """actor 필드 누락 시 None 반환."""
        result = safe_parse_event({"id": "123", "type": "PushEvent"})
        assert result is None


class TestZlibLineBufferLogic:
    """zlib 청크 경계 + line_buffer 로직 단위 테스트.

    HTTP 없이 순수 zlib 디코딩 + 라인 분할 로직만 검증.
    """

    def test_single_chunk(self) -> None:
        """단일 청크에서 모든 라인 파싱."""
        events = [_sample_event("1"), _sample_event("2"), _sample_event("3")]
        gz_data = _make_ndjson_gz(events)

        decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
        line_buffer = b""
        results: list[dict] = []

        # 단일 청크로 전달
        decompressed = decompressor.decompress(gz_data)
        line_buffer += decompressed
        while b"\n" in line_buffer:
            line, line_buffer = line_buffer.split(b"\n", 1)
            if line:
                results.append(orjson.loads(line))

        # flush 처리
        remaining = decompressor.flush()
        if remaining:
            line_buffer += remaining
        if line_buffer.strip():
            results.append(orjson.loads(line_buffer))

        assert len(results) == 3
        assert results[0]["id"] == "1"

    def test_split_across_chunks(self) -> None:
        """ndjson 라인이 두 개의 zlib 청크에 걸쳐 분할되는 경우."""
        events = [_sample_event("1"), _sample_event("2")]
        gz_data = _make_ndjson_gz(events)

        # 청크를 의도적으로 작게 분할 (라인 경계가 청크 경계와 불일치)
        chunk_size = max(len(gz_data) // 3, 1)
        chunks = [gz_data[i : i + chunk_size] for i in range(0, len(gz_data), chunk_size)]
        assert len(chunks) >= 2, "최소 2개 청크 필요"

        decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
        line_buffer = b""
        results: list[dict] = []

        for chunk in chunks:
            try:
                decompressed = decompressor.decompress(chunk)
            except zlib.error:
                break
            line_buffer += decompressed
            while b"\n" in line_buffer:
                line, line_buffer = line_buffer.split(b"\n", 1)
                if line:
                    results.append(orjson.loads(line))

        # flush
        try:
            remaining = decompressor.flush()
            if remaining:
                line_buffer += remaining
        except zlib.error:
            pass
        if line_buffer.strip():
            results.append(orjson.loads(line_buffer))

        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[1]["id"] == "2"

    def test_no_trailing_newline(self) -> None:
        """마지막 레코드 뒤에 개행이 없는 경우에도 파싱."""
        events = [_sample_event("1"), _sample_event("2")]
        gz_data = _make_ndjson_gz_no_trailing_newline(events)

        decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
        line_buffer = b""
        results: list[dict] = []

        decompressed = decompressor.decompress(gz_data)
        line_buffer += decompressed
        while b"\n" in line_buffer:
            line, line_buffer = line_buffer.split(b"\n", 1)
            if line:
                results.append(orjson.loads(line))

        remaining = decompressor.flush()
        if remaining:
            line_buffer += remaining
        if line_buffer.strip():
            results.append(orjson.loads(line_buffer))

        assert len(results) == 2


# ── Layer 1: HTTP 통합 테스트 ────────────────────────


class TestIterNdjsonEvents:
    """iter_ndjson_events HTTP 통합 테스트."""

    def test_normal_download(self, httpx_mock: HTTPXMock) -> None:
        """정상 ndjson.gz 파싱."""
        events = [_sample_event("1"), _sample_event("2")]
        gz_data = _make_ndjson_gz(events)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", content=gz_data)

        result = list(iter_ndjson_events("2024-01-15", 10, _http_config(), BASE_URL))
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

    def test_404_raises_hour_not_found(self, httpx_mock: HTTPXMock) -> None:
        """404 응답 시 HourNotFoundError."""
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=404)

        with pytest.raises(HourNotFoundError, match="Hour file not found"):
            list(iter_ndjson_events("2024-01-15", 10, _http_config(), BASE_URL))

    def test_bad_json_line_skipped(self, httpx_mock: HTTPXMock) -> None:
        """깨진 JSON 라인 스킵 + 정상 이벤트 파싱."""
        good_events = [_sample_event("1"), _sample_event("2")]
        gz_data = _make_ndjson_gz_with_bad_line(good_events, b"not-valid-json{{{")
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-0.json.gz", content=gz_data)

        result = list(iter_ndjson_events("2024-01-15", 0, _http_config(), BASE_URL))
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

    def test_empty_gzip(self, httpx_mock: HTTPXMock) -> None:
        """빈 gzip 응답 → 빈 결과, 에러 없음."""
        gz_data = _make_ndjson_gz([])
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-5.json.gz", content=gz_data)

        result = list(iter_ndjson_events("2024-01-15", 5, _http_config(), BASE_URL))
        assert result == []

    def test_retry_on_server_error(self, httpx_mock: HTTPXMock) -> None:
        """서버 에러 후 재시도 성공."""
        events = [_sample_event("1")]
        gz_data = _make_ndjson_gz(events)

        # 첫 번째: 503, 두 번째: 성공
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=503)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", content=gz_data)

        result = list(iter_ndjson_events("2024-01-15", 10, _http_config(), BASE_URL))
        assert len(result) == 1

    def test_retry_exhausted_raises(self, httpx_mock: HTTPXMock) -> None:
        """재시도 초과 시 DownloadError."""
        config = _http_config(max_retries=1)

        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=500)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=500)

        with pytest.raises(DownloadError, match="HTTP error after"):
            list(iter_ndjson_events("2024-01-15", 10, config, BASE_URL))

    def test_timeout_retry(self, httpx_mock: HTTPXMock) -> None:
        """타임아웃 후 재시도."""
        events = [_sample_event("1")]
        gz_data = _make_ndjson_gz(events)

        httpx_mock.add_exception(
            httpx.ReadTimeout("timeout"),
            url=f"{BASE_URL}/2024-01-15-10.json.gz",
        )
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", content=gz_data)

        result = list(iter_ndjson_events("2024-01-15", 10, _http_config(), BASE_URL))
        assert len(result) == 1

    def test_corrupt_gzip_raises(self, httpx_mock: HTTPXMock) -> None:
        """손상된 gzip 데이터 → DownloadError."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/2024-01-15-10.json.gz",
            content=b"this-is-not-gzip-data",
        )

        with pytest.raises(DownloadError, match="Gzip decompression failed"):
            list(iter_ndjson_events("2024-01-15", 10, _http_config(max_retries=0), BASE_URL))

    def test_no_trailing_newline_last_event(self, httpx_mock: HTTPXMock) -> None:
        """마지막 레코드 뒤 개행 없어도 파싱."""
        events = [_sample_event("1"), _sample_event("2")]
        gz_data = _make_ndjson_gz_no_trailing_newline(events)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-0.json.gz", content=gz_data)

        result = list(iter_ndjson_events("2024-01-15", 0, _http_config(), BASE_URL))
        assert len(result) == 2


# ── process_hour 파이프라인 테스트 ────────────────────


class TestProcessHour:
    """process_hour 통합 파이프라인 테스트."""

    def test_normal_pipeline(self, httpx_mock: HTTPXMock) -> None:
        """정상 파이프라인: 다운로드 → 파싱 → 필터링."""
        events = [
            _sample_event("1", "pseudolab"),
            _sample_event("2", "other-org"),
            _sample_event("3", "pseudolab"),
        ]
        gz_data = _make_ndjson_gz(events)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", content=gz_data)

        config = _app_config()
        filtered, stats = process_hour("2024-01-15", 10, config)

        assert len(filtered) == 2  # pseudolab만 통과
        assert stats.downloaded == 3
        assert stats.parsed == 3
        assert stats.invalid == 0
        assert stats.filtered_in == 2

    def test_validation_error_counted(self, httpx_mock: HTTPXMock) -> None:
        """ValidationError 이벤트는 카운트 후 스킵."""
        events = [
            _sample_event("1", "pseudolab"),
            {"invalid": "no-required-fields"},  # ValidationError 발생
        ]
        gz_data = _make_ndjson_gz(events)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-0.json.gz", content=gz_data)

        config = _app_config()
        filtered, stats = process_hour("2024-01-15", 0, config)

        assert len(filtered) == 1
        assert stats.downloaded == 2
        assert stats.parsed == 1
        assert stats.invalid == 1

    def test_404_returns_empty_with_skip_flag(self, httpx_mock: HTTPXMock) -> None:
        """404 시 빈 결과 + skipped_404=True + 에러 없음 (MAX_404_RETRIES+1번 모두 404)."""
        for _ in range(MAX_404_RETRIES + 1):
            httpx_mock.add_response(
                url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=404
            )

        config = _app_config()
        with patch("gharchive_etl.downloader.time.sleep"):
            filtered, stats = process_hour("2024-01-15", 10, config)

        assert filtered == []
        assert stats.downloaded == 0
        assert stats.skipped_404 is True
        assert stats.error is None

    def test_stream_error_retry(self, httpx_mock: HTTPXMock) -> None:
        """스트림 중단 후 process_hour 재시도 → 중복 없이 성공."""
        events = [_sample_event("1", "pseudolab")]
        gz_data = _make_ndjson_gz(events)

        # 첫 번째: 손상 데이터 (DownloadError), 두 번째: 정상
        httpx_mock.add_response(
            url=f"{BASE_URL}/2024-01-15-10.json.gz",
            content=b"corrupted-gzip",
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/2024-01-15-10.json.gz",
            content=gz_data,
        )

        config = _app_config()
        filtered, stats = process_hour("2024-01-15", 10, config)

        assert len(filtered) == 1
        assert stats.filtered_in == 1
        assert stats.error is None  # 최종 성공

    def test_stats_duration(self, httpx_mock: HTTPXMock) -> None:
        """duration_ms가 0보다 큼."""
        gz_data = _make_ndjson_gz([_sample_event("1", "pseudolab")])
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-0.json.gz", content=gz_data)

        _, stats = process_hour("2024-01-15", 0, _app_config())
        assert stats.duration_ms > 0

    def test_event_type_filter(self, httpx_mock: HTTPXMock) -> None:
        """event_types 필터 적용."""
        push_event = _sample_event("1", "pseudolab")
        push_event["type"] = "PushEvent"
        issue_event = _sample_event("2", "pseudolab")
        issue_event["type"] = "IssuesEvent"

        gz_data = _make_ndjson_gz([push_event, issue_event])
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-0.json.gz", content=gz_data)

        config = _app_config(event_types=["PushEvent"])
        filtered, stats = process_hour("2024-01-15", 0, config)

        assert len(filtered) == 1
        assert filtered[0].type == "PushEvent"
        assert stats.filtered_in == 1

    def test_exclude_repos_filter(self, httpx_mock: HTTPXMock) -> None:
        """exclude_repos 필터 적용."""
        events = [
            _sample_event("1", "pseudolab"),
            _sample_event("2", "pseudolab"),
        ]
        events[1]["repo"]["name"] = "pseudolab/excluded-repo"
        gz_data = _make_ndjson_gz(events)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-0.json.gz", content=gz_data)

        config = _app_config(exclude_repos=["pseudolab/excluded-repo"])
        filtered, stats = process_hour("2024-01-15", 0, config)

        assert len(filtered) == 1
        assert stats.filtered_in == 1


# ── 404 재시도 테스트 ─────────────────────────────────


class Test404Retry:
    """process_hour 404 재시도 로직 테스트."""

    def test_404_retries_then_succeeds(self, httpx_mock: HTTPXMock) -> None:
        """첫 2번 404, 3번째 성공 → 정상 결과 반환."""
        events = [_sample_event("1", "pseudolab")]
        gz_data = _make_ndjson_gz(events)

        # 첫 2번: 404, 마지막: 성공
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=404)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=404)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", content=gz_data)

        config = _app_config()
        with patch("gharchive_etl.downloader.time.sleep"):
            filtered, stats = process_hour("2024-01-15", 10, config)

        assert len(filtered) == 1
        assert stats.skipped_404 is False
        assert stats.error is None

    def test_404_retries_exhausted(self, httpx_mock: HTTPXMock) -> None:
        """MAX_404_RETRIES+1번 모두 404 → skipped_404=True, 빈 결과."""
        # MAX_404_RETRIES+1번 모두 404 응답 등록
        for _ in range(MAX_404_RETRIES + 1):
            httpx_mock.add_response(
                url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=404
            )

        config = _app_config()
        with patch("gharchive_etl.downloader.time.sleep"):
            filtered, stats = process_hour("2024-01-15", 10, config)

        assert filtered == []
        assert stats.skipped_404 is True
        assert stats.error is None

    def test_404_retry_delay(self, httpx_mock: HTTPXMock) -> None:
        """404 발생 시 RETRY_404_DELAY_SEC 간격으로 sleep이 호출된다."""
        events = [_sample_event("1", "pseudolab")]
        gz_data = _make_ndjson_gz(events)

        # 첫 번째: 404, 두 번째: 성공
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=404)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", content=gz_data)

        config = _app_config()
        with patch("gharchive_etl.downloader.time.sleep") as mock_sleep:
            filtered, stats = process_hour("2024-01-15", 10, config)

        # 404 재시도 sleep 호출 검증
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert RETRY_404_DELAY_SEC in sleep_calls
        assert len(filtered) == 1
        assert stats.skipped_404 is False
