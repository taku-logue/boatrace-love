from unittest.mock import MagicMock, patch

import pandas as pd

from app.features.build import build_feature_dataset, build_training_dataset


@patch("app.features.build.add_odds_features")
@patch("app.features.build.add_pre_race_features")
@patch("app.features.build.add_historical_performance_features")
@patch("app.features.build.add_racer_period_stats")
@patch("app.features.build.fetch_base_features")
@patch("app.features.build.fetch_label_records")
def test_build_training_dataset_exhibition_with_odds(
    mock_fetch_labels,
    mock_fetch_features,
    mock_add_stats,
    mock_add_history,
    mock_add_pre_race,
    mock_add_odds,
):
    """
    'exhibition_with_odds' ビューでの構築テスト。
    展示やオッズなどのすべての特徴量が付与された状態で安全に結合されるか確認。
    """
    base_df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01"],
            "race_date": [pd.to_datetime("2026-06-01")],
            "boat_no": [1],
            "venue_code": ["01"],
            "racer_registration_no": ["1234"],
        }
    )
    mock_fetch_features.return_value = base_df

    stats_df = base_df.copy()
    stats_df["racer_win_rate"] = [7.50]
    mock_add_stats.return_value = stats_df
    mock_add_history.return_value = stats_df

    pre_race_df = stats_df.copy()
    pre_race_df["exhibition_time"] = [6.60]
    pre_race_df["wind_speed"] = [3.0]
    # P1特徴量のモック返り値への追加
    pre_race_df["exhibition_time_rank"] = [1.0]
    pre_race_df["exhibition_time_diff"] = [0.0]
    mock_add_pre_race.return_value = pre_race_df

    odds_df = pre_race_df.copy()
    odds_df["win_odds"] = [1.5]
    # P1特徴量のモック返り値への追加
    odds_df["win_popularity"] = [1.0]
    odds_df["market_probability"] = [0.666]
    mock_add_odds.return_value = odds_df

    mock_fetch_labels.return_value = [
        {"race_id": "20260601_01_01", "boat_no": 1, "finish_position": 1, "result_status": None},
    ]

    dummy_session = MagicMock()

    dataset_df = build_training_dataset(dummy_session, model_view="exhibition_with_odds")

    assert not dataset_df.empty

    mock_add_stats.assert_called_once()
    mock_add_history.assert_called_once()
    mock_add_pre_race.assert_called_once()
    mock_add_odds.assert_called_once()

    boat1 = dataset_df.iloc[0]
    assert boat1["racer_win_rate"] == 7.50
    assert boat1["exhibition_time"] == 6.60
    assert boat1["wind_speed"] == 3.0
    assert boat1["win_odds"] == 1.5
    assert boat1["target_win"] == 1

    # P1特徴量の検証
    assert boat1["exhibition_time_rank"] == 1.0
    assert boat1["exhibition_time_diff"] == 0.0
    assert boat1["win_popularity"] == 1.0
    assert abs(boat1["market_probability"] - 0.666) < 0.01
    assert bool(boat1["is_missing_pre_race"]) is False
    assert bool(boat1["is_missing_weather"]) is False
    assert bool(boat1["is_missing_odds"]) is False


@patch("app.features.build.add_odds_features")
@patch("app.features.build.add_pre_race_features")
@patch("app.features.build.add_historical_performance_features")
@patch("app.features.build.add_racer_period_stats")
@patch("app.features.build.fetch_base_features")
@patch("app.features.build.fetch_label_records")
def test_build_training_dataset_pre_race_no_odds(
    mock_fetch_labels,
    mock_fetch_features,
    mock_add_stats,
    mock_add_history,
    mock_add_pre_race,
    mock_add_odds,
):
    """
    'pre_race_no_odds' ビューでの構築テスト。
    展示とオッズ情報が結合されない（未来情報として除外される）ことを確認。
    """
    base_df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01"],
            "race_date": [pd.to_datetime("2026-06-01")],
            "boat_no": [1],
        }
    )
    mock_fetch_features.return_value = base_df
    mock_add_stats.return_value = base_df.copy()
    mock_add_history.return_value = base_df.copy()
    mock_fetch_labels.return_value = [
        {"race_id": "20260601_01_01", "boat_no": 1, "finish_position": 1, "result_status": None},
    ]

    dummy_session = MagicMock()

    dataset_df = build_training_dataset(dummy_session, model_view="pre_race_no_odds")

    assert not dataset_df.empty

    mock_add_pre_race.assert_not_called()
    mock_add_odds.assert_not_called()
    mock_add_history.assert_called_once()
    boat1 = dataset_df.iloc[0]
    assert bool(boat1["is_missing_pre_race"]) is False
    assert bool(boat1["is_missing_weather"]) is False
    assert bool(boat1["is_missing_odds"]) is False


@patch("app.features.build.add_historical_performance_features")
@patch("app.features.build.add_racer_period_stats")
@patch("app.features.build.fetch_base_features")
@patch("app.features.build.fetch_label_records")
def test_build_feature_dataset_does_not_fetch_labels(
    mock_fetch_labels,
    mock_fetch_features,
    mock_add_stats,
    mock_add_history,
):
    base_df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01"],
            "race_date": [pd.to_datetime("2026-06-01")],
            "boat_no": [1],
            "venue_code": ["01"],
        }
    )
    mock_fetch_features.return_value = base_df
    mock_add_stats.return_value = base_df.copy()
    mock_add_history.return_value = base_df.copy()

    dummy_session = MagicMock()

    feature_df = build_feature_dataset(
        dummy_session,
        model_view="pre_race_no_odds",
        race_id="20260601_01_01",
    )

    assert not feature_df.empty
    assert "target_win" not in feature_df.columns
    assert "exclude_reason" not in feature_df.columns
    assert bool(feature_df.iloc[0]["is_missing_odds"]) is False
    mock_fetch_labels.assert_not_called()
