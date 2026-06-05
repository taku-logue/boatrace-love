from datetime import date
from unittest.mock import MagicMock
import pandas as pd
import pytest

from app.features.quality import (
    validate_dataset_quality,
    FeatureQualityError,
    validate_phase4_status,
)
from app.models.pre_race_info import LiveFetchStatus


def test_validate_dataset_quality_success():
    df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01", "20260601_01_01"],
            "boat_no": [1, 2],
            "target_win": [1, 0],
            "racer_class": ["A1", "B1"],
            "racer_win_rate": [7.50, 4.20],
        }
    )
    metrics = validate_dataset_quality(df)
    assert metrics["total_rows"] == 2
    assert metrics["missing_rate_racer_class"] == 0.0


def test_validate_dataset_quality_fails_on_duplicates():
    df = pd.DataFrame(
        {"race_id": ["20260601_01_01", "20260601_01_01"], "boat_no": [1, 1], "target_win": [1, 0]}
    )
    with pytest.raises(FeatureQualityError, match="重複"):
        validate_dataset_quality(df)


def test_validate_dataset_quality_fails_on_multiple_winners():
    df = pd.DataFrame(
        {"race_id": ["20260601_01_01", "20260601_01_01"], "boat_no": [1, 2], "target_win": [1, 1]}
    )
    with pytest.raises(FeatureQualityError, match="複数の1着"):
        validate_dataset_quality(df)


def test_validate_dataset_quality_fails_on_high_missing_rate():
    df = pd.DataFrame(
        {
            "race_id": [f"race_{i}" for i in range(100)],
            "boat_no": [1] * 100,
            "target_win": [0] * 100,
            "racer_class": ["A1"] * 90 + [None] * 10,
            "racer_win_rate": [7.0] * 100,
        }
    )
    with pytest.raises(FeatureQualityError, match="欠損率が閾値.*を超えています"):
        validate_dataset_quality(df)


def test_validate_phase4_status_success():
    session = MagicMock()
    mock_status = LiveFetchStatus(status="completed", file_metadata={"parser_error_count": 0})
    session.execute.return_value.scalars.return_value.all.return_value = [mock_status]
    validate_phase4_status(session, [date(2026, 6, 1)], "exhibition_with_odds")


def test_validate_phase4_status_fails_on_failed_status():
    session = MagicMock()
    mock_status = LiveFetchStatus(race_date=date(2026, 6, 1), data_kind="odds", status="failed")
    session.execute.return_value.scalars.return_value.all.return_value = [mock_status]
    with pytest.raises(FeatureQualityError, match="status='failed'"):
        validate_phase4_status(session, [date(2026, 6, 1)], "exhibition_with_odds")


def test_validate_phase4_status_fails_on_parser_error():
    session = MagicMock()
    mock_status = LiveFetchStatus(
        race_date=date(2026, 6, 1),
        data_kind="exhibition",
        status="completed",
        file_metadata={"parser_error_count": 3},
    )
    session.execute.return_value.scalars.return_value.all.return_value = [mock_status]
    with pytest.raises(FeatureQualityError, match="3件 のエラー"):
        validate_phase4_status(session, [date(2026, 6, 1)], "exhibition_with_odds")
