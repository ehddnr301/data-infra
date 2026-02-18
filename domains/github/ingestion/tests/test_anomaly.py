"""이벤트 수 이상 탐지 모듈 테스트."""

from __future__ import annotations

import pytest
from gharchive_etl.anomaly import AnomalyResult, evaluate_ingestion_anomaly


class TestEvaluateIngestionAnomaly:
    """전일 대비 이벤트 수 이상 탐지 테스트."""

    def test_normal_range(self) -> None:
        """정상 범위 → is_anomaly=False."""
        result = evaluate_ingestion_anomaly(today=110, yesterday=100)
        assert result.is_anomaly is False
        assert result.level == "INFO"
        assert result.change_rate == pytest.approx(0.1)

    def test_surge_detected(self) -> None:
        """+100% 초과 → is_anomaly=True, level=WARN."""
        result = evaluate_ingestion_anomaly(today=250, yesterday=100)
        assert result.is_anomaly is True
        assert result.level == "WARN"
        assert result.change_rate == pytest.approx(1.5)
        assert "surge" in result.message.lower()

    def test_drop_detected(self) -> None:
        """-50% 미만 → is_anomaly=True, level=WARN."""
        result = evaluate_ingestion_anomaly(today=40, yesterday=100)
        assert result.is_anomaly is True
        assert result.level == "WARN"
        assert result.change_rate == pytest.approx(-0.6)
        assert "drop" in result.message.lower()

    def test_yesterday_zero_today_nonzero(self) -> None:
        """yesterday=0, today>0 → 나누기 0 안전 처리, INFO."""
        result = evaluate_ingestion_anomaly(today=50, yesterday=0)
        assert result.is_anomaly is False
        assert result.level == "INFO"
        assert result.change_rate == float("inf")

    def test_yesterday_zero_today_zero(self) -> None:
        """yesterday=0, today=0 → INFO."""
        result = evaluate_ingestion_anomaly(today=0, yesterday=0)
        assert result.is_anomaly is False
        assert result.level == "INFO"
        assert result.change_rate == 0.0

    def test_exact_surge_threshold(self) -> None:
        """정확히 surge_threshold → is_anomaly=False (초과해야 함)."""
        # change_rate = (200 - 100) / 100 = 1.0 == surge_threshold
        result = evaluate_ingestion_anomaly(today=200, yesterday=100, surge_threshold=1.0)
        assert result.is_anomaly is False
        assert result.level == "INFO"

    def test_exact_drop_threshold(self) -> None:
        """정확히 drop_threshold → is_anomaly=False (미만이어야 함)."""
        # change_rate = (50 - 100) / 100 = -0.5 == drop_threshold
        result = evaluate_ingestion_anomaly(today=50, yesterday=100, drop_threshold=-0.5)
        assert result.is_anomaly is False
        assert result.level == "INFO"

    def test_just_above_surge_threshold(self) -> None:
        """surge_threshold 바로 초과."""
        result = evaluate_ingestion_anomaly(today=201, yesterday=100, surge_threshold=1.0)
        assert result.is_anomaly is True
        assert result.level == "WARN"

    def test_just_below_drop_threshold(self) -> None:
        """drop_threshold 바로 미만."""
        result = evaluate_ingestion_anomaly(today=49, yesterday=100, drop_threshold=-0.5)
        assert result.is_anomaly is True
        assert result.level == "WARN"

    def test_custom_thresholds(self) -> None:
        """커스텀 임계치 사용."""
        result = evaluate_ingestion_anomaly(
            today=160, yesterday=100, surge_threshold=0.5, drop_threshold=-0.3
        )
        assert result.is_anomaly is True
        assert result.level == "WARN"

    def test_result_fields(self) -> None:
        """AnomalyResult 필드 검증."""
        result = evaluate_ingestion_anomaly(today=100, yesterday=100)
        assert result.metric_name == "ingestion_events"
        assert result.today_value == 100
        assert result.yesterday_value == 100
        assert isinstance(result.change_rate, float)
        assert isinstance(result.is_anomaly, bool)
        assert result.level in ("INFO", "WARN", "ERROR")
        assert isinstance(result.message, str)

    def test_no_change(self) -> None:
        """변화 없음 → 정상."""
        result = evaluate_ingestion_anomaly(today=100, yesterday=100)
        assert result.is_anomaly is False
        assert result.change_rate == pytest.approx(0.0)
