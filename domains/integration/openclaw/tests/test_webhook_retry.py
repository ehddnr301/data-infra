from __future__ import annotations

import hashlib
import hmac
import time

from applier import backoff_seconds, is_retryable_status
from webhook import (
    _column_description_thread_chunks,
    _plan_blocks,
    _plan_error_message,
    verify_slack_signature,
)


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


def test_plan_blocks_include_column_preview() -> None:
    payload = {
        "dataset": {
            "description": "dataset desc",
            "usage_examples": ["weekly report"],
            "purpose": "quality",
            "limitations": ["stale by one day"],
        },
        "columns": [
            {"column_name": "repo_name", "description": "repository name"},
            {"column_name": "event_type", "description": "event category"},
        ],
    }
    blocks = _plan_blocks("p1", "github.watch-events.v1", payload, time.time() + 300)
    section_texts = [
        block["text"]["text"]
        for block in blocks
        if block.get("type") == "section" and isinstance(block.get("text"), dict)
    ]
    joined = "\n".join(section_texts)
    assert "Column Description Preview" in joined
    assert "purpose: quality" in joined
    assert "limitation: stale by one day" in joined
    assert "`repo_name`: repository name" in joined
    assert "`event_type`: event category" in joined


def test_plan_blocks_preview_truncates_over_limit() -> None:
    payload = {
        "dataset": {
            "description": "dataset desc",
            "usage_examples": ["weekly report"],
            "purpose": "quality",
            "limitations": ["stale by one day"],
        },
        "columns": [
            {"column_name": f"col_{idx}", "description": f"desc_{idx}"} for idx in range(9)
        ],
    }
    blocks = _plan_blocks("p2", "github.watch-events.v1", payload, time.time() + 300)
    section_texts = [
        block["text"]["text"]
        for block in blocks
        if block.get("type") == "section" and isinstance(block.get("text"), dict)
    ]
    joined = "\n".join(section_texts)
    assert "... and 3 more columns" in joined


def test_column_description_thread_chunks_split_messages() -> None:
    payload = {
        "columns": [
            {"column_name": f"col_{idx}", "description": f"description_{idx}"} for idx in range(10)
        ]
    }
    chunks = _column_description_thread_chunks(payload, lines_per_message=4)
    assert len(chunks) == 3
    assert "(1-4/10)" in chunks[0]
    assert "(5-8/10)" in chunks[1]
    assert "(9-10/10)" in chunks[2]
    assert "`col_0`: description_0" in chunks[0]
    assert "`col_9`: description_9" in chunks[2]


def test_column_description_thread_chunks_skip_empty_descriptions() -> None:
    payload = {
        "columns": [
            {"column_name": "repo_name", "description": "repo"},
            {"column_name": "event_type", "description": ""},
        ]
    }
    chunks = _column_description_thread_chunks(payload)
    assert len(chunks) == 1
    assert "repo_name" in chunks[0]
    assert "event_type" not in chunks[0]
