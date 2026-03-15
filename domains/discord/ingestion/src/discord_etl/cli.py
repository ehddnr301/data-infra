"""Discord ETL CLI.

discord-etl fetch --config config.yaml --json-log
discord-etl fetch --channel-id <ID> --config config.yaml
discord-etl upload --date 2024-06-15 --input-dir data/
discord-etl quality-check --date 2024-06-15
"""

from __future__ import annotations

import logging
import random
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import click
import orjson

from discord_etl.client import DiscordApiError, DiscordClient
from discord_etl.collector import CollectStats, collect_channel
from discord_etl.config import load_config
from discord_etl.d1 import (
    get_missing_profile_count,
    insert_messages_batch,
    list_missing_profile_targets,
    query_rows,
    save_watermark,
    upsert_user_profiles_batch,
)
from discord_etl.logging_config import setup_logging
from discord_etl.models import DiscordMessage, DiscordUserProfile
from discord_etl.r2 import upload_to_r2
from discord_etl.transformer import transform_message

logger = logging.getLogger(__name__)

_HEADER_DENYLIST = {
    "authorization",
    "cookie",
    "host",
    "content-length",
}


def _resolve_template_path(config_path: Path | None, template_path: str) -> Path | None:
    if not template_path:
        return None
    p = Path(template_path)
    if p.is_absolute():
        return p
    if config_path is not None:
        return config_path.parent / p
    return Path(__file__).resolve().parents[2] / p


def _load_profile_request_headers(template_path: Path | None) -> dict[str, str]:
    if template_path is None or not template_path.exists():
        return {}
    text = template_path.read_text(encoding="utf-8")
    match = re.search(r"fetch\([^,]+,\s*(\{[\s\S]*\})\s*\);?", text)
    if not match:
        logger.warning("Invalid profile request template: %s", template_path)
        return {}
    try:
        options = orjson.loads(match.group(1))
    except Exception as e:
        logger.warning("Failed to parse profile request template: %s", e)
        return {}

    headers = options.get("headers") if isinstance(options, dict) else None
    if not isinstance(headers, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if key.lower() in _HEADER_DENYLIST:
            continue
        normalized[key] = value
    return normalized


def _marker_profile(
    user_id: str, status_code: int, fetched_at: str, message: str
) -> DiscordUserProfile:
    raw_payload = orjson.dumps({"status": status_code, "message": message}).decode()
    return DiscordUserProfile(
        user_id=user_id,
        source="users_profile_api",
        source_endpoint=f"/users/{{id}}/profile#{status_code}",
        fetched_at=fetched_at,
        raw_payload=raw_payload,
    )


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """Discord 메시지 수집 ETL."""


@main.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="설정 파일 경로 (기본: config.yaml)",
)
@click.option("--channel-id", default=None, help="단일 채널 ID (지정 시 해당 채널만 수집)")
@click.option("--dry-run", is_flag=True, help="D1 저장 없이 수집만 시뮬레이션")
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="JSONL 출력 디렉토리 (설정 시 D1 대신 파일 저장)",
)
@click.option("--batch-date", default=None, help="배치 날짜 (YYYY-MM-DD)")
@click.option("--json-log", is_flag=True, help="JSON 형태 로그 출력")
def fetch(
    config_path: Path | None,
    channel_id: str | None,
    dry_run: bool,
    output_dir: Path | None,
    batch_date: str | None,
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
            ch,
            client,
            config,
            dry_run=dry_run,
            output_dir=output_dir,
            batch_date=batch_date,
        )
        all_stats.append(stats)
        logger.info(
            "Channel done: %s — fetched=%d, new=%d, stored=%d, %.1fs",
            ch.name,
            stats.messages_fetched,
            stats.messages_new,
            stats.messages_stored,
            stats.duration_ms / 1000,
        )

    # 최종 요약
    _log_summary(all_stats, dry_run)

    # 에러 채널이 있으면 exit code 1
    if any(s.error for s in all_stats):
        sys.exit(1)


@main.command("init-db")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="설정 파일 경로 (기본: config.yaml)",
)
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
            "discord_user_profiles",
            "CREATE TABLE IF NOT EXISTS discord_user_profiles ("
            "user_id TEXT PRIMARY KEY, "
            "username TEXT, "
            "global_name TEXT, "
            "avatar TEXT, "
            "banner TEXT, "
            "accent_color INTEGER, "
            "bio TEXT, "
            "pronouns TEXT, "
            "mutual_guild_count INTEGER NOT NULL DEFAULT 0, "
            "mutual_friend_count INTEGER NOT NULL DEFAULT 0, "
            "connected_account_count INTEGER NOT NULL DEFAULT 0, "
            "source TEXT NOT NULL CHECK (source IN ('users_profile_api')), "
            "source_endpoint TEXT NOT NULL, "
            "fetched_at TEXT NOT NULL CHECK (fetched_at GLOB '????-??-??T??:??:??*'), "
            "raw_payload TEXT NOT NULL"
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
            "CREATE INDEX IF NOT EXISTS idx_discord_messages_batch ON discord_messages(batch_date)",
        ),
        (
            "idx_discord_messages_reply",
            "CREATE INDEX IF NOT EXISTS idx_discord_messages_reply "
            "ON discord_messages(referenced_message_id) "
            "WHERE referenced_message_id IS NOT NULL",
        ),
        (
            "idx_discord_user_profiles_fetched_at",
            "CREATE INDEX IF NOT EXISTS idx_discord_user_profiles_fetched_at "
            "ON discord_user_profiles(fetched_at DESC)",
        ),
        (
            "idx_discord_user_profiles_global_name",
            "CREATE INDEX IF NOT EXISTS idx_discord_user_profiles_global_name "
            "ON discord_user_profiles(global_name)",
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
                    channel_name,
                    result.rows_inserted,
                    len(messages),
                )
                if result.errors:
                    errors.extend(result.errors)
                else:
                    channel_id = messages[0].channel_id
                    save_watermark(
                        channel_id,
                        max_id,
                        config.d1,
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
        [date],
        config.d1,
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
        "SELECT channel_id, channel_name, last_message_id FROM discord_watermarks",
        [],
        config.d1,
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


@main.command("verify-profile-api")
@click.option("--user-id", required=True)
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--json-log", is_flag=True)
def verify_profile_api(user_id: str, config_path: Path | None, json_log: bool) -> None:
    setup_logging(json_format=json_log)
    config = load_config(config_path)

    guild_id = config.profile_enrichment.guild_id
    if not guild_id:
        click.echo("[FAIL] profile_enrichment.guild_id is required", err=True)
        sys.exit(1)

    client = DiscordClient(config.discord)
    now = datetime.now(tz=UTC).isoformat()
    template_path = _resolve_template_path(
        config_path,
        config.profile_enrichment.request_template_path,
    )
    request_headers = _load_profile_request_headers(template_path)

    try:
        payload = client.fetch_user_profile(
            user_id,
            guild_id,
            type=config.profile_enrichment.type,
            with_mutual_guilds=config.profile_enrichment.with_mutual_guilds,
            with_mutual_friends=config.profile_enrichment.with_mutual_friends,
            with_mutual_friends_count=config.profile_enrichment.with_mutual_friends_count,
            request_timeout_sec=config.profile_enrichment.request_timeout_sec,
            max_retries=config.profile_enrichment.max_retries,
            extra_headers=request_headers,
        )
    except DiscordApiError as e:
        click.echo(f"[FAIL] status={e.status_code} user_id={user_id}", err=True)
        sys.exit(1)

    profile = DiscordUserProfile.from_profile_response(
        payload,
        source_endpoint="/users/{id}/profile",
        fetched_at=now,
    )
    click.echo(
        f"[OK] user_id={profile.user_id} "
        f"username={profile.username or ''} "
        f"global_name={profile.global_name or ''}",
    )
    click.echo("keys=" + ",".join(sorted(payload.keys())))


@main.command("enrich-profiles")
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--json-log", is_flag=True)
def enrich_profiles(config_path: Path | None, json_log: bool) -> None:
    setup_logging(json_format=json_log)
    config = load_config(config_path)

    if not config.profile_enrichment.enabled:
        click.echo("Profile enrichment disabled. skip.")
        return

    guild_id = config.profile_enrichment.guild_id
    if not guild_id:
        click.echo("[FAIL] profile_enrichment.guild_id is required", err=True)
        sys.exit(1)

    missing_count = get_missing_profile_count(config.d1)
    if missing_count == 0:
        click.echo("No missing profile targets.")
        return

    targets = list_missing_profile_targets(config.profile_enrichment.max_users_per_run, config.d1)
    if not targets:
        click.echo("No targets selected after limit/filter.")
        return

    client = DiscordClient(config.discord)
    fetched_at = datetime.now(tz=UTC).isoformat()
    template_path = _resolve_template_path(
        config_path,
        config.profile_enrichment.request_template_path,
    )
    request_headers = _load_profile_request_headers(template_path)

    rows: list[DiscordUserProfile] = []
    skipped_401 = 0
    skipped_403 = 0
    not_found_marked = 0
    throttled_429 = 0
    failed = 0
    delay_sec = max(config.profile_enrichment.per_user_delay_sec, 0.0)

    for target in targets:
        try:
            payload = client.fetch_user_profile(
                target.user_id,
                guild_id,
                type=config.profile_enrichment.type,
                with_mutual_guilds=config.profile_enrichment.with_mutual_guilds,
                with_mutual_friends=config.profile_enrichment.with_mutual_friends,
                with_mutual_friends_count=config.profile_enrichment.with_mutual_friends_count,
                request_timeout_sec=config.profile_enrichment.request_timeout_sec,
                max_retries=config.profile_enrichment.max_retries,
                extra_headers=request_headers,
            )
        except DiscordApiError as e:
            if e.status_code == 429:
                throttled_429 += 1
                failed += 1
                logger.error(
                    "Profile fetch rate-limited: user_id=%s status=429",
                    target.user_id,
                )
                break
            if e.status_code == 404:
                rows.append(_marker_profile(target.user_id, 404, fetched_at, "profile not found"))
                not_found_marked += 1
                logger.warning("Profile not found: user_id=%s", target.user_id)
                continue
            if e.status_code == 401:
                skipped_401 += 1
                logger.warning("Profile skipped: user_id=%s status=401", target.user_id)
                continue
            if e.status_code == 403:
                skipped_403 += 1
                logger.warning("Profile skipped: user_id=%s status=403", target.user_id)
                continue
            failed += 1
            logger.error(
                "Profile fetch failed: user_id=%s status=%s", target.user_id, e.status_code
            )
            continue
        finally:
            if delay_sec > 0:
                time.sleep(delay_sec)

        profile = DiscordUserProfile.from_profile_response(
            payload,
            source_endpoint="/users/{id}/profile",
            fetched_at=fetched_at,
        )
        if not profile.user_id:
            failed += 1
            logger.warning("Profile response missing user_id: target=%s", target.user_id)
            continue
        rows.append(profile)

    result = upsert_user_profiles_batch(rows, config.d1)
    click.echo(
        "enrich-profiles summary: "
        f"targets={len(targets)} fetched={len(rows)} "
        f"inserted={result.rows_inserted} skipped_401={skipped_401} "
        f"skipped_403={skipped_403} throttled_429={throttled_429} "
        f"not_found_marked={not_found_marked} "
        f"rows_skipped={result.rows_skipped} failed={failed}",
    )

    if result.errors or failed > 0:
        for error in result.errors:
            click.echo(f"[ERROR] {error}", err=True)
        if failed > 0:
            click.echo(f"[ERROR] non-auth failures: {failed}", err=True)
        sys.exit(1)


@main.command("backfill-profiles-safe")
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--json-log", is_flag=True)
@click.option("--max-steps", type=int, default=0, show_default=True)
@click.option("--wait-on-429", is_flag=True, default=False)
def backfill_profiles_safe(
    config_path: Path | None,
    json_log: bool,
    max_steps: int,
    wait_on_429: bool,
) -> None:
    setup_logging(json_format=json_log)
    config = load_config(config_path)

    if not config.profile_enrichment.enabled:
        click.echo("[FAIL] profile_enrichment.enabled must be true", err=True)
        sys.exit(1)

    guild_id = config.profile_enrichment.guild_id
    if not guild_id:
        click.echo("[FAIL] profile_enrichment.guild_id is required", err=True)
        sys.exit(1)

    client = DiscordClient(config.discord)
    template_path = _resolve_template_path(
        config_path,
        config.profile_enrichment.request_template_path,
    )
    request_headers = _load_profile_request_headers(template_path)

    per_user_delay = max(config.profile_enrichment.per_user_delay_sec, 0.0)
    cooldown_429 = max(config.profile_enrichment.cooldown_on_429_sec, 1)
    max_consecutive_429 = config.profile_enrichment.max_consecutive_429

    processed = 0
    inserted = 0
    marked_401 = 0
    marked_403 = 0
    marked_404 = 0
    throttled_429 = 0
    consecutive_429 = 0

    while True:
        missing_count = get_missing_profile_count(config.d1)
        if missing_count == 0:
            click.echo(
                "backfill-profiles-safe complete: "
                f"processed={processed} inserted={inserted} "
                f"marked_401={marked_401} marked_403={marked_403} marked_404={marked_404} "
                f"throttled_429={throttled_429} remaining=0"
            )
            return

        if max_steps > 0 and processed >= max_steps:
            click.echo(
                "backfill-profiles-safe paused: "
                f"processed={processed} inserted={inserted} remaining={missing_count}"
            )
            return

        targets = list_missing_profile_targets(1, config.d1)
        if not targets:
            click.echo("No target selected while missing profiles exist.", err=True)
            sys.exit(1)

        target = targets[0]
        fetched_at = datetime.now(tz=UTC).isoformat()

        try:
            payload = client.fetch_user_profile(
                target.user_id,
                guild_id,
                type=config.profile_enrichment.type,
                with_mutual_guilds=config.profile_enrichment.with_mutual_guilds,
                with_mutual_friends=config.profile_enrichment.with_mutual_friends,
                with_mutual_friends_count=config.profile_enrichment.with_mutual_friends_count,
                request_timeout_sec=config.profile_enrichment.request_timeout_sec,
                max_retries=config.profile_enrichment.max_retries,
                extra_headers=request_headers,
            )
        except DiscordApiError as e:
            if e.status_code == 429:
                throttled_429 += 1
                consecutive_429 += 1
                cooldown = min(cooldown_429 * (2 ** (consecutive_429 - 1)), 43_200)
                retry_after_match = re.search(r"retry_after=([0-9]+(?:\.[0-9]+)?)", str(e))
                retry_after = float(retry_after_match.group(1)) if retry_after_match else 0.0
                jitter = random.uniform(0.0, cooldown * 0.15)
                wait_sec = int(max(cooldown, retry_after) + jitter)
                logger.warning(
                    "Safe backfill throttled: user_id=%s consecutive_429=%d cooldown=%ss",
                    target.user_id,
                    consecutive_429,
                    wait_sec,
                )
                if consecutive_429 >= max_consecutive_429:
                    click.echo(
                        "[FAIL] too many consecutive 429 responses. "
                        f"count={consecutive_429} remaining={missing_count}",
                        err=True,
                    )
                    sys.exit(1)
                click.echo(
                    "backfill-profiles-safe paused: "
                    f"reason=429 wait_sec={wait_sec} remaining={missing_count}",
                )
                if wait_on_429:
                    time.sleep(wait_sec)
                    continue
                sys.exit(75)
                continue

            consecutive_429 = 0
            if e.status_code in (401, 403):
                click.echo(
                    f"[FAIL] auth/permission issue: user_id={target.user_id} status={e.status_code}",
                    err=True,
                )
                sys.exit(1)

            if e.status_code == 404:
                marker = _marker_profile(
                    target.user_id,
                    404,
                    fetched_at,
                    "profile unavailable: status=404",
                )
                result = upsert_user_profiles_batch([marker], config.d1)
                if result.errors:
                    for error in result.errors:
                        click.echo(f"[ERROR] {error}", err=True)
                    sys.exit(1)
                processed += 1
                inserted += result.rows_inserted
                marked_404 += 1
                logger.warning(
                    "Safe backfill terminal marker: user_id=%s status=404",
                    target.user_id,
                )
                if per_user_delay > 0:
                    time.sleep(per_user_delay)
                continue

            click.echo(
                f"[FAIL] non-terminal fetch error: user_id={target.user_id} status={e.status_code}",
                err=True,
            )
            sys.exit(1)

        consecutive_429 = 0
        profile = DiscordUserProfile.from_profile_response(
            payload,
            source_endpoint="/users/{id}/profile",
            fetched_at=fetched_at,
        )
        if not profile.user_id:
            click.echo(f"[FAIL] missing user_id in payload for target={target.user_id}", err=True)
            sys.exit(1)

        result = upsert_user_profiles_batch([profile], config.d1)
        if result.errors:
            for error in result.errors:
                click.echo(f"[ERROR] {error}", err=True)
            sys.exit(1)

        processed += 1
        inserted += result.rows_inserted

        if processed % 10 == 0:
            click.echo(
                "backfill-profiles-safe progress: "
                f"processed={processed} inserted={inserted} remaining={missing_count} "
                f"throttled_429={throttled_429}"
            )

        if per_user_delay > 0:
            time.sleep(per_user_delay)


def _log_summary(all_stats: list[CollectStats], dry_run: bool) -> None:
    """실행 요약을 로깅한다."""
    total_fetched = sum(s.messages_fetched for s in all_stats)
    total_new = sum(s.messages_new for s in all_stats)
    total_stored = sum(s.messages_stored for s in all_stats)
    errors = [s for s in all_stats if s.error]

    logger.info(
        "Fetch summary: channels=%d, fetched=%d, new=%d, stored=%d, errors=%d, dry_run=%s",
        len(all_stats),
        total_fetched,
        total_new,
        total_stored,
        len(errors),
        dry_run,
        extra={
            "event_code": "FETCH_SUMMARY",
            "count": total_stored,
        },
    )
