"""CLI fetch 명령 테스트."""

from __future__ import annotations

import gzip
import io
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import orjson
from click.testing import CliRunner
from gharchive_etl.cli import main
from pytest_httpx import HTTPXMock

# ── 헬퍼 함수 ────────────────────────────────────────


def _make_ndjson_gz(events: list[dict]) -> bytes:
    """이벤트 리스트를 ndjson.gz 바이트로 변환."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        for event in events:
            f.write(orjson.dumps(event))
            f.write(b"\n")
    return buf.getvalue()


def _sample_event(event_id: str = "12345", org_login: str = "pseudolab") -> dict[str, Any]:
    """테스트용 샘플 이벤트."""
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


def _write_config(tmp_path: Path, **overrides: Any) -> Path:
    """임시 config.yaml 생성."""
    import yaml

    config_data = {
        "gharchive": {"base_url": "https://data.gharchive.org"},
        "target_orgs": ["pseudolab"],
        "event_types": [],
        "exclude_repos": [],
        "http": {
            "download_timeout_sec": 10,
            "max_retries": 1,
            "backoff_factor": 0.01,
            "max_concurrency": 1,
            "user_agent": "test/1.0",
        },
        "r2": {"bucket_name": "test"},
        "d1": {"database_id": "test"},
    }
    config_data.update(overrides)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config_data), encoding="utf-8")
    return config_path


BASE_URL = "https://data.gharchive.org"


# ── 입력 검증 테스트 ──────────────────────────────────


class TestFetchValidation:
    """fetch 명령 입력 검증."""

    def test_no_date_option(self) -> None:
        """날짜 미지정 시 에러."""
        runner = CliRunner()
        result = runner.invoke(main, ["fetch"])
        assert result.exit_code != 0

    def test_date_and_range_conflict(self, tmp_path: Path) -> None:
        """--date와 --start-date 동시 사용 시 에러."""
        config_path = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "2024-01-15",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )
        assert result.exit_code != 0
        assert "--date" in result.output or "동시에" in result.output

    def test_start_date_only(self, tmp_path: Path) -> None:
        """--start-date만 지정 시 에러."""
        config_path = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--start-date",
                "2024-01-01",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )
        assert result.exit_code != 0

    def test_invalid_hour_range(self, tmp_path: Path) -> None:
        """start-hour > end-hour 시 에러."""
        config_path = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "2024-01-15",
                "--start-hour",
                "15",
                "--end-hour",
                "10",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )
        assert result.exit_code != 0

    def test_invalid_date_format(self, tmp_path: Path) -> None:
        """잘못된 날짜 형식 시 에러."""
        config_path = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "15-01-2024",  # 잘못된 형식
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )
        assert result.exit_code != 0

    def test_config_not_found(self) -> None:
        """존재하지 않는 config 경로 → 명확한 에러."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "2024-01-15",
                "--config",
                "/nonexistent/config.yaml",
            ],
        )
        assert result.exit_code != 0

    def test_start_date_after_end_date(self, tmp_path: Path) -> None:
        """start-date > end-date 시 에러."""
        config_path = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--start-date",
                "2024-01-31",
                "--end-date",
                "2024-01-01",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )
        assert result.exit_code != 0


# ── 실행 테스트 ───────────────────────────────────────


class TestFetchExecution:
    """fetch 명령 실행 테스트."""

    def test_single_date_single_hour(self, tmp_path: Path, httpx_mock: HTTPXMock) -> None:
        """단일 날짜, 단일 시간대 실행."""
        config_path = _write_config(tmp_path)
        events = [_sample_event("1", "pseudolab")]
        gz_data = _make_ndjson_gz(events)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", content=gz_data)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "2024-01-15",
                "--start-hour",
                "10",
                "--end-hour",
                "10",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )

        assert result.exit_code == 0
        assert "Fetch complete" in result.output

    def test_output_jsonl(self, tmp_path: Path, httpx_mock: HTTPXMock) -> None:
        """--output-jsonl로 필터 통과 이벤트 JSONL 출력."""
        config_path = _write_config(tmp_path)
        events = [
            _sample_event("1", "pseudolab"),
            _sample_event("2", "other-org"),
        ]
        gz_data = _make_ndjson_gz(events)
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", content=gz_data)

        output_path = tmp_path / "output.jsonl"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "2024-01-15",
                "--start-hour",
                "10",
                "--end-hour",
                "10",
                "--config",
                str(config_path),
                "--output-jsonl",
                str(output_path),
                "--no-json-log",
            ],
        )

        assert result.exit_code == 0
        assert output_path.exists()

        # JSONL 파일에 필터 통과 이벤트만 있는지 확인
        lines = output_path.read_bytes().strip().split(b"\n")
        assert len(lines) == 1  # pseudolab 이벤트 1개만
        parsed = orjson.loads(lines[0])
        assert parsed["id"] == "1"

    def test_hour_range(self, tmp_path: Path, httpx_mock: HTTPXMock) -> None:
        """--start-hour/--end-hour 범위 실행."""
        config_path = _write_config(tmp_path)

        # 시간 10, 11 모두 응답 준비
        for hour in (10, 11):
            gz_data = _make_ndjson_gz([_sample_event(str(hour), "pseudolab")])
            httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-{hour}.json.gz", content=gz_data)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "2024-01-15",
                "--start-hour",
                "10",
                "--end-hour",
                "11",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )

        assert result.exit_code == 0
        assert "filtered=2" in result.output

    def test_date_range(self, tmp_path: Path, httpx_mock: HTTPXMock) -> None:
        """--start-date/--end-date 범위 실행."""
        config_path = _write_config(tmp_path)

        # 2일간 각 1시간대만 테스트
        for date_str in ("2024-01-15", "2024-01-16"):
            gz_data = _make_ndjson_gz([_sample_event(date_str, "pseudolab")])
            httpx_mock.add_response(url=f"{BASE_URL}/{date_str}-0.json.gz", content=gz_data)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--start-date",
                "2024-01-15",
                "--end-date",
                "2024-01-16",
                "--start-hour",
                "0",
                "--end-hour",
                "0",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )

        assert result.exit_code == 0
        assert "filtered=2" in result.output

    @patch("gharchive_etl.downloader.time.sleep")
    def test_404_continues(
        self, mock_sleep: MagicMock, tmp_path: Path, httpx_mock: HTTPXMock
    ) -> None:
        """404 시간대를 건너뛰고 다음 시간대 계속 처리."""
        config_path = _write_config(tmp_path)

        # 시간 10: 404 (MAX_404_RETRIES+1 회 등록 — 404 재시도 대응)
        from gharchive_etl.downloader import MAX_404_RETRIES

        for _ in range(MAX_404_RETRIES + 1):
            httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=404)
        gz_data = _make_ndjson_gz([_sample_event("1", "pseudolab")])
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-11.json.gz", content=gz_data)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "2024-01-15",
                "--start-hour",
                "10",
                "--end-hour",
                "11",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )

        assert result.exit_code == 1
        assert "filtered=1" in result.output

    def test_failed_hour_exit_code_1(self, tmp_path: Path, httpx_mock: HTTPXMock) -> None:
        """실패 시간대 있으면 exit code 1."""
        config_path = _write_config(tmp_path)

        # max_retries=1 기준:
        # iter_ndjson_events: attempt 0 (500) + attempt 1 (500) → DownloadError
        # process_hour: attempt 0 catches → retry
        # iter_ndjson_events: attempt 0 (500) + attempt 1 (500) → DownloadError
        # process_hour: attempt 1 exhausted → 실패
        # 총 4회 요청
        for _ in range(4):
            httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-10.json.gz", status_code=500)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "2024-01-15",
                "--start-hour",
                "10",
                "--end-hour",
                "10",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )

        assert result.exit_code == 1

    def test_progress_output(self, tmp_path: Path, httpx_mock: HTTPXMock) -> None:
        """진행률 표시 확인."""
        config_path = _write_config(tmp_path)
        gz_data = _make_ndjson_gz([_sample_event("1", "pseudolab")])
        httpx_mock.add_response(url=f"{BASE_URL}/2024-01-15-5.json.gz", content=gz_data)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "fetch",
                "--date",
                "2024-01-15",
                "--start-hour",
                "5",
                "--end-hour",
                "5",
                "--config",
                str(config_path),
                "--no-json-log",
            ],
        )

        assert "[05/05] Processing 2024-01-15-5" in result.output

    def test_version_option(self) -> None:
        """--version 옵션."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
