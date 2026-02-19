"""Discord ETL CLI.

discord-etl fetch --config config.yaml --json-log
discord-etl fetch --channel-id <ID> --config config.yaml
discord-etl upload --date 2024-06-15 --input-dir data/
discord-etl quality-check --date 2024-06-15
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
import orjson

from discord_etl.client import DiscordClient
from discord_etl.collector import CollectStats, collect_channel
from discord_etl.config import load_config
from discord_etl.d1 import insert_messages_batch, query_rows, save_watermark
from discord_etl.logging_config import setup_logging
from discord_etl.models import DiscordMessage
from discord_etl.r2 import upload_to_r2
from discord_etl.transformer import transform_message

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """Discord 메시지 수집 ETL."""


@main.command()
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path),
              default=None, help="설정 파일 경로 (기본: config.yaml)")
@click.option("--channel-id", default=None, help="단일 채널 ID (지정 시 해당 채널만 수집)")
@click.option("--dry-run", is_flag=True, help="D1 저장 없이 수집만 시뮬레이션")
@click.option("--output-dir", type=click.Path(path_type=Path), default=None,
              help="JSONL 출력 디렉토리 (설정 시 D1 대신 파일 저장)")
@click.option("--json-log", is_flag=True, help="JSON 형태 로그 출력")
def fetch(
    config_path: Path | None,
    channel_id: str | None,
    dry_run: bool,
    output_dir: Path | None,
    json_log: bool,
) -> None:
    """Discord 채널 메시지를 수집한다."""
    setup_logging(json_format=json_log)

    config = load_config(config_path)
    client = DiscordClient(config.discord)

    # 대상 채널 결정
    if channel_id:
        channels = [ch for ch in config.channels if ch.id == channel_id]
        if not channels:
            click.echo(f"Channel ID {channel_id} not found in config", err=True)
            sys.exit(1)
    else:
        channels = config.channels

    # output_dir 생성
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    # 채널별 수집
    all_stats: list[CollectStats] = []
    for ch in channels:
        logger.info("Starting collection: %s (%s)", ch.name, ch.id)
        stats = collect_channel(
            ch, client, config,
            dry_run=dry_run,
            output_dir=output_dir,
        )
        all_stats.append(stats)
        logger.info(
            "Channel done: %s — fetched=%d, new=%d, stored=%d, %.1fs",
            ch.name, stats.messages_fetched, stats.messages_new,
            stats.messages_stored, stats.duration_ms / 1000,
        )

    # 최종 요약
    _log_summary(all_stats, dry_run)

    # 에러 채널이 있으면 exit code 1
    if any(s.error for s in all_stats):
        sys.exit(1)


@main.command("init-db")
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path),
              default=None, help="설정 파일 경로 (기본: config.yaml)")
@click.option("--json-log", is_flag=True, help="JSON 형태 로그 출력")
def init_db(config_path: Path | None, json_log: bool) -> None:
    """D1에 discord_messages, discord_watermarks 테이블을 생성한다."""
    from discord_etl.d1 import _d1_query

    setup_logging(json_format=json_log)
    config = load_config(config_path)

    ddl_statements = [
        (
            "discord_messages",
            "CREATE TABLE IF NOT EXISTS discord_messages ("
            "id TEXT PRIMARY KEY, "
            "channel_id TEXT NOT NULL, "
            "channel_name TEXT NOT NULL, "
            "author_id TEXT NOT NULL, "
            "author_username TEXT NOT NULL, "
            "content TEXT NOT NULL DEFAULT '', "
            "message_type INTEGER NOT NULL DEFAULT 0, "
            "referenced_message_id TEXT, "
            "attachment_count INTEGER NOT NULL DEFAULT 0, "
            "embed_count INTEGER NOT NULL DEFAULT 0, "
            "reaction_count INTEGER NOT NULL DEFAULT 0, "
            "mention_count INTEGER NOT NULL DEFAULT 0, "
            "pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1)), "
            "created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'), "
            "edited_at TEXT, "
            "batch_date TEXT NOT NULL CHECK (batch_date GLOB '????-??-??')"
            ")",
        ),
        (
            "discord_watermarks",
            "CREATE TABLE IF NOT EXISTS discord_watermarks ("
            "channel_id TEXT PRIMARY KEY, "
            "channel_name TEXT NOT NULL, "
            "last_message_id TEXT NOT NULL DEFAULT '0', "
            "scan_cursor TEXT, "
            "last_collected_at TEXT NOT NULL CHECK (last_collected_at GLOB '????-??-??T??:??:??*'), "
            "total_collected INTEGER NOT NULL DEFAULT 0"
            ")",
        ),
        (
            "idx_discord_messages_channel_created",
            "CREATE INDEX IF NOT EXISTS idx_discord_messages_channel_created "
            "ON discord_messages(channel_id, created_at DESC)",
        ),
        (
            "idx_discord_messages_author",
            "CREATE INDEX IF NOT EXISTS idx_discord_messages_author "
            "ON discord_messages(author_id, created_at DESC)",
        ),
        (
            "idx_discord_messages_batch",
            "CREATE INDEX IF NOT EXISTS idx_discord_messages_batch "
            "ON discord_messages(batch_date)",
        ),
        (
            "idx_discord_messages_reply",
            "CREATE INDEX IF NOT EXISTS idx_discord_messages_reply "
            "ON discord_messages(referenced_message_id) "
            "WHERE referenced_message_id IS NOT NULL",
        ),
    ]

    for name, sql in ddl_statements:
        try:
            _d1_query(sql, [], config.d1)
            click.echo(f"[OK] {name}")
        except Exception as e:
            click.echo(f"[FAIL] {name}: {e}", err=True)
            sys.exit(1)

    click.echo("D1 schema initialized successfully.")


@main.command()
@click.option("--date", required=True, help="배치 날짜 (YYYY-MM-DD)")
@click.option("--input-dir", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--target", type=click.Choice(["r2", "d1", "all"]), default="all")
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--json-log", is_flag=True)
def upload(
    date: str,
    input_dir: Path,
    target: str,
    config_path: Path | None,
    json_log: bool,
) -> None:
    """수집된 JSONL을 R2/D1에 업로드한다."""
    setup_logging(json_format=json_log)
    config = load_config(config_path)

    errors: list[str] = []

    # 채널별 디렉토리 순회
    channel_dirs = sorted(p for p in input_dir.iterdir() if p.is_dir())
    if not channel_dirs:
        click.echo("No channel directories found", err=True)
        sys.exit(1)

    for channel_dir in channel_dirs:
        channel_name = channel_dir.name
        jsonl_path = channel_dir / f"{date}.jsonl"
        if not jsonl_path.exists():
            logger.warning("No JSONL for %s on %s", channel_name, date)
            continue

        # R2 업로드
        if target in ("r2", "all"):
            ok = upload_to_r2(jsonl_path, channel_name=channel_name, date=date)
            if ok:
                logger.info("R2 upload done: %s/%s", channel_name, date)
            else:
                errors.append(f"R2 upload failed: {channel_name}")

        # D1 적재
        if target in ("d1", "all"):
            raw_lines = jsonl_path.read_bytes().strip().split(b"\n")
            messages: list[DiscordMessage] = []
            max_id = "0"

            for line in raw_lines:
                if not line:
                    continue
                raw = orjson.loads(line)
                row = transform_message(raw, channel_name=channel_name, batch_date=date)
                msg = DiscordMessage(**row)
                messages.append(msg)
                if int(msg.id) > int(max_id):
                    max_id = msg.id

            if messages:
                result = insert_messages_batch(messages, config.d1)
                logger.info(
                    "D1 insert: %s — %d/%d rows",
                    channel_name, result.rows_inserted, len(messages),
                )
                if result.errors:
                    errors.extend(result.errors)

                # watermark 갱신: 채널 ID는 첫 메시지에서 가져옴
                channel_id = messages[0].channel_id
                save_watermark(
                    channel_id, max_id, config.d1,
                    channel_name=channel_name,
                    total_collected=len(messages),
                )

    if errors:
        for err in errors:
            click.echo(f"[ERROR] {err}", err=True)
        sys.exit(1)

    click.echo(f"Upload complete: {date}")


@main.command("quality-check")
@click.option("--date", required=True)
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--json-log", is_flag=True)
def quality_check(
    date: str,
    config_path: Path | None,
    json_log: bool,
) -> None:
    """수집 데이터 품질을 검증한다."""
    setup_logging(json_format=json_log)
    config = load_config(config_path)

    passed = True

    # 1. batch_date별 메시지 수 조회
    rows = query_rows(
        "SELECT channel_name, COUNT(*) as cnt "
        "FROM discord_messages WHERE batch_date = ? "
        "GROUP BY channel_name",
        [date], config.d1,
    )

    if not rows:
        click.echo(f"[FAIL] No messages found for {date}", err=True)
        sys.exit(1)

    total = 0
    for row in rows:
        cnt = row["cnt"]
        total += cnt
        click.echo(f"[OK] {row['channel_name']}: {cnt} messages")

    click.echo(f"Total: {total} messages for {date}")

    # 2. watermark 정합성 검증
    wm_rows = query_rows(
        "SELECT channel_id, channel_name, last_message_id "
        "FROM discord_watermarks",
        [], config.d1,
    )

    for wm in wm_rows:
        if not wm.get("last_message_id") or wm["last_message_id"] == "0":
            click.echo(
                f"[WARN] Watermark not set for {wm.get('channel_name', wm['channel_id'])}",
                err=True,
            )
            passed = False

    if not passed:
        sys.exit(1)

    click.echo("Quality check passed.")


def _log_summary(all_stats: list[CollectStats], dry_run: bool) -> None:
    """실행 요약을 로깅한다."""
    total_fetched = sum(s.messages_fetched for s in all_stats)
    total_new = sum(s.messages_new for s in all_stats)
    total_stored = sum(s.messages_stored for s in all_stats)
    errors = [s for s in all_stats if s.error]

    logger.info(
        "Fetch summary: channels=%d, fetched=%d, new=%d, stored=%d, "
        "errors=%d, dry_run=%s",
        len(all_stats), total_fetched, total_new, total_stored,
        len(errors), dry_run,
        extra={
            "event_code": "FETCH_SUMMARY",
            "count": total_stored,
        },
    )
