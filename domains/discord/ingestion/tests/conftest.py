"""공통 fixture."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture()
def sample_discord_message() -> dict[str, Any]:
    """Discord API 메시지 응답 샘플."""
    return {
        "id": "1234567890123456789",
        "channel_id": "944039671707607060",
        "author": {
            "id": "111222333444555666",
            "username": "testuser",
            "discriminator": "0",
            "avatar": None,
        },
        "content": "안녕하세요!",
        "timestamp": "2024-06-15T10:30:00.000000+00:00",
        "edited_timestamp": None,
        "type": 0,
        "referenced_message": None,
        "attachments": [],
        "embeds": [],
        "reactions": [],
        "mentions": [],
        "pinned": False,
    }


@pytest.fixture()
def sample_config_data() -> dict[str, Any]:
    """테스트용 config dict."""
    return {
        "discord": {
            "api_base": "https://discord.com/api/v9",
            "limit": 50,
            "delay_sec": 0.0,  # 테스트에서는 딜레이 없음
            "max_retries": 1,
            "backoff_factor": 0.01,
            "chunk_pages": 2,
        },
        "channels": [
            {"name": "test-channel", "id": "944039671707607060"},
        ],
        "d1": {"database_id": "test-db-id"},
    }


@pytest.fixture()
def tmp_config_file(tmp_path: Path, sample_config_data: dict[str, Any]) -> Path:
    """임시 config.yaml 파일."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(sample_config_data), encoding="utf-8")
    return config_path


@pytest.fixture()
def sample_reply_message(sample_discord_message: dict[str, Any]) -> dict[str, Any]:
    """답글 메시지 샘플."""
    data = sample_discord_message.copy()
    data["id"] = "1234567890123456790"
    data["type"] = 19  # reply
    data["referenced_message"] = {"id": "1234567890123456789"}
    data["content"] = "답글입니다!"
    return data
