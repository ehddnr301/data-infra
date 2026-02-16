"""R2 업로드 모듈 — wrangler CLI 기반 gzip JSON Lines 업로드."""

from __future__ import annotations

import gzip
import logging
import random
import subprocess
import tempfile
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import orjson

from gharchive_etl.config import R2Config
from gharchive_etl.models import GitHubEvent

logger = logging.getLogger(__name__)


# ── 결과 데이터클래스 ─────────────────────────────────────


@dataclass
class R2UploadResult:
    """R2 업로드 결과."""

    total_events: int = 0
    files_uploaded: int = 0
    files_skipped: int = 0
    skipped_invalid_repo: int = 0
    bytes_total: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False


# ── 내부 헬퍼 함수 ────────────────────────────────────────


def _check_wrangler_installed() -> None:
    """wrangler CLI 설치 여부를 확인한다."""
    try:
        subprocess.run(
            ["wrangler", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(
            "wrangler CLI is not installed or not in PATH. Install with: npm install -g wrangler"
        ) from exc


def _extract_org_repo(event: GitHubEvent) -> tuple[str, str] | None:
    """이벤트에서 org/repo를 추출한다.

    repo.name이 정확히 "org/repo" 형식이어야 한다.
    그 외 형식은 None을 반환하고 경고를 로깅한다.
    """
    parts = event.repo.name.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        logger.warning(
            "Invalid repo name format: %r (event_id=%s), skipping",
            event.repo.name,
            event.id,
        )
        return None
    return parts[0], parts[1]


def _group_events_by_org_repo(
    events: list[GitHubEvent],
) -> tuple[dict[tuple[str, str], list[GitHubEvent]], int]:
    """이벤트를 org/repo 키로 그룹화한다.

    Returns:
        (grouped_dict, skipped_count)
    """
    grouped: dict[tuple[str, str], list[GitHubEvent]] = defaultdict(list)
    skipped = 0
    for event in events:
        result = _extract_org_repo(event)
        if result is None:
            skipped += 1
            continue
        grouped[result].append(event)
    return dict(grouped), skipped


def _compress_events_to_gzip(events: list[GitHubEvent], output_path: Path) -> int:
    """이벤트를 JSON Lines + gzip으로 압축한다.

    Returns:
        압축된 파일의 바이트 수
    """
    with gzip.open(output_path, "wb") as f:
        for event in events:
            line = orjson.dumps(event.model_dump(mode="json")) + b"\n"
            f.write(line)
    return output_path.stat().st_size


def _build_r2_key(prefix: str, org: str, repo: str, batch_date: str) -> str:
    """R2 오브젝트 키를 생성한다.

    형식: {prefix}/{org}/{repo}/{batch_date}.jsonl.gz
    prefix가 비어있으면 prefix 부분을 생략한다.
    """
    parts = [p for p in [prefix, org, repo, f"{batch_date}.jsonl.gz"] if p]
    return "/".join(parts)


def _wrangler_r2_put(
    bucket: str,
    key: str,
    file_path: Path,
    *,
    max_retries: int = 3,
) -> None:
    """wrangler r2 object put 명령을 실행한다.

    실패 시 지수 백오프로 재시도한다.
    """
    for attempt in range(1, max_retries + 1):
        try:
            subprocess.run(
                [
                    "wrangler",
                    "r2",
                    "object",
                    "put",
                    f"{bucket}/{key}",
                    "--file",
                    str(file_path),
                ],
                capture_output=True,
                check=True,
                text=True,
            )
            return
        except subprocess.CalledProcessError as exc:
            if attempt == max_retries:
                raise RuntimeError(
                    f"wrangler r2 put failed after {max_retries} retries: {exc.stderr}"
                ) from exc
            wait = (2**attempt) + random.uniform(0, 1)
            logger.warning(
                "wrangler r2 put attempt %d/%d failed, retrying in %.1fs: %s",
                attempt,
                max_retries,
                wait,
                exc.stderr,
            )
            time.sleep(wait)


# ── 메인 업로드 함수 ──────────────────────────────────────


def upload_events_to_r2(
    events: list[GitHubEvent],
    batch_date: str,
    config: R2Config,
    *,
    dry_run: bool = False,
    max_retries: int = 3,
    on_progress: Callable[[str, str], None] | None = None,
) -> R2UploadResult:
    """이벤트를 org/repo별로 그룹화하여 R2에 업로드한다.

    Args:
        events: 업로드할 GitHub 이벤트 목록
        batch_date: 배치 날짜 (예: "2024-01-15")
        config: R2 설정
        dry_run: True이면 실제 업로드 없이 시뮬레이션
        max_retries: wrangler 재시도 횟수
        on_progress: 진행 콜백 (org, repo)

    Returns:
        R2UploadResult
    """
    result = R2UploadResult(total_events=len(events), dry_run=dry_run)

    if not dry_run:
        _check_wrangler_installed()

    grouped, skipped = _group_events_by_org_repo(events)
    result.skipped_invalid_repo = skipped

    for (org, repo), group_events in grouped.items():
        key = _build_r2_key(config.prefix, org, repo, batch_date)

        if on_progress:
            on_progress(org, repo)

        with tempfile.TemporaryDirectory() as tmp_dir:
            gz_path = Path(tmp_dir) / "events.jsonl.gz"
            file_bytes = _compress_events_to_gzip(group_events, gz_path)
            result.bytes_total += file_bytes

            if dry_run:
                logger.info("[DRY RUN] Would upload %s (%d bytes)", key, file_bytes)
                result.files_skipped += 1
                continue

            try:
                _wrangler_r2_put(
                    config.bucket_name,
                    key,
                    gz_path,
                    max_retries=max_retries,
                )
                result.files_uploaded += 1
                logger.info("Uploaded %s (%d bytes)", key, file_bytes)
            except RuntimeError as exc:
                error_msg = f"Failed to upload {key}: {exc}"
                result.errors.append(error_msg)
                logger.error(error_msg)

    return result
