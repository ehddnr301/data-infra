"""이벤트 수 이상 탐지 모듈.

전일 대비 이벤트 수 변화율을 기반으로 이상을 탐지한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class AnomalyResult:
    """이상 탐지 결과."""

    metric_name: str
    today_value: int
    yesterday_value: int
    change_rate: float  # 변화율 (-1.0 ~ +inf)
    is_anomaly: bool
    level: Literal["INFO", "WARN", "ERROR"]
    message: str


def evaluate_ingestion_anomaly(
    today: int,
    yesterday: int,
    surge_threshold: float = 1.0,  # +100%
    drop_threshold: float = -0.5,  # -50%
) -> AnomalyResult:
    """전일 대비 이벤트 수 이상 탐지.

    Args:
        today: 오늘 이벤트 수
        yesterday: 어제 이벤트 수
        surge_threshold: 급증 임계치 (기본 +100%)
        drop_threshold: 급감 임계치 (기본 -50%)

    Returns:
        AnomalyResult with anomaly detection details.
    """
    # yesterday == 0인 경우: 나누기 0 안전 처리
    if yesterday == 0:
        if today == 0:
            return AnomalyResult(
                metric_name="ingestion_events",
                today_value=today,
                yesterday_value=yesterday,
                change_rate=0.0,
                is_anomaly=False,
                level="INFO",
                message="No events both days",
            )
        return AnomalyResult(
            metric_name="ingestion_events",
            today_value=today,
            yesterday_value=yesterday,
            change_rate=float("inf"),
            is_anomaly=False,
            level="INFO",
            message=f"New events today ({today}), no baseline yesterday",
        )

    change_rate = (today - yesterday) / yesterday

    if change_rate > surge_threshold:
        return AnomalyResult(
            metric_name="ingestion_events",
            today_value=today,
            yesterday_value=yesterday,
            change_rate=change_rate,
            is_anomaly=True,
            level="WARN",
            message=f"Event surge detected: {change_rate:+.1%} (threshold: {surge_threshold:+.1%})",
        )

    if change_rate < drop_threshold:
        return AnomalyResult(
            metric_name="ingestion_events",
            today_value=today,
            yesterday_value=yesterday,
            change_rate=change_rate,
            is_anomaly=True,
            level="WARN",
            message=f"Event drop detected: {change_rate:+.1%} (threshold: {drop_threshold:+.1%})",
        )

    return AnomalyResult(
        metric_name="ingestion_events",
        today_value=today,
        yesterday_value=yesterday,
        change_rate=change_rate,
        is_anomaly=False,
        level="INFO",
        message=f"Normal range: {change_rate:+.1%}",
    )
