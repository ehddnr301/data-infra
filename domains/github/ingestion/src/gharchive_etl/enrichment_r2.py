"""Enrichment 전용 R2 업로드 모듈.

GitHub API로 수집한 상세 데이터를 R2에 저장한다.
기존 r2.py의 wrangler CLI 패턴을 재사용하되, enrichment 전용 키 구조를 적용한다.

R2 키 구조:
  enriched/commits/{owner}/{repo}/{sha}.json
  enriched/pr-files/{owner}/{repo}/{pr_number}.json
  enriched/issue-comments/{owner}/{repo}/{issue_number}.json
  enriched/pr-reviews/{owner}/{repo}/{pr_number}.json
  enriched/users/{user_login}.json
  enriched/wiki/{owner}/{repo}/{page_name}.md
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import orjson

from gharchive_etl.r2 import _find_wrangler, _wrangler_r2_put

logger = logging.getLogger(__name__)


def build_enrichment_r2_key(
    category: str,
    owner: str,
    repo: str,
    identifier: str,
    *,
    extension: str = ".json",
    prefix: str = "enriched",
) -> str:
    """enrichment R2 오브젝트 키를 생성한다.

    Args:
        category: "commits", "pr-files", "issue-comments", "pr-reviews", "users", "wiki"
        owner: GitHub org/owner
        repo: 레포지토리 이름 (users 카테고리에서는 빈 문자열)
        identifier: sha, pr_number, issue_number, user_login, page_name
        extension: 파일 확장자 (기본: .json)
        prefix: R2 키 prefix (기본: enriched)

    Returns:
        R2 오브젝트 키 문자열

    Examples:
        >>> build_enrichment_r2_key("commits", "Pseudo-Lab", "repo", "abc123")
        'enriched/commits/Pseudo-Lab/repo/abc123.json'
        >>> build_enrichment_r2_key("users", "", "", "octocat")
        'enriched/users/octocat.json'
    """
    if category == "users":
        return f"{prefix}/{category}/{identifier}{extension}"
    return f"{prefix}/{category}/{owner}/{repo}/{identifier}{extension}"


# ── 로컬 트래커 (R2 업로드 이력) ──────────────────────────────

_TRACKER_DIR = Path.home() / ".cache" / "gharchive-etl"


def _tracker_path(bucket: str) -> Path:
    """버킷별 enrichment 트래커 파일 경로."""
    safe_name = bucket.replace("/", "_").replace(" ", "_")
    return _TRACKER_DIR / f"enriched-{safe_name}.txt"


def load_enriched_keys(bucket: str) -> set[str]:
    """로컬 캐시에서 이미 R2에 업로드된 키 집합을 로드한다."""
    path = _tracker_path(bucket)
    if not path.exists():
        return set()
    return set(path.read_text().splitlines())


def save_enriched_key(bucket: str, key: str) -> None:
    """성공적으로 업로드된 R2 키를 트래커에 기록한다."""
    _TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    with _tracker_path(bucket).open("a") as f:
        f.write(key + "\n")


def sync_enriched_keys_from_r2(
    bucket: str,
    account_id: str,
    api_token: str,
    *,
    prefix: str = "enriched/",
) -> int:
    """R2에서 기존 enrichment 오브젝트 키를 조회하여 로컬 트래커에 동기화한다.

    Cloudflare API v4의 R2 오브젝트 목록 조회를 사용한다.

    Returns:
        동기화된 키 개수
    """
    import httpx

    base_url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/r2/buckets/{bucket}/objects"
    )
    headers = {"Authorization": f"Bearer {api_token}"}

    all_keys: set[str] = load_enriched_keys(bucket)
    initial_count = len(all_keys)
    cursor: str | None = None

    while True:
        params: dict[str, str | int] = {"prefix": prefix, "per_page": 500}
        if cursor:
            params["cursor"] = cursor

        resp = httpx.get(base_url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for obj in data.get("result", []):
            key = obj.get("key", "")
            if key:
                all_keys.add(key)

        # 페이지네이션
        cursor = data.get("result_info", {}).get("cursor")
        if not cursor or not data.get("result"):
            break

    # 트래커 파일 전체 교체
    _TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    _tracker_path(bucket).write_text(
        "\n".join(sorted(all_keys)) + "\n" if all_keys else ""
    )

    new_count = len(all_keys) - initial_count
    logger.info(
        "Synced %d keys from R2 (total: %d, new: %d)", len(all_keys), len(all_keys), new_count
    )
    return len(all_keys)


def check_r2_key_exists(bucket: str, key: str) -> bool:
    """wrangler r2 object get으로 키 존재 여부를 확인한다.

    존재하면 True, 404면 False, 기타 에러면 False(보수적).
    NOTE: 건별로 subprocess를 호출하므로 대량 체크에는 load_enriched_keys를 사용할 것.
    """
    try:
        wrangler = _find_wrangler()
        result = subprocess.run(
            [wrangler, "r2", "object", "get", f"{bucket}/{key}", "--pipe", "--remote"],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def upload_enrichment_json(
    bucket: str,
    key: str,
    data: dict[str, Any] | list[Any],
    *,
    dry_run: bool = False,
    max_retries: int = 3,
) -> bool:
    """JSON 데이터를 R2에 업로드한다.

    Returns:
        업로드 성공 여부
    """
    if dry_run:
        serialized = orjson.dumps(data)
        logger.info("[DRY RUN] Would upload %s (%d bytes)", key, len(serialized))
        return True

    try:
        serialized = orjson.dumps(data, option=orjson.OPT_INDENT_2)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(serialized)
            tmp_path = Path(tmp.name)

        try:
            _wrangler_r2_put(bucket, key, tmp_path, max_retries=max_retries)
            return True
        finally:
            tmp_path.unlink(missing_ok=True)

    except Exception as exc:
        logger.error("Failed to upload %s: %s", key, exc)
        return False


def upload_enrichment_text(
    bucket: str,
    key: str,
    text: str,
    *,
    dry_run: bool = False,
    max_retries: int = 3,
) -> bool:
    """텍스트 데이터(위키 마크다운 등)를 R2에 업로드한다.

    Returns:
        업로드 성공 여부
    """
    if dry_run:
        logger.info("[DRY RUN] Would upload %s (%d bytes)", key, len(text.encode()))
        return True

    try:
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as tmp:
            tmp.write(text)
            tmp_path = Path(tmp.name)

        try:
            _wrangler_r2_put(bucket, key, tmp_path, max_retries=max_retries)
            return True
        finally:
            tmp_path.unlink(missing_ok=True)

    except Exception as exc:
        logger.error("Failed to upload text %s: %s", key, exc)
        return False
