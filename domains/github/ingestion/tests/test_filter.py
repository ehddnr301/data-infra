"""org 필터링 로직 테스트."""

from __future__ import annotations

from typing import Any

from gharchive_etl.config import AppConfig
from gharchive_etl.filter import filter_events
from gharchive_etl.models import GitHubEvent


def _make_event(
    event_id: str = "1",
    org_login: str | None = "pseudolab",
    repo_name: str = "pseudolab/test-repo",
    event_type: str = "PushEvent",
) -> GitHubEvent:
    """테스트용 이벤트 헬퍼."""
    data: dict[str, Any] = {
        "id": event_id,
        "type": event_type,
        "actor": {"id": 1, "login": "user"},
        "repo": {"id": 100, "name": repo_name},
        "payload": {},
        "created_at": "2024-01-15T10:00:00Z",
    }
    if org_login is not None:
        data["org"] = {"id": 200, "login": org_login}
    return GitHubEvent.model_validate(data)


def _make_config(**overrides: Any) -> AppConfig:
    """테스트용 AppConfig 헬퍼."""
    defaults: dict[str, Any] = {"target_orgs": ["pseudolab"]}
    defaults.update(overrides)
    return AppConfig.model_validate(defaults)


class TestFilterEvents:
    """정상 경로 테스트."""

    def test_matching_org_passes(self) -> None:
        events = [_make_event(org_login="pseudolab")]
        config = _make_config()
        result = filter_events(events, config)
        assert len(result) == 1

    def test_non_matching_org_filtered(self) -> None:
        events = [_make_event(org_login="other-org")]
        config = _make_config()
        result = filter_events(events, config)
        assert len(result) == 0

    def test_no_org_filtered(self) -> None:
        events = [_make_event(org_login=None)]
        config = _make_config()
        result = filter_events(events, config)
        assert len(result) == 0

    def test_exclude_repos(self) -> None:
        events = [_make_event(repo_name="pseudolab/excluded")]
        config = _make_config(exclude_repos=["pseudolab/excluded"])
        result = filter_events(events, config)
        assert len(result) == 0

    def test_event_type_filter(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent"),
            _make_event(event_id="2", event_type="IssuesEvent"),
        ]
        config = _make_config(event_types=["PushEvent"])
        result = filter_events(events, config)
        assert len(result) == 1
        assert result[0].type == "PushEvent"

    def test_empty_event_types_passes_all(self) -> None:
        events = [
            _make_event(event_id="1", event_type="PushEvent"),
            _make_event(event_id="2", event_type="IssuesEvent"),
        ]
        config = _make_config(event_types=[])
        result = filter_events(events, config)
        assert len(result) == 2

    def test_multiple_target_orgs(self) -> None:
        events = [
            _make_event(event_id="1", org_login="pseudolab"),
            _make_event(event_id="2", org_login="another-org"),
            _make_event(event_id="3", org_login="third-org"),
        ]
        config = _make_config(target_orgs=["pseudolab", "another-org"])
        result = filter_events(events, config)
        assert len(result) == 2


class TestFilterEdgeCases:
    """예외/엣지 케이스 테스트."""

    def test_empty_id_skipped(self) -> None:
        event = _make_event(event_id="")
        config = _make_config()
        result = filter_events([event], config)
        assert len(result) == 0

    def test_case_sensitive_org(self) -> None:
        """org login은 대소문자를 구분한다."""
        events = [_make_event(org_login="PseudoLab")]
        config = _make_config(target_orgs=["pseudolab"])
        result = filter_events(events, config)
        assert len(result) == 0

    def test_empty_events_list(self) -> None:
        config = _make_config()
        result = filter_events([], config)
        assert len(result) == 0

    def test_mixed_events(self) -> None:
        events = [
            _make_event(event_id="1", org_login="pseudolab"),
            _make_event(event_id="2", org_login="other"),
            _make_event(event_id="3", org_login=None),
            _make_event(event_id="", org_login="pseudolab"),
        ]
        config = _make_config()
        result = filter_events(events, config)
        assert len(result) == 1
        assert result[0].id == "1"
