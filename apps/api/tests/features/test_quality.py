import pandas as pd
import pytest

from app.features.quality import validate_dataset_quality, FeatureQualityError


def test_validate_dataset_quality_success():
    """正常なデータセットがエラーにならず、メトリクスを返すことをテスト"""
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
    """主キーが重複しているとエラーになることをテスト"""
    df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01", "20260601_01_01"],
            "boat_no": [1, 1],  # 1号艇が重複
            "target_win": [1, 0],
        }
    )

    with pytest.raises(FeatureQualityError, match="重複"):
        validate_dataset_quality(df)


def test_validate_dataset_quality_fails_on_multiple_winners():
    """1レースに1着が2艇以上いるとエラーになることをテスト"""
    df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01", "20260601_01_01"],
            "boat_no": [1, 2],
            "target_win": [1, 1],  # 両方1着はおかしい
        }
    )

    with pytest.raises(FeatureQualityError, match="複数の1着"):
        validate_dataset_quality(df)


def test_validate_dataset_quality_fails_on_high_missing_rate():
    """P0特徴量の欠損率が高いとエラーになることをテスト"""
    # 100行中、10行が欠損（欠損率10% -> 閾値5%オーバー）
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
