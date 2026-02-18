"""Slack 알림 및 일일 요약 모듈 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from gharchive_etl.notify import (
    AlertMessage,
    build_daily_summary,
    send_slack_webhook,
)


def _make_alert(**overrides: Any) -> AlertMessage:
    """테스트용 AlertMessage 헬퍼."""
    defaults: dict[str, Any] = {
        "level": "INFO",
        "title": "Test Alert",
        "text": "Test message body",
        "context": {},
    }
    defaults.update(overrides)
    return AlertMessage(**defaults)


def _mock_response(status_code: int = 200) -> httpx.Response:
    """테스트용 httpx.Response 생성."""
    return httpx.Response(
        status_code=status_code,
        text="ok",
        request=httpx.Request("POST", "https://hooks.slack.com/test"),
    )


class TestSendSlackWebhook:
    """Slack webhook 전송 테스트."""

    def test_payload_contains_text(self) -> None:
        """Slack payload에 text 필드 포함 검증."""
        alert = _make_alert(level="WARN", title="My Title", text="My body")
        with patch("gharchive_etl.notify.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = _mock_response()
            mock_cls.return_value = mock_client

            send_slack_webhook(alert, "https://hooks.slack.com/test")

            call_kwargs = mock_client.post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert "text" in payload
            assert "My Title" in payload["text"]
            assert "WARN" in payload["text"]

    def test_success_returns_true(self) -> None:
        """webhook 전송 성공 시 True 반환."""
        alert = _make_alert()
        with patch("gharchive_etl.notify.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = _mock_response()
            mock_cls.return_value = mock_client

            result = send_slack_webhook(alert, "https://hooks.slack.com/test")
            assert result is True

    def test_failure_returns_false(self) -> None:
        """webhook 전송 실패(네트워크) 시 False 반환."""
        alert = _make_alert()
        with patch("gharchive_etl.notify.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_cls.return_value = mock_client

            result = send_slack_webhook(alert, "https://hooks.slack.com/test")
            assert result is False

    def test_retry_on_failure(self) -> None:
        """재시도 동작 검증 (최대 3회 시도)."""
        alert = _make_alert()
        with patch("gharchive_etl.notify.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_cls.return_value = mock_client

            with patch("gharchive_etl.notify.time.sleep") as mock_sleep:
                send_slack_webhook(alert, "https://hooks.slack.com/test")
                # 3 attempts total, 2 retries with sleep
                assert mock_client.post.call_count == 3
                assert mock_sleep.call_count == 2

    def test_retry_succeeds_on_second_attempt(self) -> None:
        """두 번째 시도에서 성공."""
        alert = _make_alert()
        with patch("gharchive_etl.notify.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = [
                httpx.ConnectError("Connection refused"),
                _mock_response(),
            ]
            mock_cls.return_value = mock_client

            with patch("gharchive_etl.notify.time.sleep"):
                result = send_slack_webhook(alert, "https://hooks.slack.com/test")
                assert result is True
                assert mock_client.post.call_count == 2


class TestSlackWebhookNotifier:
    """Airflow SlackWebhookNotifier 테스트."""

    def test_notifier_calls_send_slack_webhook(self) -> None:
        """SlackWebhookNotifier.notify() 호출 시 send_slack_webhook 호출 검증."""
        # BaseNotifier 미설치 환경에서는 건너뜀
        try:
            from gharchive_etl.notify import SlackWebhookNotifier
        except ImportError:
            pytest.skip("Airflow not installed, SlackWebhookNotifier not available")

        notifier = SlackWebhookNotifier(
            webhook_url="https://hooks.slack.com/test",
            message="Custom failure message",
        )

        mock_ti = MagicMock()
        mock_ti.dag_id = "test_dag"
        mock_ti.task_id = "test_task"
        mock_ti.log_url = "http://airflow/log/123"

        context: dict[str, Any] = {"task_instance": mock_ti}

        with patch("gharchive_etl.notify.send_slack_webhook") as mock_send:
            mock_send.return_value = True
            notifier.notify(context)
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            alert = call_args[0][0]
            assert alert.level == "ERROR"
            assert "test_dag" in alert.title
            assert "test_task" in alert.title


class TestBuildDailySummary:
    """일일 요약 생성 테스트."""

    def test_success_summary(self) -> None:
        """성공 케이스: INFO 레벨."""
        msg = build_daily_summary(
            batch_date="2024-01-15",
            events_count=100,
            upload_success=True,
            quality_passed=True,
        )
        assert msg.level == "INFO"
        assert "2024-01-15" in msg.title
        assert "100" in msg.text
        assert "SUCCESS" in msg.text

    def test_failure_summary(self) -> None:
        """업로드 실패 케이스: WARN 레벨."""
        msg = build_daily_summary(
            batch_date="2024-01-15",
            events_count=50,
            upload_success=False,
            quality_passed=None,
        )
        assert msg.level == "WARN"
        assert "FAILED" in msg.text

    def test_error_summary(self) -> None:
        """에러가 있는 케이스: ERROR 레벨."""
        msg = build_daily_summary(
            batch_date="2024-01-15",
            events_count=0,
            upload_success=False,
            quality_passed=False,
            errors=["Error 1", "Error 2"],
        )
        assert msg.level == "ERROR"
        assert "Error 1" in msg.text
        assert "Error 2" in msg.text

    def test_zero_events_success(self) -> None:
        """0건 성공 케이스."""
        msg = build_daily_summary(
            batch_date="2024-01-15",
            events_count=0,
            upload_success=True,
            quality_passed=None,
        )
        assert msg.level == "INFO"
        assert "0" in msg.text
        assert msg.context["events_count"] == 0

    def test_quality_none(self) -> None:
        """quality_passed=None → N/A 표시."""
        msg = build_daily_summary(
            batch_date="2024-01-15",
            events_count=10,
            upload_success=True,
            quality_passed=None,
        )
        assert "N/A" in msg.text

    def test_many_errors_truncated(self) -> None:
        """에러가 5개 초과 시 truncation."""
        errors = [f"Error {i}" for i in range(10)]
        msg = build_daily_summary(
            batch_date="2024-01-15",
            events_count=0,
            upload_success=False,
            quality_passed=False,
            errors=errors,
        )
        assert "5 more" in msg.text
