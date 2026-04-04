"""Slack 알림 — daily summary + 에러 보고."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class DailySummary:
    """일일 ETL 요약."""

    batch_date: str = ""
    tables_total: int = 0
    tables_success: int = 0
    tables_failed: list[str] = field(default_factory=list)
    rows_total: int = 0
    archived_tables: int = 0
    errors: list[str] = field(default_factory=list)


def build_slack_message(summary: DailySummary) -> dict[str, Any]:
    """Slack webhook 메시지를 생성한다."""
    status = ":white_check_mark:" if not summary.tables_failed else ":x:"
    text_lines = [
        f"{status} *Supabase ETL Daily Summary* — `{summary.batch_date}`",
        f"- Tables: {summary.tables_success}/{summary.tables_total} succeeded",
        f"- Rows loaded: {summary.rows_total:,}",
    ]

    if summary.archived_tables:
        text_lines.append(f"- Archived to R2: {summary.archived_tables} tables")

    if summary.tables_failed:
        failed = ", ".join(summary.tables_failed[:10])
        text_lines.append(f"- :warning: Failed: {failed}")

    if summary.errors:
        for err in summary.errors[:3]:
            text_lines.append(f"  - `{err[:200]}`")

    return {"text": "\n".join(text_lines)}


def send_slack_webhook(message: dict[str, Any], webhook_url: str) -> bool:
    """Slack webhook으로 메시지를 전송한다."""
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not configured, skipping notification")
        return False

    for attempt in range(3):
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(webhook_url, json=message)
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.warning("Slack webhook attempt %d failed: %s", attempt + 1, e)
            if attempt == 2:
                logger.error("Slack webhook failed after 3 attempts")
                return False

    return False
