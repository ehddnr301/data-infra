"""D1 HTTP API 클라이언트 (parameterized query).

후속 티켓에서 구현 예정.
- Cloudflare D1 HTTP API를 통해 이벤트 적재
- 반드시 parameterized query만 사용 (문자열 SQL 생성 금지)
- INSERT OR IGNORE로 멱등성 보장 (event.id PRIMARY KEY)
"""

from __future__ import annotations

from gharchive_etl.config import D1Config
from gharchive_etl.models import GitHubEvent


def insert_events(events: list[GitHubEvent], config: D1Config) -> int:
    """D1 HTTP API로 이벤트를 적재한다.

    - parameterized query로만 적재 (문자열 SQL 조합 금지)
    - INSERT OR IGNORE로 event.id 기준 중복 방지
    - API endpoint: https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query

    Args:
        events: 적재할 GitHub 이벤트 목록
        config: D1 설정 (database_id 등)

    Returns:
        실제 적재된 이벤트 수

    Raises:
        NotImplementedError: 후속 티켓에서 구현 예정
    """
    raise NotImplementedError("insert_events will be implemented in a follow-up ticket")
