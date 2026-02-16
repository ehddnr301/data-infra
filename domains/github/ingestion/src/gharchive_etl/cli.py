"""click CLI 엔트리포인트.

기본 구조만 정의. 실제 fetch 로직은 후속 티켓에서 구현.
"""

from __future__ import annotations

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="gharchive-etl")
def main() -> None:
    """GitHub Archive ETL - 특정 org의 GitHub 이벤트를 수집합니다."""


@main.command()
@click.option("--date", required=True, help="수집 대상 날짜 (예: 2024-01-15)")
def fetch(date: str) -> None:
    """지정된 날짜의 GitHub Archive 이벤트를 수집합니다.

    해당 날짜의 0~23시 파일을 순회하며, 설정된 target_orgs에
    해당하는 이벤트만 필터링하여 R2/D1에 적재합니다.
    """
    raise NotImplementedError(f"fetch for date={date} will be implemented in a follow-up ticket")


if __name__ == "__main__":
    main()
