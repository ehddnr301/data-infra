"""Parquet 변환 + R2 업로드 (pyarrow + boto3).

후속 티켓에서 구현 예정.
"""

from __future__ import annotations

from gharchive_etl.config import R2Config
from gharchive_etl.models import GitHubEvent


def upload_to_r2(events: list[GitHubEvent], key: str, config: R2Config) -> None:
    """필터링된 이벤트를 Parquet으로 변환 후 R2에 업로드한다.

    - pyarrow로 이벤트 리스트를 Parquet 포맷으로 변환
    - boto3 S3 호환 클라이언트로 R2에 업로드
    - R2 object key: raw/github-archive/{date}/{hour}.parquet
    - 동일 키에 덮어쓰기로 멱등성 보장

    Args:
        events: 업로드할 GitHub 이벤트 목록
        key: R2 object key (예: "raw/github-archive/2024-01-15/0.parquet")
        config: R2 설정 (bucket_name, prefix 등)

    Raises:
        NotImplementedError: 후속 티켓에서 구현 예정
    """
    raise NotImplementedError("upload_to_r2 will be implemented in a follow-up ticket")
