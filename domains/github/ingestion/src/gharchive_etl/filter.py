"""org/repo 필터링 로직."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from gharchive_etl.config import AppConfig
from gharchive_etl.models import GitHubEvent

logger = logging.getLogger(__name__)


def filter_events(
    events: Iterable[GitHubEvent],
    config: AppConfig,
) -> list[GitHubEvent]:
    """설정에 정의된 target_orgs에 해당하는 이벤트만 필터링한다.

    - id가 없는 이벤트는 스킵 + 경고 로그
    - org.login이 target_orgs에 포함된 이벤트만 통과
    - exclude_repos에 해당하는 repo는 제외
    - event_types가 지정되면 해당 타입만 통과
    """
    target_orgs = set(config.target_orgs)
    exclude_repos = set(config.exclude_repos)
    event_types = set(config.event_types) if config.event_types else None

    result: list[GitHubEvent] = []

    for event in events:
        # id 검증
        if not event.id:
            logger.warning(
                "Skipping event with empty id: type=%s, repo=%s", event.type, event.repo.name
            )
            continue

        # org 필터링: org가 없는 이벤트는 스킵
        if event.org is None:
            continue

        if event.org.login not in target_orgs:
            continue

        # repo 제외 필터
        if event.repo.name in exclude_repos:
            continue

        # 이벤트 타입 필터
        if event_types and event.type not in event_types:
            continue

        result.append(event)

    logger.info(
        "Filtered %d events from stream (target_orgs=%s)",
        len(result),
        list(target_orgs),
    )
    return result
