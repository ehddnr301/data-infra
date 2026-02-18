"""Slack 알림 및 일일 요약 모듈.

Slack Incoming Webhook을 통해 파이프라인 상태를 알린다.
- 재시도: 최대 2회, 1초 백오프
- Airflow 3.0+ BaseNotifier 서브클래스 지원
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

logger = logging.getLogger(__name__)


@dataclass
class AlertMessage:
    """알림 메시지."""

    level: Literal["INFO", "WARN", "ERROR"]
    title: str
    text: str
    context: dict[str, Any] = field(default_factory=dict)


_LEVEL_EMOJI = {"INFO": ":information_source:", "WARN": ":warning:", "ERROR": ":rotating_light:"}


def send_slack_webhook(message: AlertMessage, webhook_url: str) -> bool:
    """Slack Incoming Webhook으로 메시지 전송.

    - 재시도: 최대 2회, 1초 백오프
    - 네트워크 실패 시 False 반환 + 로그 기록
    - 성공 시 True 반환
    """
    emoji = _LEVEL_EMOJI.get(message.level, "")
    payload: dict[str, Any] = {
        "text": f"{emoji} *[{message.level}] {message.title}*\n{message.text}",
    }

    max_attempts = 3  # 1 initial + 2 retries
    for attempt in range(max_attempts):
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(webhook_url, json=payload)
                resp.raise_for_status()
            return True
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.warning("Slack webhook attempt %d/%d failed: %s", attempt + 1, max_attempts, e)
            if attempt < max_attempts - 1:
                time.sleep(1.0)

    logger.error("Slack webhook failed after %d attempts: %s", max_attempts, message.title)
    return False


# Airflow 3.0+ BaseNotifier 지원
try:
    from airflow.sdk.bases.notifier import BaseNotifier
except (ImportError, Exception):
    try:
        from airflow.notifications.basenotifier import BaseNotifier
    except (ImportError, Exception):
        BaseNotifier = None  # type: ignore[assignment, misc]

if BaseNotifier is not None:

    class SlackWebhookNotifier(BaseNotifier):  # type: ignore[misc]
        """Airflow 3.0+ on_failure_callback용 Slack 알림 노티파이어."""

        template_fields = ("message",)

        def __init__(self, webhook_url: str, message: str = "") -> None:
            super().__init__()
            self.webhook_url = webhook_url
            self.message = message

        def notify(self, context: dict[str, Any]) -> None:
            """context에서 task_id, dag_id, run_id, log_url 추출 후 Slack 전송."""
            task_instance = context.get("task_instance")
            dag_id = "unknown"
            task_id = "unknown"
            log_url = ""

            if task_instance is not None:
                dag_id = getattr(task_instance, "dag_id", "unknown")
                task_id = getattr(task_instance, "task_id", "unknown")
                log_url = getattr(task_instance, "log_url", "")

            text = self.message or f"Task failed: {dag_id}.{task_id}"
            if log_url:
                text += f"\n<{log_url}|View Log>"

            alert = AlertMessage(
                level="ERROR",
                title=f"Airflow Task Failed: {dag_id}.{task_id}",
                text=text,
                context={"dag_id": dag_id, "task_id": task_id},
            )
            send_slack_webhook(alert, self.webhook_url)


def build_daily_summary(
    batch_date: str,
    events_count: int,
    upload_success: bool,
    quality_passed: bool | None,
    errors: list[str] | None = None,
) -> AlertMessage:
    """일일 실행 요약 AlertMessage 생성."""
    if errors:
        level: Literal["INFO", "WARN", "ERROR"] = "ERROR"
    elif not upload_success:
        level = "WARN"
    else:
        level = "INFO"

    status = "SUCCESS" if upload_success else "FAILED"
    quality_str = "N/A" if quality_passed is None else ("PASS" if quality_passed else "FAIL")

    lines = [
        f"Date: {batch_date}",
        f"Events: {events_count}",
        f"Upload: {status}",
        f"Quality: {quality_str}",
    ]

    if errors:
        lines.append(f"Errors ({len(errors)}):")
        for err in errors[:5]:  # 최대 5개만 표시
            lines.append(f"  - {err}")
        if len(errors) > 5:
            lines.append(f"  ... and {len(errors) - 5} more")

    return AlertMessage(
        level=level,
        title=f"Daily Summary: {batch_date}",
        text="\n".join(lines),
        context={
            "batch_date": batch_date,
            "events_count": events_count,
            "upload_success": upload_success,
            "quality_passed": quality_passed,
        },
    )
