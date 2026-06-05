from unittest.mock import MagicMock, patch

import pandas as pd

from app.features.build import build_training_dataset


@patch("app.features.build.add_odds_features")
@patch("app.features.build.add_pre_race_features")
@patch("app.features.build.add_racer_period_stats")
@patch("app.features.build.fetch_base_features")
@patch("app.features.build.fetch_label_records")
def test_build_training_dataset_exhibition_with_odds(
    mock_fetch_labels, mock_fetch_features, mock_add_stats, mock_add_pre_race, mock_add_odds
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

    # 各処理を通過するごとにカラムが増えていく様をモック
    stats_df = base_df.copy()
    stats_df["racer_win_rate"] = [7.50]
    mock_add_stats.return_value = stats_df

    pre_race_df = stats_df.copy()
    pre_race_df["exhibition_time"] = [6.60]
    pre_race_df["wind_speed"] = [3.0]
    mock_add_pre_race.return_value = pre_race_df

    odds_df = pre_race_df.copy()
    odds_df["win_odds"] = [1.5]
    mock_add_odds.return_value = odds_df

    mock_fetch_labels.return_value = [
        {"race_id": "20260601_01_01", "boat_no": 1, "finish_position": 1, "result_status": None},
    ]

    dummy_session = MagicMock()

    # exhibition_with_odds ビューで実行
    dataset_df = build_training_dataset(dummy_session, model_view="exhibition_with_odds")

    assert not dataset_df.empty

    # 全ての追加機能が呼ばれたか
    mock_add_stats.assert_called_once()
    mock_add_pre_race.assert_called_once()
    mock_add_odds.assert_called_once()

    # カラムがすべて揃っているか
    boat1 = dataset_df.iloc[0]
    assert boat1["racer_win_rate"] == 7.50
    assert boat1["exhibition_time"] == 6.60
    assert boat1["wind_speed"] == 3.0
    assert boat1["win_odds"] == 1.5
    assert boat1["target_win"] == 1


@patch("app.features.build.add_odds_features")
@patch("app.features.build.add_pre_race_features")
@patch("app.features.build.add_racer_period_stats")
@patch("app.features.build.fetch_base_features")
@patch("app.features.build.fetch_label_records")
def test_build_training_dataset_pre_race_no_odds(
    mock_fetch_labels, mock_fetch_features, mock_add_stats, mock_add_pre_race, mock_add_odds
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
    mock_fetch_labels.return_value = [
        {"race_id": "20260601_01_01", "boat_no": 1, "finish_position": 1, "result_status": None},
    ]

    dummy_session = MagicMock()

    # デフォルトの pre_race_no_odds ビューで実行
    dataset_df = build_training_dataset(dummy_session, model_view="pre_race_no_odds")

    assert not dataset_df.empty

    # 禁止されている特徴量結合関数が呼ばれていないか
    mock_add_pre_race.assert_not_called()
    mock_add_odds.assert_not_called()
