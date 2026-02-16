"""gharchive.org 시간별 ndjson.gz 다운로드.

후속 티켓에서 구현 예정.
"""

from __future__ import annotations

from pathlib import Path

from gharchive_etl.config import HttpConfig


def download_hour(date: str, hour: int, config: HttpConfig) -> Path:
    """지정된 날짜/시간의 gharchive ndjson.gz 파일을 다운로드한다.

    Args:
        date: 날짜 문자열 (예: "2024-01-15")
        hour: 시간 (0~23)
        config: HTTP 설정 (timeout, retries 등)

    Returns:
        다운로드된 파일의 로컬 경로

    Raises:
        NotImplementedError: 후속 티켓에서 구현 예정
    """
    raise NotImplementedError("download_hour will be implemented in a follow-up ticket")
