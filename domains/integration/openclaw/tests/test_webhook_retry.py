from __future__ import annotations

import hashlib
import hmac
import time

from applier import backoff_seconds, is_retryable_status
from webhook import _plan_error_message, verify_slack_signature


def test_retryable_status_policy() -> None:
    assert is_retryable_status(429)
    assert is_retryable_status(500)
    assert is_retryable_status(503)
    assert not is_retryable_status(400)
    assert not is_retryable_status(401)


def test_backoff_grows_with_attempt() -> None:
    first = backoff_seconds(0, 1000)
    second = backoff_seconds(1, 1000)
    assert first >= 1.0
    assert second >= 2.0
    assert second > first


def test_verify_slack_signature() -> None:
    body = b"token=abc&text=plan+seed"
    timestamp = str(int(time.time()))
    secret = "signing-secret"
    base = f"v0:{timestamp}:{body.decode('utf-8')}"
    signature = (
        "v0=" + hmac.new(secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()
    )
    assert verify_slack_signature(
        body=body,
        timestamp=timestamp,
        signature=signature,
        signing_secret=secret,
    )


def test_plan_error_message_timeout() -> None:
    message, failure_code = _plan_error_message(TimeoutError("Request timed out or interrupted"))
    assert "응답 시간" in message
    assert failure_code == "anthropic_timeout"


def test_plan_error_message_generic() -> None:
    message, failure_code = _plan_error_message(ValueError("invalid payload"))
    assert message == "invalid payload"
    assert failure_code == "plan_generation_error"
