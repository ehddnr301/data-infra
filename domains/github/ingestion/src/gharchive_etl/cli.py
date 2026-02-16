"""click CLI 엔트리포인트.

gharchive-etl fetch 명령으로 GitHub Archive 이벤트를 수집합니다.
"""

from __future__ import annotations

import logging
import sys
from datetime import date as date_type
from datetime import datetime, timedelta
from pathlib import Path

import click
import orjson

from gharchive_etl.config import load_config
from gharchive_etl.d1 import _validate_d1_auth, insert_daily_stats, insert_events
from gharchive_etl.downloader import HourStats, process_hour
from gharchive_etl.logging_config import setup_logging
from gharchive_etl.models import GitHubEvent
from gharchive_etl.r2 import _check_wrangler_installed, upload_events_to_r2
from gharchive_etl.transformer import compute_daily_stats, transform_events

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> date_type:
    """YYYY-MM-DD 형식의 날짜를 파싱한다."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise click.BadParameter(f"날짜 형식이 올바르지 않습니다: {value} (YYYY-MM-DD)") from exc


def _date_range(start: date_type, end: date_type) -> list[date_type]:
    """시작일~종료일 범위의 날짜 리스트를 반환한다."""
    days = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(days)]


@click.group()
@click.version_option(version="0.1.0", prog_name="gharchive-etl")
def main() -> None:
    """GitHub Archive ETL - 특정 org의 GitHub 이벤트를 수집합니다."""


@main.command()
@click.option("--date", "single_date", default=None, help="수집 대상 날짜 (예: 2024-01-15)")
@click.option("--start-date", default=None, help="범위 시작 날짜 (예: 2024-01-01)")
@click.option("--end-date", default=None, help="범위 종료 날짜 (예: 2024-01-31)")
@click.option("--start-hour", default=0, type=int, help="시작 시간 (0~23, 기본: 0)")
@click.option("--end-hour", default=23, type=int, help="종료 시간 (0~23, 기본: 23)")
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="설정 파일 경로 (기본: 패키지 내부 config.yaml)",
)
@click.option(
    "--output-jsonl",
    default=None,
    type=click.Path(path_type=Path),
    help="필터 통과 이벤트를 JSONL 파일로 출력",
)
@click.option("--json-log/--no-json-log", default=True, help="JSON 로그 포맷 (기본: 활성)")
def fetch(
    single_date: str | None,
    start_date: str | None,
    end_date: str | None,
    start_hour: int,
    end_hour: int,
    config_path: Path | None,
    output_jsonl: Path | None,
    json_log: bool,
) -> None:
    """지정된 날짜의 GitHub Archive 이벤트를 수집합니다.

    해당 날짜의 시간별 파일을 순회하며, 설정된 target_orgs에
    해당하는 이벤트만 필터링합니다.
    """
    setup_logging(json_format=json_log)

    # ── 입력 검증 ──
    _validate_date_options(single_date, start_date, end_date)
    _validate_hour_range(start_hour, end_hour)

    # 날짜 범위 결정
    if single_date:
        dates = [_parse_date(single_date)]
    else:
        assert start_date is not None and end_date is not None
        s = _parse_date(start_date)
        e = _parse_date(end_date)
        if s > e:
            raise click.BadParameter(f"start-date({s})가 end-date({e})보다 늦습니다")
        dates = _date_range(s, e)

    # 설정 로딩
    config = load_config(config_path)

    # ── 실행 ──
    total_stats: list[HourStats] = []
    total_filtered = 0
    failed_hours: list[str] = []
    jsonl_file = None

    try:
        if output_jsonl:
            output_jsonl.parent.mkdir(parents=True, exist_ok=True)
            jsonl_file = open(output_jsonl, "wb")  # noqa: SIM115

        for d in dates:
            date_str = d.strftime("%Y-%m-%d")
            for hour in range(start_hour, end_hour + 1):
                click.echo(f"[{hour:02d}/{end_hour:02d}] Processing {date_str}-{hour}...")

                try:
                    events, stats = process_hour(date_str, hour, config)
                except Exception as exc:
                    logger.error(
                        "Unexpected error for %s-%d: %s",
                        date_str,
                        hour,
                        exc,
                        extra={
                            "event_code": "NETWORK_ERROR",
                            "date": date_str,
                            "hour": hour,
                        },
                    )
                    failed_hours.append(f"{date_str}-{hour}")
                    total_stats.append(HourStats(date=date_str, hour=hour, error=str(exc)))
                    continue

                total_stats.append(stats)

                if stats.error:
                    failed_hours.append(f"{date_str}-{hour}")
                    continue

                total_filtered += len(events)

                # JSONL 출력 (필터 통과 이벤트만)
                if jsonl_file and events:
                    for event in events:
                        jsonl_file.write(orjson.dumps(event.model_dump(mode="json")))
                        jsonl_file.write(b"\n")

    finally:
        if jsonl_file:
            jsonl_file.close()

    # ── 최종 요약 ──
    _log_summary(total_stats, total_filtered, failed_hours, output_jsonl)

    if failed_hours:
        sys.exit(1)


def _validate_date_options(
    single_date: str | None,
    start_date: str | None,
    end_date: str | None,
) -> None:
    """날짜 옵션 상호배타 검증."""
    has_single = single_date is not None
    has_range = start_date is not None or end_date is not None

    if has_single and has_range:
        raise click.UsageError("--date와 --start-date/--end-date는 동시에 사용할 수 없습니다")

    if not has_single and not has_range:
        raise click.UsageError("--date 또는 --start-date/--end-date를 지정하세요")

    if has_range and (start_date is None or end_date is None):
        raise click.UsageError("--start-date와 --end-date를 모두 지정하세요")


def _validate_hour_range(start_hour: int, end_hour: int) -> None:
    """시간 범위 검증."""
    if not (0 <= start_hour <= 23):
        raise click.BadParameter(f"start-hour는 0~23 범위여야 합니다: {start_hour}")
    if not (0 <= end_hour <= 23):
        raise click.BadParameter(f"end-hour는 0~23 범위여야 합니다: {end_hour}")
    if start_hour > end_hour:
        raise click.BadParameter(f"start-hour({start_hour})가 end-hour({end_hour})보다 큽니다")


def _log_summary(
    stats_list: list[HourStats],
    total_filtered: int,
    failed_hours: list[str],
    output_jsonl: Path | None,
) -> None:
    """최종 집계 요약 로그를 출력한다."""
    total_downloaded = sum(s.downloaded for s in stats_list)
    total_parsed = sum(s.parsed for s in stats_list)
    total_invalid = sum(s.invalid for s in stats_list)
    total_duration_ms = sum(s.duration_ms for s in stats_list)

    summary_msg = (
        f"Fetch complete: "
        f"hours={len(stats_list)}, "
        f"downloaded={total_downloaded}, "
        f"parsed={total_parsed}, "
        f"invalid={total_invalid}, "
        f"filtered={total_filtered}, "
        f"failed_hours={len(failed_hours)}, "
        f"duration={total_duration_ms:.0f}ms"
    )

    log_extra = {
        "event_code": "FETCH_SUMMARY",
        "counts": {
            "hours_processed": len(stats_list),
            "downloaded": total_downloaded,
            "parsed": total_parsed,
            "invalid": total_invalid,
            "filtered_in": total_filtered,
            "failed_hours": len(failed_hours),
        },
        "duration_ms": total_duration_ms,
        "failed_hours": failed_hours if failed_hours else None,
    }

    if output_jsonl:
        summary_msg += f", output={output_jsonl}"

    if failed_hours:
        logger.warning(summary_msg, extra=log_extra)
        click.echo(f"Failed hours: {', '.join(failed_hours)}", err=True)
    else:
        logger.info(summary_msg, extra=log_extra)

    click.echo(summary_msg)


def _load_jsonl(path: Path) -> tuple[list[GitHubEvent], int]:
    """JSONL 파일을 읽어 GitHubEvent 리스트로 변환한다.

    Args:
        path: JSONL 파일 경로

    Returns:
        (events_list, error_count) 튜플
    """
    events: list[GitHubEvent] = []
    errors = 0
    with open(path, "rb") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = orjson.loads(line)
                event = GitHubEvent.model_validate(data)
                events.append(event)
            except Exception as exc:
                errors += 1
                logger.warning("Parse error at %s line %d: %s", path.name, line_no, exc)
    return events, errors


@main.command()
@click.option("--date", "single_date", default=None, help="업로드 대상 날짜 (예: 2024-01-15)")
@click.option("--start-date", default=None, help="범위 시작 날짜 (예: 2024-01-01)")
@click.option("--end-date", default=None, help="범위 종료 날짜 (예: 2024-01-31)")
@click.option(
    "--input-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="JSONL 파일이 있는 디렉터리 경로",
)
@click.option(
    "--target",
    type=click.Choice(["r2", "d1", "all"]),
    default="all",
    help="업로드 대상 (r2, d1, all 중 택1, 기본: all)",
)
@click.option("--dry-run", is_flag=True, default=False, help="실제 업로드 없이 시뮬레이션")
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="설정 파일 경로 (기본: 패키지 내부 config.yaml)",
)
@click.option("--json-log/--no-json-log", default=True, help="JSON 로그 포맷 (기본: 활성)")
def upload(
    single_date: str | None,
    start_date: str | None,
    end_date: str | None,
    input_dir: Path,
    target: str,
    dry_run: bool,
    config_path: Path | None,
    json_log: bool,
) -> None:
    """JSONL 파일을 R2/D1에 업로드합니다.

    fetch 명령으로 생성된 JSONL 파일을 읽어 Cloudflare R2 및/또는 D1에 적재합니다.
    """
    setup_logging(json_format=json_log)

    # ── 입력 검증 ──
    _validate_date_options(single_date, start_date, end_date)

    # 날짜 범위 결정
    if single_date:
        dates = [_parse_date(single_date)]
    else:
        assert start_date is not None and end_date is not None
        s = _parse_date(start_date)
        e = _parse_date(end_date)
        if s > e:
            raise click.BadParameter(f"start-date({s})가 end-date({e})보다 늦습니다")
        dates = _date_range(s, e)

    # 설정 로딩
    config = load_config(config_path)

    # ── 사전 검증 ──
    if target in ("d1", "all"):
        try:
            _validate_d1_auth(config.d1)
        except RuntimeError as exc:
            click.echo(f"D1 auth error: {exc}", err=True)
            sys.exit(1)

    if target in ("r2", "all"):
        try:
            _check_wrangler_installed()
        except RuntimeError as exc:
            click.echo(f"Wrangler error: {exc}", err=True)
            sys.exit(1)

    # ── 실행 ──
    total_parse_errors = 0
    total_events_processed = 0
    total_upload_errors: list[str] = []
    dates_processed = 0
    dates_skipped = 0

    for batch_date in dates:
        date_str = batch_date.strftime("%Y-%m-%d")
        jsonl_path = input_dir / f"{date_str}.jsonl"

        if not jsonl_path.exists():
            logger.warning("JSONL file not found, skipping: %s", jsonl_path)
            click.echo(f"[SKIP] {date_str}: {jsonl_path} not found")
            dates_skipped += 1
            continue

        click.echo(f"[LOAD] {date_str}: loading {jsonl_path.name}...")
        events, parse_errors = _load_jsonl(jsonl_path)
        total_parse_errors += parse_errors
        total_events_processed += len(events)

        if parse_errors:
            click.echo(f"  parse errors: {parse_errors}")

        if not events:
            click.echo(f"  no events to upload for {date_str}")
            continue

        # R2 업로드
        if target in ("r2", "all"):
            click.echo(f"  [R2] uploading {len(events)} events...")
            r2_result = upload_events_to_r2(events, date_str, config.r2, dry_run=dry_run)
            click.echo(
                f"  [R2] files={r2_result.files_uploaded}, "
                f"bytes={r2_result.bytes_total}, "
                f"errors={len(r2_result.errors)}"
            )
            total_upload_errors.extend(r2_result.errors)

        # D1 적재
        if target in ("d1", "all"):
            click.echo(f"  [D1] transforming {len(events)} events...")
            rows, _transform_stats = transform_events(events, date_str)

            click.echo(f"  [D1] inserting {len(rows)} event rows...")
            events_result = insert_events(rows, config.d1, dry_run=dry_run)
            click.echo(
                f"  [D1] events inserted={events_result.rows_inserted}, "
                f"errors={len(events_result.errors)}"
            )
            total_upload_errors.extend(events_result.errors)

            daily = compute_daily_stats(rows)
            click.echo(f"  [D1] upserting {len(daily)} daily stats...")
            stats_result = insert_daily_stats(daily, config.d1, dry_run=dry_run)
            click.echo(
                f"  [D1] stats inserted={stats_result.rows_inserted}, "
                f"errors={len(stats_result.errors)}"
            )
            total_upload_errors.extend(stats_result.errors)

        dates_processed += 1

    # ── 최종 요약 ──
    summary = (
        f"Upload complete: "
        f"dates_processed={dates_processed}, "
        f"dates_skipped={dates_skipped}, "
        f"events={total_events_processed}, "
        f"parse_errors={total_parse_errors}"
    )
    if dry_run:
        summary += " (DRY RUN)"

    click.echo(summary)
    logger.info(summary)

    if total_upload_errors:
        click.echo(f"ERROR: {len(total_upload_errors)} upload error(s) occurred", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
