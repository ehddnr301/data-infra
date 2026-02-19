"""Discord 메시지 Pagination 수집기.

청크 단위로 수집 -> 필터 -> 저장하며,
scan_cursor로 중단/재개를 지원한다.
output_dir 모드: raw API 응답을 JSONL 파일로 저장.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import orjson

from discord_etl.client import DiscordApiError, DiscordClient
from discord_etl.config import AppConfig, ChannelConfig
from discord_etl.d1 import (
    clear_scan_cursor,
    get_scan_cursor,
    get_watermark,
    insert_messages_batch,
    save_scan_cursor,
    save_watermark,
)
from discord_etl.models import DiscordMessage

logger = logging.getLogger(__name__)


@dataclass
class CollectStats:
    """채널별 수집 통계."""

    channel_name: str
    channel_id: str
    pages_fetched: int = 0
    messages_fetched: int = 0
    messages_new: int = 0         # watermark 필터 후 신규
    messages_stored: int = 0      # D1 저장 성공
    chunks_stored: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    resumed_from_cursor: bool = False


def collect_channel(
    channel: ChannelConfig,
    client: DiscordClient,
    config: AppConfig,
    *,
    dry_run: bool = False,
    output_dir: Path | None = None,
    batch_date: str | None = None,
) -> CollectStats:
    """단일 채널의 메시지를 수집한다.

    흐름:
    1. watermark(last_message_id)와 scan_cursor 조회
    2. scan_cursor가 있으면 해당 위치부터 이어서 수집
    3. 페이지별 응답을 청크 버퍼에 누적
    4. 청크 크기 도달 시: 필터 -> 배치 저장 -> cursor 저장 -> 버퍼 초기화
    5. watermark 이하 ID 도달 또는 빈 응답 -> 루프 종료
    6. 잔여 버퍼 필터 후 저장
    7. watermark 갱신 + scan_cursor 제거

    output_dir 모드:
    - raw API 응답을 JSONL 파일로 저장 ({output_dir}/{channel.name}/{batch_date}.jsonl)
    - watermark는 갱신하지 않음 (upload 커맨드에서 처리)
    - scan_cursor는 중단 복구용으로 저장
    """
    stats = CollectStats(channel_name=channel.name, channel_id=channel.id)
    start_time = time.monotonic()

    if batch_date is None:
        batch_date = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    try:
        # 1. watermark & scan_cursor 조회
        #    dry_run 또는 output_dir 모드이면 D1 조회 생략 (fetch 단계에서 D1 불필요)
        if dry_run or output_dir is not None:
            watermark_id = "0"
            scan_cursor = None
            # output_dir 모드: 로컬 .cursor 파일로 중단 복구 지원
            if output_dir is not None:
                scan_cursor = _read_local_cursor(output_dir, channel.name)
        else:
            watermark_id = get_watermark(channel.id, config.d1)
            scan_cursor = get_scan_cursor(channel.id, config.d1)

        if scan_cursor:
            stats.resumed_from_cursor = True
            logger.info(
                "Resuming from scan_cursor=%s (channel=%s)",
                scan_cursor, channel.name,
                extra={"event_code": "SCAN_RESUME",
                       "channel_id": channel.id},
            )

        # 2. pagination 시작점
        before: str | None = scan_cursor  # cursor가 없으면 None (최신부터)

        chunk_buffer: list[DiscordMessage] = []
        raw_buffer: list[dict] = []  # output_dir 모드용 raw 응답 버퍼
        chunk_page_count = 0
        max_collected_id = "0"  # 수집 중 발견된 최대 ID
        reached_watermark = False

        # 3-6. 페이지 순회 루프
        while True:
            raw_messages = client.fetch_messages(
                channel.id, before=before,
            )

            if not raw_messages:
                logger.info(
                    "Empty response, end of history (channel=%s)",
                    channel.name,
                    extra={"event_code": "HISTORY_END",
                           "channel_id": channel.id},
                )
                break

            stats.pages_fetched += 1

            # 페이지 내 메시지 파싱 + 버퍼 누적
            for raw in raw_messages:
                try:
                    msg = DiscordMessage.from_api_response(raw)
                except Exception as e:
                    logger.warning("Parse error: %s (raw_id=%s)", e,
                                   raw.get("id", "?"))
                    continue

                stats.messages_fetched += 1
                chunk_buffer.append(msg)
                if output_dir is not None:
                    raw_buffer.append(raw)

                # 최대 ID 추적
                if int(msg.id) > int(max_collected_id):
                    max_collected_id = msg.id

            # pagination cursor: 현재 페이지의 마지막(가장 오래된) 메시지 ID
            oldest_in_page = raw_messages[-1]["id"]
            before = oldest_in_page

            # watermark 도달 검사: 페이지 내 모든 메시지가 watermark 이하
            if all(
                int(raw["id"]) <= int(watermark_id)
                for raw in raw_messages
            ):
                reached_watermark = True
                logger.info(
                    "Reached watermark (channel=%s, watermark=%s)",
                    channel.name, watermark_id,
                    extra={"event_code": "WATERMARK_REACHED",
                           "channel_id": channel.id},
                )

            chunk_page_count += 1

            # 4. 청크 크기 도달 또는 watermark 도달 -> 플러시
            if chunk_page_count >= config.discord.chunk_pages or reached_watermark:
                _flush_chunk(
                    chunk_buffer, watermark_id, channel, config, stats,
                    dry_run=dry_run,
                    output_dir=output_dir,
                    raw_messages=raw_buffer,
                    batch_date=batch_date,
                )
                # scan_cursor 저장 (중단 대비)
                if not dry_run and not reached_watermark:
                    if output_dir is not None:
                        _save_local_cursor(output_dir, channel.name, before)
                    else:
                        save_scan_cursor(channel.id, before, config.d1)
                chunk_buffer = []
                raw_buffer = []
                chunk_page_count = 0

            if reached_watermark:
                break

            # 보수적 딜레이
            time.sleep(config.discord.delay_sec)

        # 7. 잔여 버퍼 플러시
        if chunk_buffer:
            _flush_chunk(
                chunk_buffer, watermark_id, channel, config, stats,
                dry_run=dry_run,
                output_dir=output_dir,
                raw_messages=raw_buffer,
                batch_date=batch_date,
            )

        # 8. watermark 갱신 — output_dir 모드에서는 생략 (upload에서 처리)
        if not dry_run and output_dir is None and int(max_collected_id) > int(watermark_id):
            save_watermark(channel.id, max_collected_id, config.d1)
            logger.info(
                "Watermark updated: %s -> %s (channel=%s)",
                watermark_id, max_collected_id, channel.name,
                extra={"event_code": "WATERMARK_UPDATED",
                       "channel_id": channel.id},
            )

        # 9. scan_cursor 제거
        if not dry_run:
            if output_dir is not None:
                _clear_local_cursor(output_dir, channel.name)
            else:
                clear_scan_cursor(channel.id, config.d1)

    except DiscordApiError as e:
        stats.error = str(e)
        logger.error(
            "Collection failed (channel=%s): %s",
            channel.name, e,
            extra={"event_code": "COLLECT_ERROR",
                   "channel_id": channel.id},
        )
    except Exception as e:
        stats.error = str(e)
        logger.error(
            "Unexpected error (channel=%s): %s",
            channel.name, e,
            extra={"event_code": "COLLECT_ERROR",
                   "channel_id": channel.id},
        )

    stats.duration_ms = (time.monotonic() - start_time) * 1000
    return stats


# ── 로컬 커서 (output_dir 모드 중단 복구) ─────────────


def _local_cursor_path(output_dir: Path, channel_name: str) -> Path:
    return output_dir / channel_name / ".cursor"


def _read_local_cursor(output_dir: Path, channel_name: str) -> str | None:
    """로컬 .cursor 파일에서 scan_cursor를 읽는다."""
    path = _local_cursor_path(output_dir, channel_name)
    if path.exists():
        value = path.read_text().strip()
        return value if value else None
    return None


def _save_local_cursor(output_dir: Path, channel_name: str, cursor: str) -> None:
    """로컬 .cursor 파일에 scan_cursor를 저장한다."""
    path = _local_cursor_path(output_dir, channel_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cursor)


def _clear_local_cursor(output_dir: Path, channel_name: str) -> None:
    """로컬 .cursor 파일을 삭제한다."""
    path = _local_cursor_path(output_dir, channel_name)
    if path.exists():
        path.unlink()


def _flush_chunk(
    buffer: list[DiscordMessage],
    watermark_id: str,
    channel: ChannelConfig,
    config: AppConfig,
    stats: CollectStats,
    *,
    dry_run: bool = False,
    output_dir: Path | None = None,
    raw_messages: list[dict] | None = None,
    batch_date: str = "",
) -> None:
    """청크 버퍼를 필터 후 저장한다.

    output_dir가 설정되면 raw API 응답을 JSONL로 저장.
    아니면 기존 D1 배치 INSERT.
    """
    # watermark 필터: int(id) > int(watermark_id)인 메시지만
    new_messages = [
        msg for msg in buffer
        if int(msg.id) > int(watermark_id)
    ]
    stats.messages_new += len(new_messages)

    if not new_messages:
        return

    if dry_run:
        logger.info(
            "Dry run: would store %d messages (channel=%s)",
            len(new_messages), channel.name,
        )
        stats.messages_stored += len(new_messages)
        stats.chunks_stored += 1
        return

    # output_dir 모드: JSONL 파일로 저장
    if output_dir is not None:
        new_ids = {msg.id for msg in new_messages}
        raw_to_write = [
            r for r in (raw_messages or [])
            if r.get("id") in new_ids
        ]
        channel_dir = output_dir / channel.name
        channel_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = channel_dir / f"{batch_date}.jsonl"

        with open(jsonl_path, "ab") as f:
            for raw in raw_to_write:
                f.write(orjson.dumps(raw))
                f.write(b"\n")

        stats.messages_stored += len(raw_to_write)
        stats.chunks_stored += 1

        logger.info(
            "JSONL written: %d messages -> %s (channel=%s)",
            len(raw_to_write), jsonl_path, channel.name,
            extra={"event_code": "JSONL_WRITTEN",
                   "channel_id": channel.id,
                   "count": len(raw_to_write)},
        )
        return

    result = insert_messages_batch(new_messages, config.d1)
    stats.messages_stored += result.rows_inserted
    stats.chunks_stored += 1

    logger.info(
        "Chunk stored: %d/%d messages (channel=%s, batches=%d)",
        result.rows_inserted, len(new_messages),
        channel.name, result.batches_executed,
        extra={"event_code": "CHUNK_STORED",
               "channel_id": channel.id,
               "count": result.rows_inserted},
    )
