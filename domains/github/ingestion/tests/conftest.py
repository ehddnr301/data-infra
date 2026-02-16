"""공통 fixture."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture()
def sample_event_data() -> dict[str, Any]:
    """정상 GitHub Archive 이벤트 JSON 샘플."""
    return {
        "id": "12345678901",
        "type": "PushEvent",
        "actor": {
            "id": 1,
            "login": "testuser",
            "display_login": "testuser",
            "gravatar_id": "",
            "url": "https://api.github.com/users/testuser",
            "avatar_url": "https://avatars.githubusercontent.com/u/1?",
        },
        "repo": {
            "id": 100,
            "name": "pseudolab/test-repo",
            "url": "https://api.github.com/repos/pseudolab/test-repo",
        },
        "org": {
            "id": 200,
            "login": "pseudolab",
            "gravatar_id": "",
            "url": "https://api.github.com/orgs/pseudolab",
            "avatar_url": "https://avatars.githubusercontent.com/u/200?",
        },
        "payload": {"push_id": 999, "size": 1},
        "public": True,
        "created_at": "2024-01-15T10:30:00Z",
    }


@pytest.fixture()
def sample_config_data() -> dict[str, Any]:
    """테스트용 config dict."""
    return {
        "gharchive": {"base_url": "https://data.gharchive.org"},
        "target_orgs": ["pseudolab"],
        "event_types": [],
        "exclude_repos": [],
        "http": {
            "download_timeout_sec": 120,
            "max_retries": 3,
            "backoff_factor": 2.0,
            "max_concurrency": 4,
            "user_agent": "gharchive-etl/0.1.0 (pseudolab)",
        },
        "r2": {"bucket_name": "github-archive-raw", "prefix": "raw/github-archive"},
        "d1": {"database_id": "test-db-id"},
    }


@pytest.fixture()
def tmp_config_file(tmp_path: Path, sample_config_data: dict[str, Any]) -> Path:
    """임시 YAML 설정 파일."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(sample_config_data), encoding="utf-8")
    return config_path


@pytest.fixture()
def malformed_event_no_org(sample_event_data: dict[str, Any]) -> dict[str, Any]:
    """org 필드 누락 이벤트."""
    data = sample_event_data.copy()
    del data["org"]
    return data


@pytest.fixture()
def malformed_event_no_id(sample_event_data: dict[str, Any]) -> dict[str, Any]:
    """id 필드 누락 이벤트."""
    data = sample_event_data.copy()
    del data["id"]
    return data
