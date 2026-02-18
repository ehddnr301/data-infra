"""CLI upload / verify-aggregation / quality-check 명령 테스트."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import orjson
import yaml
from click.testing import CliRunner
from gharchive_etl.cli import _load_jsonl, main
from gharchive_etl.d1 import D1InsertResult
from gharchive_etl.quality import ConsistencyReport, QualityReport, QualityRuleResult
from gharchive_etl.r2 import R2UploadResult

# ── 헬퍼 함수 ────────────────────────────────────────


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
    """임시 config.yaml 생성 (D1 auth 포함)."""
    config_data: dict[str, Any] = {
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
        "r2": {"bucket_name": "test-bucket", "prefix": "raw/github-archive"},
        "d1": {
            "database_id": "test-db-id",
            "account_id": "test-account-id",
            "api_token": "test-api-token",
        },
    }
    config_data.update(overrides)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config_data), encoding="utf-8")
    return config_path


def _write_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    """JSONL 파일을 생성한다."""
    with open(path, "wb") as f:
        for event in events:
            f.write(orjson.dumps(event))
            f.write(b"\n")


def _make_d1_result(**kwargs: Any) -> D1InsertResult:
    """D1InsertResult를 생성한다."""
    return D1InsertResult(**kwargs)


def _make_r2_result(**kwargs: Any) -> R2UploadResult:
    """R2UploadResult를 생성한다."""
    return R2UploadResult(**kwargs)


def _make_dl_results(**kwargs: Any) -> dict[str, D1InsertResult]:
    """insert_all_dl_rows 반환값 헬퍼 (dict[str, D1InsertResult])."""
    return {"dl_push_events": D1InsertResult(**kwargs)}


def _make_daily_stats_row(**kwargs: Any) -> dict[str, Any]:
    """compute_daily_stats_from_dl 반환값용 헬퍼."""
    row = {
        "date": "2024-01-15",
        "org_name": "pseudolab",
        "repo_name": "pseudolab/test-repo",
        "event_type": "PushEvent",
        "count": 1,
    }
    row.update(kwargs)
    return row


# ── 업로드 명령 테스트 ────────────────────────────────


_MOCK_D1_AUTH = "gharchive_etl.cli._validate_d1_auth"
_MOCK_WRANGLER = "gharchive_etl.cli._check_wrangler_installed"
_MOCK_INSERT_DL = "gharchive_etl.cli.insert_all_dl_rows"
_MOCK_INSERT_STATS = "gharchive_etl.cli.insert_daily_stats"
_MOCK_COMPUTE_STATS_FROM_DL = "gharchive_etl.cli.compute_daily_stats_from_dl"
_MOCK_R2_UPLOAD = "gharchive_etl.cli.upload_events_to_r2"


class TestUploadCommand:
    """upload 명령 테스트."""

    def test_upload_all_targets(self, tmp_path: Path) -> None:
        """--target all -> R2와 D1 모두 호출."""
        config_path = _write_config(tmp_path)
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        _write_jsonl(input_dir / "2024-01-15.jsonl", [_sample_event("1")])

        with (
            patch(_MOCK_D1_AUTH),
            patch(_MOCK_WRANGLER),
            patch(
                _MOCK_R2_UPLOAD, return_value=_make_r2_result(files_uploaded=1, bytes_total=100)
            ) as mock_r2,
            patch(
                _MOCK_INSERT_DL, return_value=_make_dl_results(rows_inserted=1)
            ) as mock_d1_dl,
            patch(
                _MOCK_COMPUTE_STATS_FROM_DL, return_value=[_make_daily_stats_row(count=1)]
            ),
            patch(
                _MOCK_INSERT_STATS, return_value=_make_d1_result(rows_inserted=1)
            ) as mock_d1_stats,
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--date",
                    "2024-01-15",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "all",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code == 0, result.output
            assert "Upload complete" in result.output
            mock_r2.assert_called_once()
            mock_d1_dl.assert_called_once()
            mock_d1_stats.assert_called_once()

    def test_upload_r2_only(self, tmp_path: Path) -> None:
        """--target r2 -> R2만 호출."""
        config_path = _write_config(tmp_path)
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        _write_jsonl(input_dir / "2024-01-15.jsonl", [_sample_event("1")])

        with (
            patch(_MOCK_WRANGLER),
            patch(
                _MOCK_R2_UPLOAD, return_value=_make_r2_result(files_uploaded=1, bytes_total=50)
            ) as mock_r2,
            patch(_MOCK_INSERT_DL) as mock_d1_dl,
            patch(_MOCK_INSERT_STATS) as mock_d1_stats,
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--date",
                    "2024-01-15",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "r2",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code == 0, result.output
            mock_r2.assert_called_once()
            mock_d1_dl.assert_not_called()
            mock_d1_stats.assert_not_called()

    def test_upload_d1_only(self, tmp_path: Path) -> None:
        """--target d1 -> D1만 호출."""
        config_path = _write_config(tmp_path)
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        _write_jsonl(input_dir / "2024-01-15.jsonl", [_sample_event("1")])

        with (
            patch(_MOCK_D1_AUTH),
            patch(_MOCK_R2_UPLOAD) as mock_r2,
            patch(
                _MOCK_INSERT_DL, return_value=_make_dl_results(rows_inserted=1)
            ) as mock_d1_dl,
            patch(
                _MOCK_COMPUTE_STATS_FROM_DL, return_value=[_make_daily_stats_row(count=1)]
            ),
            patch(
                _MOCK_INSERT_STATS, return_value=_make_d1_result(rows_inserted=1)
            ) as mock_d1_stats,
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--date",
                    "2024-01-15",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "d1",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code == 0, result.output
            mock_r2.assert_not_called()
            mock_d1_dl.assert_called_once()
            mock_d1_stats.assert_called_once()

    def test_upload_dry_run(self, tmp_path: Path) -> None:
        """--dry-run -> dry_run=True 전달."""
        config_path = _write_config(tmp_path)
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        _write_jsonl(input_dir / "2024-01-15.jsonl", [_sample_event("1")])

        with (
            patch(_MOCK_D1_AUTH),
            patch(_MOCK_WRANGLER),
            patch(_MOCK_R2_UPLOAD, return_value=_make_r2_result(dry_run=True)) as mock_r2,
            patch(
                _MOCK_INSERT_DL, return_value=_make_dl_results(dry_run=True)
            ) as mock_d1_dl,
            patch(
                _MOCK_COMPUTE_STATS_FROM_DL, return_value=[_make_daily_stats_row(count=1)]
            ),
            patch(_MOCK_INSERT_STATS, return_value=_make_d1_result(dry_run=True)) as mock_d1_stats,
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--date",
                    "2024-01-15",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "all",
                    "--dry-run",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code == 0, result.output
            assert "DRY RUN" in result.output

            # dry_run=True가 전달되었는지 확인
            _, r2_kwargs = mock_r2.call_args
            assert r2_kwargs["dry_run"] is True

            _, d1_kwargs = mock_d1_dl.call_args
            assert d1_kwargs["dry_run"] is True

            _, stats_kwargs = mock_d1_stats.call_args
            assert stats_kwargs["dry_run"] is True

    def test_upload_date_range(self, tmp_path: Path) -> None:
        """--start-date/--end-date -> 여러 날짜 처리."""
        config_path = _write_config(tmp_path)
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        _write_jsonl(input_dir / "2024-01-15.jsonl", [_sample_event("1")])
        _write_jsonl(input_dir / "2024-01-16.jsonl", [_sample_event("2")])

        with (
            patch(_MOCK_D1_AUTH),
            patch(_MOCK_WRANGLER),
            patch(_MOCK_R2_UPLOAD, return_value=_make_r2_result(files_uploaded=1)) as mock_r2,
            patch(_MOCK_INSERT_DL, return_value=_make_dl_results(rows_inserted=1)),
            patch(_MOCK_COMPUTE_STATS_FROM_DL, return_value=[_make_daily_stats_row(count=1)]),
            patch(_MOCK_INSERT_STATS, return_value=_make_d1_result(rows_inserted=1)),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--start-date",
                    "2024-01-15",
                    "--end-date",
                    "2024-01-16",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "all",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code == 0, result.output
            assert "dates_processed=2" in result.output
            assert mock_r2.call_count == 2

    def test_upload_missing_jsonl(self, tmp_path: Path) -> None:
        """JSONL 파일 없을 때 -> 경고 + 스킵."""
        config_path = _write_config(tmp_path)
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        # JSONL 파일을 생성하지 않음

        with (
            patch(_MOCK_D1_AUTH),
            patch(_MOCK_WRANGLER),
            patch(_MOCK_R2_UPLOAD) as mock_r2,
            patch(_MOCK_INSERT_DL) as mock_d1_dl,
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--date",
                    "2024-01-15",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "all",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code == 0, result.output
            assert "SKIP" in result.output
            assert "dates_skipped=1" in result.output
            mock_r2.assert_not_called()
            mock_d1_dl.assert_not_called()

    def test_upload_nonzero_exit_on_errors(self, tmp_path: Path) -> None:
        """업로드 에러 발생 시 exit_code != 0."""
        config_path = _write_config(tmp_path)
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        _write_jsonl(input_dir / "2024-01-15.jsonl", [_sample_event("1")])

        with (
            patch(_MOCK_D1_AUTH),
            patch(_MOCK_WRANGLER),
            patch(
                _MOCK_R2_UPLOAD,
                return_value=_make_r2_result(
                    files_uploaded=0, errors=["upload failed"]
                ),
            ),
            patch(
                _MOCK_INSERT_DL, return_value=_make_dl_results(rows_inserted=1)
            ),
            patch(_MOCK_COMPUTE_STATS_FROM_DL, return_value=[_make_daily_stats_row(count=1)]),
            patch(
                _MOCK_INSERT_STATS, return_value=_make_d1_result(rows_inserted=1)
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--date",
                    "2024-01-15",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "all",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code != 0
            assert "Upload complete" in result.output

    def test_upload_skips_daily_stats_when_dl_errors(self, tmp_path: Path) -> None:
        """DL 적재 에러가 있으면 daily_stats 갱신을 수행하지 않는다."""
        config_path = _write_config(tmp_path)
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        _write_jsonl(input_dir / "2024-01-15.jsonl", [_sample_event("1")])

        with (
            patch(_MOCK_D1_AUTH),
            patch(
                _MOCK_INSERT_DL,
                return_value=_make_dl_results(rows_inserted=0, errors=["dl insert failed"]),
            ),
            patch(_MOCK_INSERT_STATS) as mock_d1_stats,
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--date",
                    "2024-01-15",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "d1",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code != 0
            assert "skip daily stats" in result.output
            mock_d1_stats.assert_not_called()

    def test_upload_skips_daily_stats_when_dl_rows_skipped(self, tmp_path: Path) -> None:
        """DL rows_skipped가 있으면 daily_stats 갱신을 수행하지 않는다."""
        config_path = _write_config(tmp_path)
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        _write_jsonl(input_dir / "2024-01-15.jsonl", [_sample_event("1")])

        with (
            patch(_MOCK_D1_AUTH),
            patch(
                _MOCK_INSERT_DL,
                return_value=_make_dl_results(rows_inserted=1, rows_skipped=1),
            ),
            patch(_MOCK_INSERT_STATS) as mock_d1_stats,
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--date",
                    "2024-01-15",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "d1",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code != 0
            assert "skip daily stats" in result.output
            mock_d1_stats.assert_not_called()

    def test_upload_d1_auth_missing(self, tmp_path: Path) -> None:
        """D1 인증 실패 -> 에러 종료."""
        config_path = _write_config(
            tmp_path,
            d1={"database_id": "", "account_id": "", "api_token": ""},
        )
        input_dir = tmp_path / "data"
        input_dir.mkdir()
        _write_jsonl(input_dir / "2024-01-15.jsonl", [_sample_event("1")])

        with patch(
            _MOCK_D1_AUTH,
            side_effect=RuntimeError("D1 auth config missing: account_id, database_id, api_token"),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "upload",
                    "--date",
                    "2024-01-15",
                    "--input-dir",
                    str(input_dir),
                    "--target",
                    "d1",
                    "--config",
                    str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code != 0
            assert "D1 auth error" in result.output


class TestLoadJsonl:
    """_load_jsonl 함수 직접 테스트."""

    def test_load_jsonl(self, tmp_path: Path) -> None:
        """정상 JSONL 파일 로딩."""
        jsonl_path = tmp_path / "test.jsonl"
        events_data = [_sample_event("1"), _sample_event("2")]
        _write_jsonl(jsonl_path, events_data)

        events, errors = _load_jsonl(jsonl_path)
        assert len(events) == 2
        assert errors == 0
        assert events[0].id == "1"
        assert events[1].id == "2"

    def test_load_jsonl_with_errors(self, tmp_path: Path) -> None:
        """파싱 에러 포함 JSONL 파일 로딩."""
        jsonl_path = tmp_path / "test.jsonl"
        with open(jsonl_path, "wb") as f:
            # 정상 이벤트
            f.write(orjson.dumps(_sample_event("1")))
            f.write(b"\n")
            # 잘못된 JSON
            f.write(b"this is not json\n")
            # 정상 이벤트
            f.write(orjson.dumps(_sample_event("3")))
            f.write(b"\n")

        events, errors = _load_jsonl(jsonl_path)
        assert len(events) == 2
        assert errors == 1

    def test_load_jsonl_empty_file(self, tmp_path: Path) -> None:
        """빈 JSONL 파일 로딩."""
        jsonl_path = tmp_path / "empty.jsonl"
        jsonl_path.write_bytes(b"")

        events, errors = _load_jsonl(jsonl_path)
        assert len(events) == 0
        assert errors == 0


# ── verify-aggregation 명령 테스트 ────────────────────


_MOCK_CONSISTENCY = "gharchive_etl.quality.check_daily_stats_consistency"


class TestVerifyAggregation:
    """verify-aggregation 명령 테스트."""

    def test_verify_success(self, tmp_path: Path) -> None:
        """정합성 검증 통과 시 exit_code == 0."""
        config_path = _write_config(tmp_path)
        report = ConsistencyReport(
            batch_date="2024-01-15",
            total_event_rows=10,
            total_daily_stats=3,
            mismatched_keys=0,
            missing_in_stats=0,
            extra_in_stats=0,
            passed=True,
        )

        with patch(_MOCK_CONSISTENCY, return_value=report):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "verify-aggregation",
                    "--date", "2024-01-15",
                    "--config", str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code == 0, result.output
            assert "PASSED" in result.output

    def test_verify_failure(self, tmp_path: Path) -> None:
        """정합성 검증 실패 시 exit_code != 0."""
        config_path = _write_config(tmp_path)
        report = ConsistencyReport(
            batch_date="2024-01-15",
            total_event_rows=10,
            total_daily_stats=3,
            mismatched_keys=2,
            missing_in_stats=1,
            extra_in_stats=0,
            passed=False,
        )

        with patch(_MOCK_CONSISTENCY, return_value=report):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "verify-aggregation",
                    "--date", "2024-01-15",
                    "--config", str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code != 0
            assert "FAILED" in result.output


# ── quality-check 명령 테스트 ─────────────────────────


_MOCK_QUALITY = "gharchive_etl.quality.run_quality_checks"


class TestQualityCheck:
    """quality-check 명령 테스트."""

    def test_quality_check_success(self, tmp_path: Path) -> None:
        """품질 검증 통과 시 exit_code == 0."""
        config_path = _write_config(tmp_path)
        report = QualityReport(
            batch_date="2024-01-15",
            passed=True,
            total_rules=6,
            failed_rules=0,
            results=[
                QualityRuleResult(
                    rule_id="DQ001", severity="ERROR",
                    passed=True, checked_rows=10, failed_rows=0,
                ),
            ],
        )

        with patch(_MOCK_QUALITY, return_value=report):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "quality-check",
                    "--date", "2024-01-15",
                    "--config", str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code == 0, result.output
            assert "PASSED" in result.output

    def test_quality_check_failure(self, tmp_path: Path) -> None:
        """품질 검증 실패 시 exit_code != 0 + failed rule_id 출력."""
        config_path = _write_config(tmp_path)
        report = QualityReport(
            batch_date="2024-01-15",
            passed=False,
            total_rules=6,
            failed_rules=1,
            results=[
                QualityRuleResult(
                    rule_id="DQ001", severity="ERROR",
                    passed=False, checked_rows=10, failed_rows=2,
                    message="필수 필드 null/empty 검사: 2건 실패",
                ),
                QualityRuleResult(
                    rule_id="DQ002", severity="ERROR",
                    passed=True, checked_rows=10, failed_rows=0,
                ),
            ],
        )

        with patch(_MOCK_QUALITY, return_value=report):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "quality-check",
                    "--date", "2024-01-15",
                    "--config", str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code != 0
            assert "FAILED" in result.output
            assert "DQ001" in result.output

    def test_quality_check_report_json(self, tmp_path: Path) -> None:
        """--report-json 옵션 → JSON 파일 생성 확인."""
        config_path = _write_config(tmp_path)
        report_path = tmp_path / "report" / "quality.json"
        report = QualityReport(
            batch_date="2024-01-15",
            passed=True,
            total_rules=6,
            failed_rules=0,
            results=[],
        )

        with patch(_MOCK_QUALITY, return_value=report):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "quality-check",
                    "--date", "2024-01-15",
                    "--report-json", str(report_path),
                    "--config", str(config_path),
                    "--no-json-log",
                ],
            )

            assert result.exit_code == 0, result.output
            assert report_path.exists()
            data = orjson.loads(report_path.read_bytes())
            assert data["batch_date"] == "2024-01-15"
            assert data["passed"] is True
