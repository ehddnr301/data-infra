"""데이터 모델 검증 테스트."""

from __future__ import annotations

from typing import Any

import pytest
from gharchive_etl.models import GitHubEvent
from pydantic import ValidationError


class TestGitHubEvent:
    """GitHubEvent 정상 파싱 테스트."""

    def test_parse_valid_event(self, sample_event_data: dict[str, Any]) -> None:
        event = GitHubEvent.model_validate(sample_event_data)
        assert event.id == "12345678901"
        assert event.type == "PushEvent"
        assert event.actor.login == "testuser"
        assert event.repo.name == "pseudolab/test-repo"
        assert event.org is not None
        assert event.org.login == "pseudolab"

    def test_parse_event_without_org(self, malformed_event_no_org: dict[str, Any]) -> None:
        event = GitHubEvent.model_validate(malformed_event_no_org)
        assert event.org is None

    def test_parse_event_created_at(self, sample_event_data: dict[str, Any]) -> None:
        event = GitHubEvent.model_validate(sample_event_data)
        assert event.created_at.year == 2024
        assert event.created_at.month == 1
        assert event.created_at.hour == 10

    def test_default_payload_empty(self, sample_event_data: dict[str, Any]) -> None:
        data = sample_event_data.copy()
        del data["payload"]
        event = GitHubEvent.model_validate(data)
        assert event.payload == {}

    def test_default_public_true(self, sample_event_data: dict[str, Any]) -> None:
        data = sample_event_data.copy()
        del data["public"]
        event = GitHubEvent.model_validate(data)
        assert event.public is True


class TestGitHubEventEdgeCases:
    """예외/엣지 케이스 테스트."""

    def test_missing_id_raises(self, malformed_event_no_id: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            GitHubEvent.model_validate(malformed_event_no_id)

    def test_missing_required_actor_raises(self, sample_event_data: dict[str, Any]) -> None:
        data = sample_event_data.copy()
        del data["actor"]
        with pytest.raises(ValidationError):
            GitHubEvent.model_validate(data)

    def test_missing_required_repo_raises(self, sample_event_data: dict[str, Any]) -> None:
        data = sample_event_data.copy()
        del data["repo"]
        with pytest.raises(ValidationError):
            GitHubEvent.model_validate(data)

    def test_large_payload(self, sample_event_data: dict[str, Any]) -> None:
        data = sample_event_data.copy()
        data["payload"] = {"large_data": "x" * 1_000_000}
        event = GitHubEvent.model_validate(data)
        assert len(event.payload["large_data"]) == 1_000_000

    def test_invalid_datetime_raises(self, sample_event_data: dict[str, Any]) -> None:
        data = sample_event_data.copy()
        data["created_at"] = "not-a-date"
        with pytest.raises(ValidationError):
            GitHubEvent.model_validate(data)
