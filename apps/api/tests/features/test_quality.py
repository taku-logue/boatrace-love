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


def make_quality_df(**overrides: object) -> pd.DataFrame:
    data: dict[str, object] = {
        "race_id": ["20260601_01_01"] * 6,
        "boat_no": [1, 2, 3, 4, 5, 6],
        "target_win": [1, 0, 0, 0, 0, 0],
        "target_top2": [1, 1, 0, 0, 0, 0],
        "target_top3": [1, 1, 1, 0, 0, 0],
        "exclude_reason": [None] * 6,
        "racer_class": ["A1", "A2", "B1", "B1", "A1", "B2"],
        "racer_win_rate": [7.5, 6.0, 5.1, 4.2, 6.8, 3.9],
        "is_missing_period_stats": [False] * 6,
        "is_missing_pre_race": [False] * 6,
        "is_missing_weather": [False] * 6,
        "is_missing_odds": [False] * 6,
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_validate_dataset_quality_success():
    df = make_quality_df()
    metrics = validate_dataset_quality(df)
    assert metrics["total_rows"] == 6
    assert metrics["missing_rate_racer_class"] == 0.0
    assert metrics["row_completeness_rate"] == 1.0


def test_validate_dataset_quality_fails_on_duplicates():
    df = make_quality_df(boat_no=[1, 1, 3, 4, 5, 6])
    with pytest.raises(FeatureQualityError, match="重複"):
        validate_dataset_quality(df)


def test_validate_dataset_quality_fails_on_multiple_winners():
    df = make_quality_df(target_win=[1, 1, 0, 0, 0, 0])
    with pytest.raises(FeatureQualityError, match="複数の1着"):
        validate_dataset_quality(df)


def test_validate_dataset_quality_fails_on_invalid_top2_sum():
    df = make_quality_df(target_top2=[1, 0, 0, 0, 0, 0])
    with pytest.raises(FeatureQualityError, match="target_top2"):
        validate_dataset_quality(df)


def test_validate_dataset_quality_fails_on_high_missing_rate():
    df = make_quality_df(racer_class=["A1", None, None, None, None, None])
    with pytest.raises(FeatureQualityError, match="欠損率が閾値.*を超えています"):
        validate_dataset_quality(df)


def test_validate_dataset_quality_fails_when_view_feature_missing():
    df = make_quality_df()
    with pytest.raises(FeatureQualityError, match="win_odds"):
        validate_dataset_quality(df, model_view="pre_race_with_odds")


def test_validate_dataset_quality_fails_when_view_feature_null_rate_is_high():
    df = make_quality_df(win_odds=[1.8, None, None, None, None, None])
    with pytest.raises(FeatureQualityError, match="win_odds.*欠損率"):
        validate_dataset_quality(df, model_view="pre_race_with_odds")


def test_validate_phase4_status_success():
    session = MagicMock()
    mock_status = LiveFetchStatus(status="completed", file_metadata={"parser_error_count": 0})
    session.execute.return_value.scalars.return_value.all.return_value = [mock_status]
    validate_phase4_status(session, [date(2026, 6, 1)], "exhibition_with_odds")


def test_validate_phase4_status_fails_when_missing_status():
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []
    with pytest.raises(FeatureQualityError, match="取得ステータスが存在しません"):
        validate_phase4_status(session, [date(2026, 6, 1)], "exhibition_with_odds", "23")


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
