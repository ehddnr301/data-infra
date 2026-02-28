"""REST API Events 수집 모듈.

GitHub REST API의 org/repo events 엔드포인트에서 이벤트를 수집한다.
- org 우선 수집 + repo 보충 전략
- ETag 기반 조건부 요청 (304 Not Modified)
- event_id 기준 중복 제거
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gharchive_etl.config import AppConfig
from gharchive_etl.github_api import GitHubApiClient
from gharchive_etl.models import GitHubEvent

logger = logging.getLogger(__name__)

_DEFAULT_ETAG_CACHE_DIR = Path.home() / ".cache" / "gharchive-etl"


@dataclass
class CollectionResult:
    """단일 org 수집 결과."""
    org: str
    events: list[dict[str, Any]] = field(default_factory=list)
    new_events: int = 0
    skipped_304: bool = False
    repo_supplement: bool = False
    repos_fetched: int = 0
    api_calls: int = 0


@dataclass
class RestApiCollectionSummary:
    """전체 수집 요약."""
    results: list[CollectionResult] = field(default_factory=list)
    total_events: int = 0
    total_new: int = 0
    total_api_calls: int = 0
    duration_ms: float = 0.0


class RestApiCollector:
    """REST API Events 수집기.

    수집 전략:
    1. target_orgs 순회
    2. org별: fetch_org_events(org, etag=cached_etag) 호출
    3. 304 응답 시 스킵 (backfill 모드에서는 etag=None으로 강제)
    4. repo_supplement_threshold(300)건 이상이면 repo 보충 수집
    5. org+repo 결과를 event_id 기준 중복 제거
    6. GitHubEvent.model_validate(raw_dict)로 정규화
    """

    def __init__(
        self,
        api_client: GitHubApiClient,
        config: AppConfig,
        *,
        etag_cache_path: Path | None = None,
    ) -> None:
        self._api = api_client
        self._config = config
        self._rest_config = config.rest_api
        self._etag_cache_path = etag_cache_path or (
            _DEFAULT_ETAG_CACHE_DIR / "rest-api-etags.json"
        )
        self._etag_cache: dict[str, dict[str, str]] = self._load_etag_cache()
        self._api_calls = 0

    def collect_all(
        self, *, backfill: bool = False,
    ) -> tuple[list[GitHubEvent], RestApiCollectionSummary]:
        """모든 target_orgs에서 이벤트를 수집한다.

        Args:
            backfill: True이면 ETag 무시, 모든 org에서 repo 보충 강제

        Returns:
            (normalized_events, summary)
        """
        start = time.monotonic()
        summary = RestApiCollectionSummary()
        all_raw_events: list[dict[str, Any]] = []

        for org in self._config.target_orgs:
            result = self._collect_org(org, backfill=backfill)
            summary.results.append(result)
            all_raw_events.extend(result.events)

        # 중복 제거
        deduped = self._deduplicate(all_raw_events)
        summary.total_events = len(deduped)
        summary.total_new = len(deduped)
        summary.total_api_calls = self._api_calls

        # 정규화
        normalized: list[GitHubEvent] = []
        for raw in deduped:
            event = self._normalize_event(raw)
            if event is not None:
                normalized.append(event)

        # ETag 캐시 저장
        if not backfill:
            self._save_etag_cache()

        summary.duration_ms = (time.monotonic() - start) * 1000
        return normalized, summary

    def _collect_org(
        self, org: str, *, backfill: bool = False,
    ) -> CollectionResult:
        """단일 org의 이벤트를 수집한다."""
        result = CollectionResult(org=org)

        # ETag 조회 (backfill 시 무시)
        etag = None if backfill else self._etag_cache.get(org, {}).get("etag")

        # org 이벤트 수집
        api_result = self._api.fetch_org_events(org, etag=etag)
        self._api_calls += 1
        result.api_calls += 1

        # 304 Not Modified
        if api_result.status_code == 304:
            result.skipped_304 = True
            logger.info("Org %s: 304 Not Modified, skipping", org)
            return result

        if api_result.error:
            logger.warning("Org %s: API error: %s", org, api_result.error)
            return result

        org_events = api_result.data if isinstance(api_result.data, list) else []
        result.events.extend(org_events)
        result.new_events = len(org_events)

        # ETag 캐시 갱신
        new_etag = api_result.headers.get("etag") or api_result.headers.get("ETag")
        if new_etag:
            self._etag_cache[org] = {
                "etag": new_etag,
                "last_poll": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

        # repo 보충 수집 판단
        threshold = self._rest_config.repo_supplement_threshold
        if backfill or self._should_supplement_repos(org_events, threshold):
            result.repo_supplement = True
            repo_events = self._collect_repo_supplement(org)
            result.events.extend(repo_events)
            result.new_events += len(repo_events)

        logger.info(
            "Org %s: collected %d events (org=%d, repo_supplement=%s, api_calls=%d)",
            org, len(result.events), len(org_events),
            result.repo_supplement, result.api_calls,
        )
        return result

    @staticmethod
    def _should_supplement_repos(
        org_events: list[dict[str, Any]], threshold: int,
    ) -> bool:
        """org events 수가 threshold 이상이면 repo 보충 필요."""
        return len(org_events) >= threshold

    def _collect_repo_supplement(self, org: str) -> list[dict[str, Any]]:
        """org의 모든 repo에서 이벤트를 보충 수집한다."""
        # repo 목록 조회
        repos_result = self._api.fetch_org_repos(org)
        self._api_calls += 1

        if repos_result.error or not isinstance(repos_result.data, list):
            logger.warning("Failed to fetch repos for %s: %s", org, repos_result.error)
            return []

        repo_events: list[dict[str, Any]] = []
        for repo_data in repos_result.data:
            repo_name = repo_data.get("name", "")
            if not repo_name:
                continue

            events_result = self._api.fetch_repo_events(org, repo_name)
            self._api_calls += 1

            if events_result.error or not isinstance(events_result.data, list):
                continue

            repo_events.extend(events_result.data)

        return repo_events

    @staticmethod
    def _normalize_event(raw: dict[str, Any]) -> GitHubEvent | None:
        """REST API 이벤트를 GitHubEvent 모델로 정규화한다."""
        try:
            return GitHubEvent.model_validate(raw)
        except Exception as exc:
            logger.warning(
                "Failed to normalize event %s: %s",
                raw.get("id", "unknown"), exc,
            )
            return None

    @staticmethod
    def _deduplicate(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """event_id 기준 중복 제거 (먼저 등장한 것 우선)."""
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for event in events:
            event_id = str(event.get("id", ""))
            if event_id and event_id not in seen:
                seen.add(event_id)
                unique.append(event)
        return unique

    def _load_etag_cache(self) -> dict[str, dict[str, str]]:
        """ETag 캐시를 파일에서 로드한다."""
        if not self._etag_cache_path.exists():
            return {}
        try:
            return json.loads(self._etag_cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load ETag cache: %s", exc)
            return {}

    def _save_etag_cache(self) -> None:
        """ETag 캐시를 파일에 원자적으로 저장한다 (Architect I3)."""
        self._etag_cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._etag_cache_path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(self._etag_cache, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(tmp_path, self._etag_cache_path)
        except OSError as exc:
            logger.warning("Failed to save ETag cache: %s", exc)
            # 임시 파일 정리
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
